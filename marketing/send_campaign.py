"""
General-purpose marketing email campaign runner.

Sends via Microsoft Graph's sendMail API using an app-only (client
credentials) OAuth2 token — not SMTP AUTH. This avoids per-mailbox SMTP AUTH
settings and Conditional Access "block legacy authentication" policies
entirely, since it's a modern OAuth-authenticated REST call, not an SMTP
login.

Manually triggered only — this script never sends anything on its own; it
must be invoked from the command line, and even then defaults to a dry run
(preview) unless --send is passed explicitly.

Usage:
    # 1. Copy config.example.json to config.json and fill in your details,
    #    including auth.tenant_id and auth.client_id from your Entra app
    #    registration (see marketing/README.md for the full setup).
    # 2. Put the app's client secret in a plain text file (default: scret.txt,
    #    next to this script). It is read fresh from disk on every run and
    #    never written anywhere else (not logged, not cached, not copied into
    #    config.json). Keep that file out of git.
    # 3. Set campaign.learn_more_url in config.json to your live NAPLAN portal
    #    URL — the template's "Learn more" button links there.
    # 4. Preview what would be sent (no emails leave your machine):
    #       python send_campaign.py --config config.json
    # 5. Actually send:
    #       python send_campaign.py --config config.json --send
"""

import argparse
import base64
import csv
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GRAPH_TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
GRAPH_SEND_MAIL_URL = "https://graph.microsoft.com/v1.0/users/{sender}/sendMail"

# Imported lazily inside get_db_connection() so dry-run/preview mode never
# needs pyodbc or a live database — only --send does.
DATABASE_DIR = Path(__file__).resolve().parent.parent / "database"

# Policy guardrail (2026-08-25): real campaign sends are on hold until
# explicitly lifted — only this test address may receive an actual --send.
# Dry-run/preview is unrestricted since it never leaves the machine. Remove
# this restriction only on explicit instruction to run the real campaign.
ALLOWED_SEND_RECIPIENTS = {"sqlpython@hotmail.com", "ben.zzzz@outlook.com"}

DEFAULT_MAX_SEND_PER_RUN = 15
PLACEHOLDER_MARKERS = ("placeholder", "replace_with", "your name", "your registered")


def _dns_lookup_confirms(record_type: str, name: str, must_contain: str | None, retries: int = 3) -> bool | None:
    """True if the record is confirmed present, False if confirmed absent,
    None if the check couldn't be run reliably at all (nslookup missing or
    erroring on every attempt).

    DNS lookups via nslookup proved flaky in this environment (a record
    confirmed present on one call came back looking absent on the next,
    purely from transient resolver issues) — a record that's actually there
    doesn't intermittently vanish, so a single successful confirmation
    short-circuits to True, while "absent" only sticks if every retry
    agrees. nslookup's "can't find"/NXDOMAIN text lands on stderr, not
    stdout — checking stdout alone (an earlier bug here) made every missing
    record look like a false PASS.
    """
    ran_at_least_once = False
    for _ in range(retries):
        try:
            result = subprocess.run(
                ["nslookup", f"-type={record_type}", name],
                capture_output=True, text=True, timeout=10,
            )
        except Exception:
            continue
        ran_at_least_once = True
        combined = (result.stdout + "\n" + result.stderr).lower()
        if "can't find" in combined or "non-existent domain" in combined:
            continue
        if must_contain is None or must_contain.lower() in result.stdout.lower():
            return True
    return False if ran_at_least_once else None


def run_preflight_checklist(sender_email: str, business: dict, sender: dict,
                             leads_count: int, max_send_per_run: int) -> None:
    """Enforces marketing/DELIVERABILITY_PLAN.md before every real --send.
    Any failed check aborts the run — see that file for what to fix and why."""
    domain = sender_email.split("@")[-1]
    failures = []

    def check(label: str, ok: bool, detail: str = "") -> None:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f" — {detail}" if detail and not ok else ""))
        if not ok:
            failures.append(label)

    print("\n--- Deliverability preflight (marketing/DELIVERABILITY_PLAN.md) ---")

    spf = _dns_lookup_confirms("TXT", domain, "v=spf1")
    check("SPF record", spf is True,
          "no 'v=spf1' confirmed on TXT records after retries (missing, or nslookup unavailable here) — "
          "verify manually: nslookup -type=TXT " + domain)

    dkim = _dns_lookup_confirms("CNAME", f"selector1._domainkey.{domain}", must_contain=None)
    check("DKIM (selector1)", dkim is True,
          "selector1._domainkey CNAME not confirmed after retries — enable DKIM in the M365 admin center "
          "(see plan doc section 1), or verify manually if you believe it's already set up")

    dmarc = _dns_lookup_confirms("TXT", f"_dmarc.{domain}", "v=DMARC1")
    check("DMARC record", dmarc is True,
          "_dmarc TXT record not confirmed after retries — publish one (see plan doc section 1), "
          "or verify manually if you believe it's already set up")

    check(f"Batch size <= {max_send_per_run}", leads_count <= max_send_per_run,
          f"{leads_count} recipients this run exceeds the warm-up limit — reduce with --limit or raise "
          f"campaign.max_send_per_run once far enough along the ramp (see plan doc section 2)")

    address_lower = (business.get("address") or "").lower()
    check("Business address is real (not a placeholder)",
          bool(business.get("address")) and not any(m in address_lower for m in PLACEHOLDER_MARKERS),
          f"business.address looks like a placeholder: {business.get('address')!r}")

    sender_name_lower = (sender.get("name") or "").lower()
    check("Sender name is real (not a placeholder)",
          bool(sender.get("name")) and not any(m in sender_name_lower for m in PLACEHOLDER_MARKERS),
          f"sender.name looks like a placeholder: {sender.get('name')!r}")

    print("---")

    if failures:
        raise SystemExit(
            f"Refusing to send: {len(failures)} deliverability check(s) failed "
            f"({', '.join(failures)}).\nSee marketing/DELIVERABILITY_PLAN.md for what each check means "
            f"and how to fix it. This is a hard gate, not advisory — dry-run/preview is unaffected."
        )


def load_config(config_path: Path) -> dict:
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def extract_email(raw: str) -> str | None:
    """Pull a single usable email address out of a CSV cell.

    Cells in scraped lead lists are messy, e.g. "rosebery@mwns.com.au
    (general: admin@mwns.com.au)" or "Not published - see https://...".
    Returns the first token that looks like an email, or None.
    """
    if not raw:
        return None
    for token in re.split(r"[\s,;()]+", raw):
        token = token.strip().strip(".,;")
        if EMAIL_RE.match(token):
            return token
    return None


def load_leads(csv_path: Path, name_col: str, email_col: str) -> list[dict]:
    leads = []
    seen = set()
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get(name_col) or "").strip()
            email = extract_email(row.get(email_col) or "")
            if not email:
                continue
            key = email.lower()
            if key in seen:
                continue
            seen.add(key)
            leads.append({"name": name, "email": email})
    return leads


def load_suppression(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with open(path, encoding="utf-8") as f:
        return {line.strip().lower() for line in f if line.strip()}


def load_already_sent(log_path: Path) -> set[str]:
    if not log_path.exists():
        return set()
    sent = set()
    with open(log_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status") == "sent":
                sent.add((row.get("email") or "").strip().lower())
    return sent


def append_log(log_path: Path, email: str, name: str, status: str, detail: str = "") -> None:
    is_new = not log_path.exists()
    with open(log_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["timestamp", "email", "name", "status", "detail"])
        writer.writerow([datetime.now(timezone.utc).isoformat(), email, name, status, detail])


def render(template: str, **fields) -> str:
    try:
        return template.format(**fields)
    except KeyError as e:
        raise SystemExit(f"Template references unknown placeholder: {e}")


def get_graph_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    url = GRAPH_TOKEN_URL.format(tenant_id=tenant_id)
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise SystemExit(
            f"Failed to obtain access token ({e.code} {e.reason}):\n{body}\n"
            f"Check auth.tenant_id / auth.client_id in config.json and MAIL_CLIENT_SECRET."
        )
    return payload["access_token"]


def build_mime_message(sender_email: str, sender_name: str, reply_to: str, to_email: str,
                        subject: str, text_body: str, html_body: str) -> str:
    """multipart/alternative (plain text + HTML) with a List-Unsubscribe header.

    Graph's single-call sendMail action can't express either of these — only
    one body contentType, and internetMessageHeaders rejects anything not
    X-prefixed (confirmed live: InvalidInternetMessageHeader on a literal
    "List-Unsubscribe"). Needs the raw-MIME flow in send_via_graph instead.

    List-Unsubscribe only carries a mailto: form, not a one-click HTTPS URL —
    there's no backend endpoint yet that fulfils an unsubscribe request
    without further confirmation, and RFC 8058's List-Unsubscribe-Post is
    only valid alongside a real one-click endpoint.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((sender_name, sender_email))
    msg["To"] = to_email
    msg["Reply-To"] = reply_to
    msg["List-Unsubscribe"] = f"<mailto:{reply_to}?subject=unsubscribe>"
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg.as_string()


def send_via_graph(token: str, sender_email: str, sender_name: str, reply_to: str,
                    to_email: str, subject: str, text_body: str, html_body: str) -> None:
    """Sends via Graph's raw-MIME flow for a real multipart/alternative body
    and a List-Unsubscribe header, using the Mail.ReadWrite application
    permission (confirmed live in the issued token's roles claim on
    2026-09-06, after the admin-consent grant that had silently failed to
    complete was re-confirmed).

    Two calls, not the three-step create-then-PUT-$value sequence some docs
    suggest: PUT .../messages/{id}/$value turned out to 405
    ("OData request is not supported") — confirmed live. The actual working
    shape is POST .../messages with the MIME content, base64-encoded, as the
    body (Content-Type: text/plain) — this creates the message fully
    populated in one call — then POST .../messages/{id}/send.
    """
    mime_content = build_mime_message(sender_email, sender_name, reply_to, to_email, subject, text_body, html_body)
    mime_b64 = base64.b64encode(mime_content.encode("utf-8"))
    auth_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base_url = f"https://graph.microsoft.com/v1.0/users/{urllib.parse.quote(sender_email)}/messages"

    def _call(url, data, headers, method="POST"):
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            body_text = e.read().decode(errors="replace")
            raise RuntimeError(f"{e.code} {e.reason}: {body_text}")

    draft = json.loads(_call(base_url, mime_b64, {"Authorization": f"Bearer {token}", "Content-Type": "text/plain"}).decode())
    message_id = draft["id"]
    _call(f"{base_url}/{message_id}/send", b"", auth_headers)


def get_db_connection():
    """Lazily imports database/config.py so dry-run/preview never requires
    pyodbc or a reachable SQL Server — only --send does."""
    if str(DATABASE_DIR) not in sys.path:
        sys.path.insert(0, str(DATABASE_DIR))
    from config import get_connection  # noqa: E402
    return get_connection()


def get_or_create_campaign(conn, name: str, subject_template: str, template_path: str,
                            sender_email: str, learn_more_url: str) -> int:
    cursor = conn.cursor()
    cursor.execute("SELECT campaign_id FROM dbo.campaigns WHERE name = ?", name)
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        """
        INSERT INTO dbo.campaigns
            (name, subject_template, template_path, sender_email, learn_more_url, status)
        VALUES (?, ?, ?, ?, ?, 'sending')
        RETURNING campaign_id
        """,
        name, subject_template, template_path, sender_email, learn_more_url,
    )
    campaign_id = cursor.fetchone()[0]
    conn.commit()
    return campaign_id


def get_or_create_receiver(conn, org_name: str, email: str) -> int:
    cursor = conn.cursor()
    cursor.execute("SELECT receiver_id FROM dbo.campaign_receivers WHERE email = ?", email)
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        """
        INSERT INTO dbo.campaign_receivers (org_name, email, source)
        VALUES (?, ?, ?)
        RETURNING receiver_id
        """,
        org_name, email, "send_campaign.py (ad-hoc, not in leads CSV)",
    )
    receiver_id = cursor.fetchone()[0]
    conn.commit()
    return receiver_id


def record_send(conn, campaign_id: int, receiver_id: int, tracking_token: str,
                 status: str, error_detail: str = None) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO dbo.campaign_sends
            (campaign_id, receiver_id, tracking_token, status, error_detail)
        VALUES (?, ?, ?, ?, ?)
        """,
        campaign_id, receiver_id, tracking_token, status, error_detail,
    )
    conn.commit()


def mark_campaign_completed(conn, campaign_id: int) -> None:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE dbo.campaigns SET status = 'completed' WHERE campaign_id = ? AND status = 'sending'",
        campaign_id,
    )
    conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="config.json", help="Path to config JSON (default: config.json)")
    parser.add_argument("--send", action="store_true", help="Actually send emails. Without this flag, runs a dry-run preview only.")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N leads (after filtering).")
    parser.add_argument("--resend", action="store_true", help="Ignore the sent-log and resend to everyone (still respects the unsubscribe list).")
    parser.add_argument("--preview-out", default=None, help="Write full rendered previews to this file instead of stdout.")
    parser.add_argument("--add-unsubscribe", metavar="EMAIL", default=None, help="Add an address to the suppression list and exit.")
    parser.add_argument("--secret-file", default="scret.txt", help="Path to a plain text file containing the client secret (default: scret.txt next to this script). Read fresh on every run, never stored elsewhere.")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = base_dir / config_path
    if not config_path.exists():
        raise SystemExit(
            f"Config file not found: {config_path}\n"
            f"Copy config.example.json to config.json and fill in your details first."
        )
    config = load_config(config_path)

    campaign = config["campaign"]
    sender = config["sender"]
    business = config["business"]
    auth_cfg = config["auth"]

    suppression_path = base_dir / campaign["suppression_path"]
    log_path = base_dir / campaign["log_path"]

    if args.add_unsubscribe:
        suppression_path.parent.mkdir(parents=True, exist_ok=True)
        with open(suppression_path, "a", encoding="utf-8") as f:
            f.write(args.add_unsubscribe.strip().lower() + "\n")
        print(f"Added {args.add_unsubscribe} to {suppression_path}")
        return

    csv_path = Path(campaign["csv_path"])
    if not csv_path.is_absolute():
        csv_path = base_dir / csv_path
    template_path = base_dir / campaign["template_path"]
    text_template_path = template_path.with_suffix(".txt")

    leads = load_leads(csv_path, campaign["name_column"], campaign["email_column"])
    suppressed = load_suppression(suppression_path)
    already_sent = set() if args.resend else load_already_sent(log_path)

    leads = [l for l in leads if l["email"].lower() not in suppressed and l["email"].lower() not in already_sent]
    if args.limit is not None:
        leads = leads[: args.limit]

    print(f"Leads file: {csv_path}")
    print(f"Eligible recipients this run: {len(leads)} (suppressed: {len(suppressed)}, already sent: {len(already_sent)})")

    if not leads:
        print("Nothing to do.")
        return

    if args.send:
        blocked = [l for l in leads if l["email"].lower() not in ALLOWED_SEND_RECIPIENTS]
        if blocked:
            raise SystemExit(
                "Refusing to send: real campaign sends are currently restricted to "
                f"{', '.join(sorted(ALLOWED_SEND_RECIPIENTS))} only (policy guardrail, not a bug).\n"
                f"{len(blocked)} recipient(s) in this run fall outside that list, e.g. {blocked[0]['email']}.\n"
                "Dry-run/preview is unaffected — only --send is blocked. "
                "Edit ALLOWED_SEND_RECIPIENTS in send_campaign.py once sending the real campaign is authorized."
            )
        run_preflight_checklist(
            sender["email"], business, sender, len(leads),
            campaign.get("max_send_per_run", DEFAULT_MAX_SEND_PER_RUN),
        )

    template = template_path.read_text(encoding="utf-8")
    if not text_template_path.exists():
        raise SystemExit(
            f"Plain-text template not found: {text_template_path}\n"
            f"Every HTML template needs a plain-text sibling (same name, .txt extension) "
            f"for the multipart/alternative message — see marketing/email_template.txt."
        )
    text_template = text_template_path.read_text(encoding="utf-8")

    tracking_base_url = campaign.get("tracking_base_url", "").rstrip("/")

    if not args.send:
        print("\n--- DRY RUN (no emails will be sent; pass --send to actually send) ---\n")
        out_lines = []
        for lead in leads:
            preview_token = "PREVIEW-" + uuid.uuid4().hex[:12]
            subject = render(campaign["subject"], agent_name=lead["name"])
            render_fields = dict(
                agent_name=lead["name"],
                sender_name=sender["name"],
                reply_to=sender["reply_to"],
                business_name=business["name"],
                business_address=business["address"],
                tracking_pixel_url=f"{tracking_base_url}/t/open/{preview_token}.png",
                tracking_click_url=f"{tracking_base_url}/t/click/{preview_token}",
            )
            html_body = render(template, **render_fields)
            text_body = render(text_template, **render_fields)
            out_lines.append(
                f"To: {lead['email']}\nSubject: {subject}\n\n"
                f"--- text/plain part ---\n{text_body}\n"
                f"--- text/html part ---\n{html_body}\n{'=' * 60}\n"
            )
        text = "\n".join(out_lines)
        if args.preview_out:
            Path(args.preview_out).write_text(text, encoding="utf-8")
            print(f"Wrote {len(leads)} previews to {args.preview_out}")
        else:
            print(text)
        return

    secret_path = Path(args.secret_file)
    if not secret_path.is_absolute():
        secret_path = base_dir / secret_path
    if not secret_path.exists():
        raise SystemExit(
            f"Client secret file not found: {secret_path}\n"
            f"Put the client secret in this file (plain text, no quotes) before using --send. "
            f"It is read fresh on every run and never stored elsewhere."
        )
    client_secret = secret_path.read_text(encoding="utf-8").strip()
    if not client_secret:
        raise SystemExit(f"Client secret file is empty: {secret_path}")

    print(f"\n--- SENDING to {len(leads)} recipient(s) as {sender['email']} via Microsoft Graph ---\n")
    confirm = input(f"Type SEND to confirm sending to {len(leads)} real recipients: ")
    if confirm.strip() != "SEND":
        print("Aborted.")
        return

    token = get_graph_token(auth_cfg["tenant_id"], auth_cfg["client_id"], client_secret)

    conn = get_db_connection()
    campaign_id = get_or_create_campaign(
        conn, campaign["name"], campaign["subject"], campaign["template_path"],
        sender["email"], campaign["learn_more_url"],
    )

    sent_count = 0
    for lead in leads:
        tracking_token = str(uuid.uuid4())
        subject = render(campaign["subject"], agent_name=lead["name"])
        render_fields = dict(
            agent_name=lead["name"],
            sender_name=sender["name"],
            reply_to=sender["reply_to"],
            business_name=business["name"],
            business_address=business["address"],
            tracking_pixel_url=f"{tracking_base_url}/t/open/{tracking_token}.png",
            tracking_click_url=f"{tracking_base_url}/t/click/{tracking_token}",
        )
        html_body = render(template, **render_fields)
        text_body = render(text_template, **render_fields)
        receiver_id = get_or_create_receiver(conn, lead["name"], lead["email"])
        try:
            send_via_graph(token, sender["email"], sender["name"], sender["reply_to"], lead["email"], subject, text_body, html_body)
            append_log(log_path, lead["email"], lead["name"], "sent")
            record_send(conn, campaign_id, receiver_id, tracking_token, "sent")
            sent_count += 1
            print(f"Sent to {lead['email']}")
        except Exception as e:
            append_log(log_path, lead["email"], lead["name"], "failed", str(e))
            record_send(conn, campaign_id, receiver_id, tracking_token, "failed", str(e))
            print(f"FAILED to {lead['email']}: {e}", file=sys.stderr)
        time.sleep(campaign.get("delay_seconds", 5))

    mark_campaign_completed(conn, campaign_id)
    conn.close()
    print(f"\nDone. Sent {sent_count}/{len(leads)}. Log: {log_path}")


if __name__ == "__main__":
    main()

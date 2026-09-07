"""
Generates a campaign send report (delivery, opens, clicks, with a
bot-vs-human signal classification) by reading directly from the
production Supabase database, and renders it into template.html for
publishing as an Artifact. Read-only — never writes to the database.

Usage:
    python generate_report.py --list
    python generate_report.py --campaign-id 6 --out report.html
    python generate_report.py --campaign-name "Production Batch 1" --out report.html
"""

import argparse
import html
import ipaddress
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def find_repo_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / "database" / "config.py").exists():
            return parent
    raise SystemExit(
        "Could not locate the repo root (no database/config.py found in any parent "
        f"directory of {start})."
    )


REPO_ROOT = find_repo_root(SCRIPT_DIR)
sys.path.insert(0, str(REPO_ROOT / "database"))
from config import get_connection  # noqa: E402

BOT_UA_MARKERS = [
    "bot", "spam", "scan", "crawl", "monitor", "checker", "antispam",
    "safelink", "proofpoint", "mimecast", "barracuda",
]
PROXY_UA_MARKERS = [
    "googleimageproxy", "ggpht.com", "outlook.com image proxy",
    "microsoft office existence discovery",
]


def is_private_ip(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


def classify_event(user_agent: str, ip_address: str) -> str:
    """'bot', 'proxy', or 'engaged' for a single open/click event, on its
    own signal (user-agent, IP) — call-site logic in build_report() then
    overrides this with 'bot' when a send's click precedes its open,
    since that ordering itself is a stronger tell than either UA alone."""
    ua = (user_agent or "").lower()
    if any(m in ua for m in BOT_UA_MARKERS):
        return "bot"
    if any(m in ua for m in PROXY_UA_MARKERS):
        return "proxy"
    if is_private_ip(ip_address or ""):
        return "bot"
    return "engaged"


def fetch_campaign(conn, campaign_id=None, campaign_name=None):
    cursor = conn.cursor()
    if campaign_id is not None:
        cursor.execute(
            "SELECT campaign_id, name, status, sender_email, learn_more_url, created_at "
            "FROM dbo.campaigns WHERE campaign_id = ?",
            campaign_id,
        )
    else:
        cursor.execute(
            "SELECT campaign_id, name, status, sender_email, learn_more_url, created_at "
            "FROM dbo.campaigns WHERE name ILIKE ? ORDER BY campaign_id DESC",
            f"%{campaign_name}%",
        )
    rows = cursor.fetchall()
    if not rows:
        raise SystemExit(
            f"No campaign found for "
            f"{'campaign_id=' + str(campaign_id) if campaign_id is not None else 'name~=' + repr(campaign_name)}. "
            f"Run with --list to see available campaigns."
        )
    if len(rows) > 1:
        options = "\n".join(f"  {r.campaign_id}: {r.name} ({r.status})" for r in rows)
        raise SystemExit(f"Multiple campaigns match that name — use --campaign-id instead:\n{options}")
    return rows[0]


def fetch_sends(conn, campaign_id):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT cs.send_id, cs.receiver_id, cr.org_name, cr.email, cs.status,
               cs.sent_at, cs.tracking_token, cs.error_detail
        FROM dbo.campaign_sends cs
        JOIN dbo.campaign_receivers cr ON cr.receiver_id = cs.receiver_id
        WHERE cs.campaign_id = ?
        ORDER BY cs.sent_at
        """,
        campaign_id,
    )
    return cursor.fetchall()


def fetch_events(conn, send_ids):
    if not send_ids:
        return [], []
    placeholders = ",".join(["?"] * len(send_ids))
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT send_id, opened_at, ip_address, user_agent FROM dbo.campaign_opens "
        f"WHERE send_id IN ({placeholders}) ORDER BY opened_at",
        *send_ids,
    )
    opens = cursor.fetchall()
    cursor.execute(
        f"SELECT send_id, clicked_at, target_url, ip_address, user_agent FROM dbo.campaign_clicks "
        f"WHERE send_id IN ({placeholders}) ORDER BY clicked_at",
        *send_ids,
    )
    clicks = cursor.fetchall()
    return opens, clicks


def aggregate_signal(send_id, opens, clicks):
    """Returns (signal, log_entries) for one send: signal is 'engaged',
    'proxy', 'bot', or 'none'. A click timestamped before that send's
    earliest open overrides every individual event's own UA/IP
    classification to 'bot' for this send — a human opens an email before
    clicking a link inside it, so the reverse order is itself the tell,
    regardless of how legitimate either event's user-agent looks alone."""
    my_opens = [o for o in opens if o.send_id == send_id]
    my_clicks = [c for c in clicks if c.send_id == send_id]
    if not my_opens and not my_clicks:
        return "none", []

    earliest_open = min((o.opened_at for o in my_opens), default=None)
    earliest_click = min((c.clicked_at for c in my_clicks), default=None)
    ordering_anomaly = (
        earliest_open is not None and earliest_click is not None and earliest_click < earliest_open
    )

    classifications = []
    log_entries = []
    for o in my_opens:
        c = "bot" if ordering_anomaly else classify_event(o.user_agent, o.ip_address)
        classifications.append(c)
        log_entries.append(("open", o.opened_at, o.ip_address, o.user_agent, c))
    for c_ in my_clicks:
        c = "bot" if ordering_anomaly else classify_event(c_.user_agent, c_.ip_address)
        classifications.append(c)
        log_entries.append(("click", c_.clicked_at, c_.ip_address, c_.user_agent, c))

    if "engaged" in classifications:
        signal = "engaged"
    elif "proxy" in classifications:
        signal = "proxy"
    else:
        signal = "bot"
    return signal, log_entries


SIGNAL_BADGE = {
    "engaged": ('<span class="badge engaged">Engaged</span>', "Confirmed engagement"),
    "proxy": ('<span class="badge proxy">Proxy open</span>', "Mail-client image proxy"),
    "bot": ('<span class="badge bot">Automated</span>', "Mail-security scanner"),
    "none": ('<span class="badge none">No events yet</span>', "No events yet"),
}


def esc(value) -> str:
    return html.escape(str(value)) if value is not None else ""


def build_report(campaign, sends, opens, clicks) -> str:
    template = (SCRIPT_DIR / "template.html").read_text(encoding="utf-8")

    total_count = len(sends)
    sent_count = sum(1 for s in sends if s.status == "sent")
    open_count = len(opens)
    click_count = len(clicks)

    recipient_rows = []
    log_rows = []
    engaged_count = 0
    failed_sends = []

    all_log_entries = []
    for s in sends:
        signal, log_entries = aggregate_signal(s.send_id, opens, clicks)
        if signal == "engaged":
            engaged_count += 1
        if s.status != "sent":
            failed_sends.append(s)
        for entry in log_entries:
            all_log_entries.append((s.org_name, *entry))

        delivery_badge = (
            '<span class="badge sent">Sent</span>'
            if s.status == "sent"
            else f'<span class="badge failed">{esc(s.status.title())}</span>'
        )
        signal_badge, _ = SIGNAL_BADGE[signal]
        recipient_rows.append(
            f'          <tr>\n'
            f'            <td class="org">{esc(s.org_name)}</td>\n'
            f'            <td class="email">{esc(s.email)}</td>\n'
            f'            <td class="time">{esc(s.sent_at.strftime("%H:%M:%S"))}</td>\n'
            f'            <td>{delivery_badge}</td>\n'
            f'            <td>{signal_badge}</td>\n'
            f'          </tr>'
        )

    all_log_entries.sort(key=lambda e: e[2])
    for org_name, ev_type, ts, ip, ua, classification in all_log_entries:
        ev_class = "click" if ev_type == "click" else "open"
        log_rows.append(
            f'      <div class="log-row">\n'
            f'        <span class="ev {ev_class}">{ev_type.upper()}</span>\n'
            f'        <span class="who">{esc(ts.strftime("%H:%M:%S"))} · {esc(org_name)} · {esc(ip)}</span>\n'
            f'        <span class="ua">{esc(ua)}</span>\n'
            f'      </div>'
        )
    log_rows_html = "\n".join(log_rows) if log_rows else '      <div class="log-empty">No open or click events recorded yet.</div>'

    # Signal callout: what to make of the numbers above, in one place.
    if failed_sends:
        callout_class, callout_title = "warn", f"{len(failed_sends)} send(s) failed — check these before anything else"
        callout_body = "".join(
            f'<p><strong>{esc(s.org_name)}</strong> (<span class="mono">{esc(s.email)}</span>): {esc(s.error_detail or "no error detail recorded")}</p>'
            for s in failed_sends
        )
    elif engaged_count > 0:
        callout_class, callout_title = "good", f"{engaged_count} of {total_count} recipient(s) show confirmed human engagement"
        callout_body = "<p>At least one open or click traced to a plausible human signal (public IP, ordinary browser user-agent, normal open-then-click sequencing) rather than automated scanning infrastructure.</p>"
    elif open_count or click_count:
        callout_class, callout_title = "warn", "Recorded signal so far looks automated, not human"
        callout_body = (
            "<p>Every open/click event traces to mail-security or proxy infrastructure — a spam-scanner user-agent, "
            "a known image-proxy service, a private-range IP, or a click timestamped before that recipient's own open "
            "(the reverse of how a human reads an email, then clicks inside it).</p>"
            "<p>This is normal in the first hours after a cold send. Genuine opens typically land hours to days later — "
            "treat this window as too early to read.</p>"
        )
    else:
        callout_class, callout_title = "info", "No engagement recorded yet"
        callout_body = "<p>No open or click events yet. Too early to read anything into this — check back in 24–48 hours.</p>"

    callout_html = (
        f'  <div class="callout {callout_class}">\n'
        f'    <h2>{esc(callout_title)}</h2>\n'
        f'    {callout_body}\n'
        f'  </div>'
    )

    # Next steps: always grounded in DELIVERABILITY_PLAN.md's warm-up ramp.
    steps = []
    if failed_sends:
        steps.append("Resolve the failed send(s) above before sending anything further in this campaign or the next batch.")
    if engaged_count == 0:
        steps.append("Hold before sending the next batch — give this one 24–48 hours per the warm-up ramp in marketing/DELIVERABILITY_PLAN.md before scaling volume.")
    else:
        steps.append("This batch is showing real engagement — reasonable to proceed to the next step of the warm-up ramp in marketing/DELIVERABILITY_PLAN.md.")
    steps.append("Watch for bounces, not opens — re-check dbo.campaign_sends.status for this campaign in a day or two; a clean batch matters more right now than any pixel firing.")
    if open_count or click_count:
        steps.append("Don't discard automated scanner hits entirely — a security scanner fetching the link at all confirms the email cleared spam filtering and reached an inbox capable of scanning it.")
    next_steps_html = "\n".join(
        f'      <div class="step"><span class="dot">{i+1}</span><p>{s}</p></div>'
        for i, s in enumerate(steps)
    )

    def day_month_year(dt):
        return f"{dt.day} {dt.strftime('%b %Y')}"  # %-d isn't portable (missing on Windows)

    sent_times = [s.sent_at for s in sends]
    if sent_times:
        start, end = min(sent_times), max(sent_times)
        date_str = day_month_year(start)
        if start.date() == end.date() and start != end:
            sent_range = f"Sent {date_str}, {start.strftime('%H:%M')}–{end.strftime('%H:%M')} UTC"
        elif start == end:
            sent_range = f"Sent {date_str}, {start.strftime('%H:%M')} UTC"
        else:
            sent_range = f"Sent {date_str} – {day_month_year(end)}"
    else:
        sent_range = "No sends recorded"

    learn_more_line = (
        f' · linking to <a href="{esc(campaign.learn_more_url)}">{esc(campaign.learn_more_url)}</a>'
        if campaign.learn_more_url else ""
    )

    status_class = campaign.status if campaign.status in ("completed", "sending", "draft") else "draft"

    replacements = {
        "%%PAGE_TITLE%%": esc(campaign.name),
        "%%CAMPAIGN_NAME%%": esc(campaign.name),
        "%%CAMPAIGN_ID%%": esc(campaign.campaign_id),
        "%%SENT_RANGE%%": esc(sent_range),
        "%%SENDER_EMAIL%%": esc(campaign.sender_email),
        "%%LEARN_MORE_LINE%%": learn_more_line,
        "%%STATUS_CLASS%%": status_class,
        "%%STATUS_LABEL%%": esc(campaign.status.title()),
        "%%SENT_COUNT%%": str(sent_count),
        "%%TOTAL_COUNT%%": str(total_count),
        "%%OPEN_COUNT%%": str(open_count),
        "%%CLICK_COUNT%%": str(click_count),
        "%%ENGAGED_COUNT%%": str(engaged_count),
        "%%SIGNAL_CALLOUT%%": callout_html,
        "%%RECIPIENT_ROWS%%": "\n".join(recipient_rows) if recipient_rows else '          <tr><td colspan="5" class="log-empty">No sends recorded for this campaign.</td></tr>',
        "%%LOG_ROWS%%": log_rows_html,
        "%%NEXT_STEPS%%": next_steps_html,
        "%%GENERATED_AT%%": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    return template


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--campaign-id", type=int, default=None)
    parser.add_argument("--campaign-name", default=None, help="Partial or full campaign name (case-insensitive)")
    parser.add_argument("--list", action="store_true", help="List recent campaigns and exit")
    parser.add_argument("--out", default=None, help="Path to write the rendered HTML report")
    args = parser.parse_args()

    conn = get_connection()

    if args.list:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.campaign_id, c.name, c.status, c.created_at,
                   (SELECT COUNT(*) FROM dbo.campaign_sends cs WHERE cs.campaign_id = c.campaign_id) AS send_count
            FROM dbo.campaigns c
            ORDER BY c.campaign_id DESC
            """
        )
        for row in cursor.fetchall():
            print(f"{row.campaign_id:>4}  {row.status:<10} {row.send_count:>3} send(s)  {row.name}")
        return

    if args.campaign_id is None and args.campaign_name is None:
        raise SystemExit("Provide --campaign-id, --campaign-name, or --list.")
    if not args.out:
        raise SystemExit("Provide --out <path> to write the report to.")

    campaign = fetch_campaign(conn, campaign_id=args.campaign_id, campaign_name=args.campaign_name)
    sends = fetch_sends(conn, campaign.campaign_id)
    opens, clicks = fetch_events(conn, [s.send_id for s in sends])
    conn.close()

    report_html = build_report(campaign, sends, opens, clicks)
    out_path = Path(args.out)
    out_path.write_text(report_html, encoding="utf-8")
    print(f"Wrote report for campaign {campaign.campaign_id} ({campaign.name}) to {out_path}")


if __name__ == "__main__":
    main()

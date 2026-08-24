"""
Backfills dbo.campaign_receivers from database/naplan_sydney_agent_leads.csv.

Some rows' Email cell isn't a real address — e.g. the Sprouts Academy row
holds "Not published - see https://sproutsacademy.com.au/... (chat/WhatsApp
contact)" instead. Since campaign_receivers.email is NOT NULL (and uniquely
indexed), those rows are skipped rather than inserted, and printed to stderr
as a report so the lead isn't silently lost — it just needs a real contact
enriched in manually later.

Idempotent: skips any email already present in dbo.campaign_receivers, so
re-running after the CSV gains new rows only inserts what's new.

Usage:
    python backfill_campaign_receivers.py
"""

import csv
import os
import re
import sys

from config import get_connection

CSV_PATH = os.path.join(os.path.dirname(__file__), "naplan_sydney_agent_leads.csv")
SOURCE_LABEL = "naplan_sydney_agent_leads.csv"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def extract_email(raw: str):
    """Same first-valid-email-token extraction as marketing/send_campaign.py,
    kept in sync deliberately rather than imported (the two live in separate
    top-level folders with no shared package)."""
    if not raw:
        return None
    for token in re.split(r"[\s,;()]+", raw):
        token = token.strip().strip(".,;")
        if EMAIL_RE.match(token):
            return token
    return None


def load_rows():
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    rows = load_rows()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT email FROM dbo.campaign_receivers")
    existing = {row[0].lower() for row in cursor.fetchall()}

    inserted = 0
    skipped_duplicate = 0
    skipped_no_email = []

    for row in rows:
        org_name = (row.get("Agent Name") or "").strip()
        email = extract_email(row.get("Email") or "")

        if not email:
            skipped_no_email.append((org_name, row.get("Email")))
            continue
        if email.lower() in existing:
            skipped_duplicate += 1
            continue

        cursor.execute(
            """
            INSERT INTO dbo.campaign_receivers
                (org_name, email, phone, address, region, source, selection_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            org_name,
            email,
            (row.get("Phone") or "").strip() or None,
            (row.get("Address") or "").strip() or None,
            (row.get("State/Region") or "").strip() or None,
            SOURCE_LABEL,
            (row.get("Reason for Selection") or "").strip() or None,
        )
        existing.add(email.lower())
        inserted += 1

    conn.commit()
    conn.close()

    print(f"Inserted {inserted} new receiver(s).")
    print(f"Skipped {skipped_duplicate} already-existing email(s).")
    if skipped_no_email:
        print(
            f"\nSkipped {len(skipped_no_email)} row(s) with no parseable email "
            f"(need manual follow-up):",
            file=sys.stderr,
        )
        for org_name, raw in skipped_no_email:
            print(f"  - {org_name}: {raw!r}", file=sys.stderr)


if __name__ == "__main__":
    main()

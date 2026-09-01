"""
One-off backfill: turns historical send records in sent_log.csv and
test_sent_log.csv (sends made before dbo.campaign_sends tracking existed)
into dbo.campaigns + dbo.campaign_sends rows, so that history isn't lost
once the DB becomes the source of truth for campaign sends.

These historical sends never had a tracking pixel/click link embedded in
the email, so there was never a real tracking_token at send time — a fresh
one is generated per row purely to satisfy the column's NOT NULL/unique
constraint. It will never see a real open or click; that's expected for
backfilled history, not a bug.

Idempotent: skips a (campaign, receiver, sent_at) combination already
present in dbo.campaign_sends, so re-running after either log file gains
new rows only inserts what's new.

Usage:
    python backfill_send_history.py
"""

import csv
import os
import sys
import uuid
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "database"))
from config import get_connection  # noqa: E402

BASE_DIR = os.path.dirname(__file__)

LOG_FILES = [
    ("sent_log.csv", "NAPLAN Licensing Outreach — Sydney Tutoring Centres (pre-tracking backfill)"),
    ("test_sent_log.csv", "NAPLAN Licensing Outreach — Test (pre-tracking backfill)"),
]


def get_or_create_campaign(conn, name: str) -> int:
    cursor = conn.cursor()
    cursor.execute("SELECT campaign_id FROM dbo.campaigns WHERE name = ?", name)
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        """
        INSERT INTO dbo.campaigns (name, subject_template, template_path, sender_email, status)
        VALUES (?, ?, ?, ?, 'completed')
        RETURNING campaign_id
        """,
        name,
        "(historical — subject not recorded pre-tracking)",
        "(historical — template not recorded pre-tracking)",
        "support@zcube.com.au",
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
        org_name, email, "backfill_send_history.py (ad-hoc)",
    )
    receiver_id = cursor.fetchone()[0]
    conn.commit()
    return receiver_id


def already_recorded(conn, campaign_id: int, receiver_id: int, sent_at: datetime) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM dbo.campaign_sends WHERE campaign_id = ? AND receiver_id = ? AND sent_at = ?",
        campaign_id, receiver_id, sent_at,
    )
    return cursor.fetchone() is not None


def parse_sent_at(raw: str) -> datetime:
    """sent_log.csv timestamps are UTC ISO-8601 (e.g. "...+00:00"). sent_at is
    TIMESTAMPTZ, so keep the tz-aware value rather than stripping it — a naive
    datetime would be interpreted in the session's local timezone instead."""
    return datetime.fromisoformat(raw)


def main():
    conn = get_connection()
    total_inserted = 0
    total_skipped = 0

    for filename, campaign_name in LOG_FILES:
        path = os.path.join(BASE_DIR, filename)
        if not os.path.exists(path):
            print(f"Skipping {filename} (not found)")
            continue

        campaign_id = get_or_create_campaign(conn, campaign_name)

        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = (row.get("email") or "").strip()
                name = (row.get("name") or "").strip()
                status = (row.get("status") or "sent").strip()
                detail = (row.get("detail") or "").strip() or None
                if not email:
                    continue
                sent_at = parse_sent_at(row["timestamp"])

                receiver_id = get_or_create_receiver(conn, name, email)

                if already_recorded(conn, campaign_id, receiver_id, sent_at):
                    total_skipped += 1
                    continue

                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO dbo.campaign_sends
                        (campaign_id, receiver_id, tracking_token, status, error_detail, sent_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    campaign_id, receiver_id, str(uuid.uuid4()), status, detail, sent_at,
                )
                conn.commit()
                total_inserted += 1

    conn.close()
    print(f"Inserted {total_inserted} historical send record(s), skipped {total_skipped} already-recorded.")


if __name__ == "__main__":
    main()

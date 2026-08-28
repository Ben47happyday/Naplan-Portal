"""
One-off data migration: copies every row out of the local SQL Server
"naplan-portal" database and into the hosted PostgreSQL database pointed
to by DATABASE_URL (see config.py), preserving primary keys so foreign
keys stay intact, then resets each Postgres identity sequence so future
inserts continue from the right number.

This is separate from schema.sql / create_schema.py: run those FIRST to
create empty tables on the Postgres side, then run this script to copy
the data across. Safe to re-run — every insert uses ON CONFLICT DO
NOTHING, so rows already migrated are skipped.

Requires pyodbc (for the SQL Server source) in addition to this repo's
normal psycopg2 dependency (for the Postgres target):
    pip install pyodbc

Usage:
    python migrate_to_postgres.py
    python migrate_to_postgres.py --source-server "localhost\\SQLEXPRESS"
"""

import argparse
import datetime
import uuid

import pyodbc

from config import get_connection as get_target_connection

# Tables in FK-safe order. pk_col is None for tables with no single
# identity primary key to reset a sequence for (a fixed-value PK, or a
# composite PK).
TABLES = [
    ("dbo.year_levels", None),
    ("dbo.domains", "domain_id"),
    ("dbo.questions", "question_id"),
    ("dbo.tests", "test_id"),
    ("dbo.test_questions", None),
    ("dbo.students", "student_id"),
    ("dbo.attempts", "attempt_id"),
    ("dbo.attempt_answers", "attempt_answer_id"),
    ("dbo.campaign_receivers", "receiver_id"),
    ("dbo.campaigns", "campaign_id"),
    ("dbo.campaign_sends", "send_id"),
    ("dbo.campaign_opens", "open_id"),
    ("dbo.campaign_clicks", "click_id"),
]


def get_source_connection(server, database):
    connection_string = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={server};"
        f"DATABASE={database};"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(connection_string)


def normalize(value):
    """SQL Server DATETIME2 columns hold UTC values (written via
    SYSUTCDATETIME()) but carry no timezone info — pyodbc returns them as
    naive datetimes. Tag them UTC explicitly so Postgres's timestamptz
    columns don't reinterpret them in the connection's session timezone.
    UNIQUEIDENTIFIER columns come back as uuid.UUID; Postgres's UUID type
    accepts the string form."""
    if isinstance(value, datetime.datetime) and value.tzinfo is None:
        return value.replace(tzinfo=datetime.timezone.utc)
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def migrate_table(src_conn, dst_conn, table, pk_col):
    src_cursor = src_conn.cursor()
    src_cursor.execute(f"SELECT * FROM {table}")
    columns = [d[0] for d in src_cursor.description]
    rows = [tuple(normalize(v) for v in row) for row in src_cursor.fetchall()]

    if not rows:
        print(f"{table}: nothing to migrate.")
        return

    col_list = ", ".join(columns)
    placeholders = ", ".join(["?"] * len(columns))
    insert_sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

    dst_cursor = dst_conn.cursor()
    dst_cursor.executemany(insert_sql, rows)
    dst_conn.commit()
    print(f"{table}: migrated {len(rows)} rows.")

    if pk_col:
        dst_cursor.execute(
            f"SELECT setval(pg_get_serial_sequence('{table}', '{pk_col}'), "
            f"COALESCE((SELECT MAX({pk_col}) FROM {table}), 1))"
        )
        dst_conn.commit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-server", default="localhost\\MANTEAUDEV",
                         help="SQL Server instance to migrate FROM (default matches the repo's local dev setup)")
    parser.add_argument("--source-database", default="naplan-portal")
    args = parser.parse_args()

    print(f"Source (SQL Server): {args.source_server} / {args.source_database}")
    src_conn = get_source_connection(args.source_server, args.source_database)

    print("Target (PostgreSQL): DATABASE_URL")
    dst_conn = get_target_connection()

    try:
        for table, pk_col in TABLES:
            migrate_table(src_conn, dst_conn, table, pk_col)
    finally:
        src_conn.close()
        dst_conn.close()

    print("Migration complete.")


if __name__ == "__main__":
    main()

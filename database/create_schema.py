"""
Runs schema.sql against the naplan-portal database using the connection
defined in config.py (Windows Authentication).

Usage:
    python create_schema.py
"""

import os
from config import get_connection_autocommit

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.sql")


def run_schema():
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        sql_script = f.read()

    # Split on GO batch separators, like SSMS/sqlcmd does
    batches = [b.strip() for b in sql_script.split("\nGO") if b.strip()]

    conn = get_connection_autocommit()
    cursor = conn.cursor()
    for batch in batches:
        try:
            cursor.execute(batch)
        except Exception as exc:
            print("Error running batch:")
            print(batch[:200])
            raise exc
    conn.close()
    print(f"Schema applied: {len(batches)} batches executed.")


if __name__ == "__main__":
    run_schema()

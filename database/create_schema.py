"""
Runs schema.sql against the naplan-portal PostgreSQL database using the
connection defined in config.py (DATABASE_URL).

Usage:
    python create_schema.py
"""

import os
from config import get_connection_autocommit

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.sql")


def run_schema():
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        sql_script = f.read()

    conn = get_connection_autocommit()
    cursor = conn.cursor()
    try:
        cursor.execute(sql_script)
    except Exception as exc:
        print("Error running schema.sql:")
        print(exc)
        raise
    finally:
        conn.close()
    print("Schema applied successfully.")


if __name__ == "__main__":
    run_schema()

"""
NAPLAN Prep Hub — database configuration.

Connects to a local SQL Server instance using Windows Authentication
(Trusted_Connection), targeting the 'naplan-portal' database.

Requires:
    pip install pyodbc
    ODBC Driver 17 (or 18) for SQL Server installed on the machine.

Usage:
    from config import get_connection
    conn = get_connection()
"""

import pyodbc

# --- Connection settings -----------------------------------------------
# SERVER: '.' / 'localhost' / 'localhost\\SQLEXPRESS' depending on your
# local instance name. Change if your SQL Server uses a named instance.
SERVER = "localhost\\MANTEAUDEV"
DATABASE = "naplan-portal"
DRIVER = "{ODBC Driver 17 for SQL Server}"

CONNECTION_STRING = (
    f"DRIVER={DRIVER};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    "Trusted_Connection=yes;"
)


def get_connection():
    """Return a new pyodbc connection using Windows Authentication."""
    return pyodbc.connect(CONNECTION_STRING)


def get_connection_autocommit():
    """Return a connection with autocommit enabled (useful for DDL scripts)."""
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    return conn


if __name__ == "__main__":
    # Quick connectivity check: run `python config.py`
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION;")
        row = cursor.fetchone()
        print("Connected successfully.")
        print(row[0])
        conn.close()
    except Exception as exc:
        print("Connection failed:")
        print(exc)

"""
NAPLAN Prep Hub — database configuration.

Connects to PostgreSQL using DATABASE_URL, targeting the 'dbo' schema
(kept as 'dbo' rather than Postgres's default 'public' purely so every
existing dbo.<table> reference in the app/scripts keeps working unchanged
after the migration off SQL Server).

Requires:
    pip install psycopg2-binary

Usage:
    from config import get_connection
    conn = get_connection()

Connection string format (postgresql://user:password@host:5432/dbname),
set via the DATABASE_URL environment variable — see .env.example. Local
dev can point DATABASE_URL at a local Postgres instance; production
points it at the hosted instance (e.g. Render/Neon/Supabase/RDS).
"""

import os

import psycopg2
import psycopg2.extras

# Load .env from the repo root (a no-op if python-dotenv already loaded it,
# e.g. via backend/app.py) so standalone scripts under database/ also pick
# up DATABASE_URL without needing it exported in the shell.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

DATABASE_URL = os.environ.get("DATABASE_URL")


class Cursor(psycopg2.extras.NamedTupleCursor):
    """A psycopg2 cursor that accepts the pyodbc-style call conventions
    this codebase was written against, so query code ported from SQL
    Server doesn't need every call site rewritten:

      - '?' placeholders (pyodbc/T-SQL style) are translated to psycopg2's
        '%s' before executing.
      - params may be passed as a single list/tuple (cursor.execute(sql,
        params)) or as separate positional arguments
        (cursor.execute(sql, a, b, c)) — both pyodbc-supported forms.

    Rows come back as namedtuples (row.column_name), matching pyodbc's
    Row objects, so downstream attribute-style access is unchanged too.
    """

    def execute(self, sql, *params):
        if len(params) == 1 and isinstance(params[0], (list, tuple)):
            params = params[0]
        pg_sql = sql.replace("?", "%s")
        return super().execute(pg_sql, params if params else None)

    def executemany(self, sql, seq_of_params):
        return super().executemany(sql.replace("?", "%s"), seq_of_params)


def get_connection():
    """Return a new psycopg2 connection using DATABASE_URL."""
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env and fill in "
            "your PostgreSQL connection string."
        )
    return psycopg2.connect(DATABASE_URL, cursor_factory=Cursor)


def get_connection_autocommit():
    """Return a connection with autocommit enabled (useful for DDL scripts)."""
    conn = get_connection()
    conn.autocommit = True
    return conn


if __name__ == "__main__":
    # Quick connectivity check: run `python config.py`
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        row = cursor.fetchone()
        print("Connected successfully.")
        print(row[0])
        conn.close()
    except Exception as exc:
        print("Connection failed:")
        print(exc)

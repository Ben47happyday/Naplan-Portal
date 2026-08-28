# Naplan-Portal

## Database: PostgreSQL

The app runs against PostgreSQL (see `database/schema.sql`, `database/config.py`).
Objects live under a `dbo` schema (not Postgres's default `public`) so the
`dbo.<table>` references throughout the app/scripts didn't need renaming
after moving off the original SQL Server database.

Local setup:
1. `pip install -r backend/requirements.txt`
2. Copy `.env.example` to `.env` and set `DATABASE_URL` to your Postgres instance.
3. `cd database && python create_schema.py` to create the schema.
4. `python seed_data.py` (and the other `seed_*`/`generate_bulk_bank.py` scripts as needed) to populate content.

### Migrating existing data off SQL Server

If you have an existing local SQL Server `naplan-portal` database with real
data (student accounts, attempt history, question bank), run
`database/migrate_to_postgres.py` **after** `create_schema.py` has created
the empty tables on the Postgres side. It copies every row across via
`pyodbc` (source) + `psycopg2` (target), preserving primary keys and
resetting Postgres's identity sequences. Safe to re-run.

```
pip install pyodbc   # only needed for this one migration script
python database/migrate_to_postgres.py
```

## Deploying the web portal online

`Procfile` + `render.yaml` are set up for [Render.com](https://render.com)
as a default — a free web service plus a free managed Postgres database,
provisioned together from one Blueprint. This is a starting point, not a
requirement: any host that runs a Python/Flask app behind gunicorn, pointed
at a Postgres `DATABASE_URL`, works (Railway, Fly.io, Azure App Service,
etc.), and the Postgres database itself can just as easily live on Neon,
Supabase, or RDS instead of Render's.

To deploy on Render:
1. Push this repo to GitHub.
2. In the Render dashboard: **New → Blueprint**, point it at the repo.
3. Render provisions the web service and the Postgres database from
   `render.yaml` and wires `DATABASE_URL` between them automatically.
4. Once it's live, run `database/create_schema.py` (and
   `migrate_to_postgres.py` if migrating existing data) with `DATABASE_URL`
   set to the new hosted database's connection string.

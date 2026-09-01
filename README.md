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

**Recommended for launch: Render (free web) + Supabase (free Postgres, Sydney) = $0/month.**
Render's own free Postgres tier auto-deletes 30 days after creation, which
makes it unsuitable for anything meant to stay live — so `render.yaml`
deploys only the web service; the database is a separate free Supabase
project in the Sydney region, keeping student data hosted in Australia.
The tradeoff: Render's free web service sleeps after 15 minutes with no
traffic (~30-60s to wake), and Supabase pauses a free project entirely
after 7 days with **no database activity** (it stays paused until manually
resumed from the dashboard — not just a slow wake-up). Both are solved by
the free uptime pinger set up below, so in practice neither ever triggers
once it's running.

To deploy:
1. Create a free Supabase project at [supabase.com](https://supabase.com),
   choosing the **Sydney (ap-southeast-2)** region, and copy its Postgres
   connection string (Project Settings → Database → Connection string →
   URI). Use the pooled "Transaction" connection string if offered — it
   suits a small web app's short-lived connections better than the direct
   one.
2. Push this repo to GitHub.
3. In the Render dashboard: **New → Blueprint**, point it at the repo, and
   when prompted for `DATABASE_URL`, paste in the Supabase connection string.
4. Once it's live, run `database/create_schema.py` (and
   `migrate_to_postgres.py` if migrating existing data) with `DATABASE_URL`
   set to that same Supabase connection string.
5. Set up the uptime pinger (below) — without it, the free tier's cold
   starts and 7-day pause are unavoidable.

### Uptime pinger (keeps the $0 setup actually usable)

The app exposes `GET /healthz`, which does a real `SELECT 1` against the
database — unlike `/`, which is a static file and never touches Postgres.
Pinging `/healthz` keeps both Render and Supabase active:

1. Sign up free at [UptimeRobot](https://uptimerobot.com) (or
   [cron-job.org](https://cron-job.org) — either works, no card needed).
2. Add a new HTTP(s) monitor:
   - URL: `https://<your-render-app>.onrender.com/healthz`
   - Interval: **5-10 minutes** (well under Render's 15-minute sleep
     threshold; far more often than Supabase's 7-day pause needs)
3. Save. That's it — as a side effect this also gives you free uptime
   alerts if the site ever goes down.

### If/when it needs to be always-on

Once there's real traffic and the cold-start/pause dance (or babysitting
the pinger) isn't worth it, here's what was actually compared before
landing on the $0 setup — prices as surveyed August 2026, always worth
re-checking before committing:

| Option | Cost | Notes |
|---|---|---|
| **Render free + Supabase free (Sydney)** (recommended) | **$0/mo** | AU-hosted; needs the uptime pinger above to avoid cold starts/pause |
| Render free + Neon free | $0/mo | Also $0, no pause to babysit, but no confirmed AU region |
| Render Starter ($7) + Supabase free | $7/mo | Web always-on; DB stays free (pinger still recommended) |
| Render free + Render Postgres free | $0/mo *(30 days only)* | Render's free DB is deleted after a 30-day + 14-day grace window — avoid for anything long-lived |
| Railway Hobby | $5/mo minimum, usage-billed on top | A Postgres instance alone tends to burn through the $5 credit within days; ends up costing more than it looks |
| Fly.io (web + Postgres) | ~$4-5/mo minimum | No free tier at all in 2026; smallest always-on VM + smallest Postgres, pay-as-you-go from day one |
| Render Starter + DigitalOcean Postgres (Sydney) | $22/mo | Everything always-on, AU-hosted, flat predictable billing, no free-tier expiry/pause logic anywhere |
| Render Standard + Supabase Pro | $50/mo | Adds backups + SLA once there's enough traffic to justify it |

This app is small (a Flask app serving static pages + a lightweight JSON
API, low expected traffic pre-launch), so the free tier is genuinely
adequate — no need to default to a paid always-on setup before there's
traffic that needs it.

# FRI backend

FastAPI + PostgreSQL. See `../ARCHITECTURE.md` for the full picture.

## Local setup

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# One-time, as a Postgres superuser: create the database and the two roles
# the RLS design depends on (see db/roles.sql for what/why).
sudo -u postgres psql -c "CREATE DATABASE fri_dev;"
sudo -u postgres psql -f db/roles.sql
sudo -u postgres psql -d fri_dev -c "ALTER DATABASE fri_dev OWNER TO fri_migrator;"
sudo -u postgres psql -d fri_dev -c "GRANT ALL ON SCHEMA public TO fri_migrator; GRANT USAGE ON SCHEMA public TO fri_app;"

cp .env.example .env   # adjust if your local roles use different passwords

alembic upgrade head
python scripts/seed_reference_data.py

uvicorn app.main:app --reload
```

Then `POST /auth/login` with one of the seeded test accounts (see
`scripts/seed_reference_data.py` — not real credentials, replace before any
non-local use) and `GET /auth/me` with the resulting cookie.

## Why two DB roles

The app connects as `fri_app`, a role with `NOBYPASSRLS` that is not the
table owner — so the Row-Level Security policies on `employee` and
`departure_event` actually constrain it. Migrations run as `fri_migrator`,
which owns the tables and therefore bypasses RLS, as an owner/admin role
should. Connecting the app as the owner would silently defeat RLS.

## Tests

None yet — Module 1 is schema + auth only per the kickoff brief. Add a test
suite alongside the first router that does real query logic (directory
listing), so the sort/filter column allow-list has something to test
against.

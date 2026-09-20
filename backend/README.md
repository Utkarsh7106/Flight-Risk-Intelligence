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

The seed script also creates ~18 illustrative employee rows spread across
all 5 business units, so `GET /employees` has something realistic to look
at through `/docs` — not the eventual ~320-row baseline panel (see
ARCHITECTURE.md).

## Why two DB roles

The app connects as `fri_app`, a role with `NOBYPASSRLS` that is not the
table owner — so the Row-Level Security policies on `employee` and
`departure_event` actually constrain it. Migrations run as `fri_migrator`,
which owns the tables and therefore bypasses RLS, as an owner/admin role
should. Connecting the app as the owner would silently defeat RLS.

## Tests

`backend/tests/` — pytest, run against the real local `fri_dev` database
(no mocking; the point is proving Row-Level Security holds through the
real request path, not a stand-in for it). Requires the venv, migrations,
and seed data already set up per the steps above.

```bash
cd backend
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
.venv/Scripts/python.exe -m pytest -v
```

Covers: JWT expiry, and the employee directory endpoint's BU isolation
(HR sees all, BU Head sees only their own BU, cross-BU access by ID and
by filter both return empty/404 rather than an error, compensation
fields are never returned for a row the caller can't see, gender/DOB/phone
never appear in any response, a manager in a different BU resolves to
`null` rather than leaking a name, and a missing RLS session context
returns zero rows rather than erroring).

Module 2 (Workforce Health): the scoring model's math against
hand-calculated inputs, a structural regression test proving forbidden
attributes (gender/BU/department/manager identity/location) genuinely
cannot reach `score_employee()`, the recommendation engine's rule
coverage, the fairness-audit statistics engine, RLS isolation on the new
score endpoints (mirroring the directory tests above), and an adversarial
check that every seeded BU Head account is refused the fairness-audit
endpoint (HR-only, non-negotiable — see `MODULE2_REFERENCE.md`).

# FRI backend

FastAPI + PostgreSQL. See `../ARCHITECTURE.md` for the full picture.

## Local setup

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium   # Module 4's PDF export — see "PDF export" below

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

Module 3 (Risk Analysis / ML demo): a structural regression test
mirroring Module 2's, proving `RawSignals`/`Features` (the label
generator's and model's own input types) genuinely cannot carry
gender/BU/department/manager/location, plus a test proving the label
is not a deterministic function of the features (same feature values,
many noise draws, must show real spread — see `MODULE3_REFERENCE.md`),
and RLS isolation on `/risk-analysis/*` (mirroring the directory/
workforce-health tests), including that `employment_status='separated'`
rows (labeled training examples) 404 for every role, HR included.

Module 4 (departure capture + exports): the write path on
`POST /departure-events` (not just reads — a real 409 on double-recording,
422 on a pre-joining departure_date and on a reason_category that doesn't
match its departure_type), that the `mark_employee_separated` trigger
actually flips `employee.employment_status`, that a newly-separated
employee is excluded from the default directory/Workforce Health views
but reachable via `?employment_status=separated`/`all`, RLS isolation on
`/departure-events` (HR sees every BU, a BU Head only their own, and can
record a departure only for their own BU's employees — an honest 404 for
anyone else's, same as every other cross-BU lookup in this app), and on
`/exports/workforce-health`: correct data scoping in the *generated
report content itself* (not just a 200 status) for both an org-wide and
a single-BU export, that a BU Head's export is forced to their own BU
even if a different `business_unit_id` is requested, that no fairness-
audit content ever appears in an export, and a real (not mocked)
Chromium-rendered PDF via `format=pdf`.

## Module 3's offline pipeline

The synthetic dataset and trained model aren't built by the test suite
or by `seed_reference_data.py` — run these once, in order, after the
usual setup above (they need `requirements-ml.txt`, not part of the
app's runtime `requirements.txt`):

```bash
pip install -r requirements-ml.txt
python -m app.synthetic.generate   # ~3000-row synthetic workforce
python -m app.synthetic.train      # trains, evaluates, scores, persists SHAP
```

`generate` prints the calibrated intercept and realized departure rate;
`train` prints held-out ROC-AUC and a base-rate-matched precision/recall
readout. Re-running either is safe (both are idempotent/deterministic
under a fixed seed) and required after almost any change to
`app/synthetic/`. See `MODULE3_REFERENCE.md` for what these numbers mean
and why the label is generated the way it is.

## PDF export

`GET /exports/workforce-health?format=pdf` (Module 4) renders the exact
same self-contained HTML template `format=html` returns
(`app/exports/workforce_health_report.py`) through a real, headless
Chromium (`app/exports/pdf.py`), so the two formats can't visually drift
apart. This makes `playwright` a genuine **runtime** dependency of the
live API — unlike Module 3's offline-only ML libs, the PDF is generated
per live, RLS-scoped request, so it can't be precomputed — and it needs
its own browser binary: `playwright install chromium` once after
`pip install -r requirements.txt` (see "Local setup" above). A deployed
build (Render/Railway, per `ARCHITECTURE.md`) needs this same install
step wired into its build process; those hosts aren't behind a
restrictive proxy the way this project's dev sandbox sometimes is, so the
plain command works there. Never set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`
(`.env.example`) on a deployed build — it exists only for a dev sandbox
with a nonstandard pre-installed Chromium path; see `app/config.py`.

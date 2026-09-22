# Flight Risk Intelligence — Architecture

Proof-of-concept HR attrition dashboard for LS Digital. This document is a working reference, updated as modules land — not a spec written in advance.

## Stack

- **Backend**: FastAPI (Python 3.11+), SQLAlchemy 2.0, Alembic migrations, `psycopg` (v3) driver.
- **Database**: PostgreSQL 16, Row-Level Security enabled on employee-related tables.
- **Frontend**: React 19 + Vite 8 + TypeScript, react-router-dom. CSS Modules on top of design tokens translated from `design/stitch/DESIGN.md` — no CSS framework/UI kit dependency.
- **ML**: scikit-learn + SHAP (`TreeExplainer`) — Module 3 only, offline-only (`requirements-ml.txt`). Module 2 is a hand-weighted scorecard, not a model.
- **Charts**: Recharts.
- **PDF export**: Playwright's headless Chromium (Module 4) — a genuine runtime dependency, unlike the ML libs above.
- **Auth**: JWT (HS256, 15-minute access tokens, no refresh tokens), stored in an httpOnly/Secure cookie.
- No Java, C, or their "sister languages" anywhere in the stack.
- `starlette>=1.0.1` pinned (CVE-2026-48710) — see `backend/requirements.txt`.

## Branching

- `new-fri` — active development. All work lands here.
- `main` — only fast-forwarded once a module is fully built, tested, and confirmed deployment-ready. Deploys via Netlify/Vercel. Never pushed to directly.

## Repository layout

```
ARCHITECTURE.md
backend/
  app/
    config.py          # pydantic-settings: DATABASE_URL, JWT secret, CORS allowlist
    database.py         # SQLAlchemy engine/session, per-request RLS session vars
    models/              # SQLAlchemy ORM models — one module per table
    schemas/              # Pydantic request/response schemas
    security/              # password hashing, JWT encode/decode, auth dependencies
    routers/                # FastAPI routers: auth, employees (directory), workforce_health (Module 2), risk_analysis (Module 3), departure_events + exports (Module 4)
    scoring/                 # Module 2's pure logic: scoring model, recommendations, fairness audit; employee_scoring.py's fetch/peer-group/score helpers are shared with Module 4's export
    synthetic/                # Module 3's offline pipeline: dataset generation, label generator, feature engineering, model training + SHAP (see MODULE3_REFERENCE.md)
    exports/                     # Module 4's shareable-report template (one HTML template, reused for both the HTML and PDF export formats) and PDF rendering (see MODULE4_REFERENCE.md)
    main.py                     # app factory, CORS, router registration
  alembic/                    # schema migrations (source of truth for DB shape)
  scripts/
    seed_reference_data.py     # idempotent seed: business units, departments, test accounts
  db/
    roles.sql                   # documents the fri_migrator / fri_app role split for RLS
  requirements.txt
  .env.example
frontend/
  src/
    styles/                  # design tokens (tokens.css) translated from design/stitch/DESIGN.md
    components/
      ui/                     # reusable component library — Avatar, Badge, Card, Table, Button, form controls
      layout/                  # AppShell, Sidebar (single sidebar, no top navbar — locked guardrail)
      feedback/                 # full-page loading/error states
    context/
      AuthContext.tsx           # session state sourced from GET /auth/me, never from decoding the cookie
    api/                        # typed fetch client (credentials:'include' only, no token storage)
    routes/
      ProtectedRoute.tsx         # gates authenticated routes
    pages/
      auth/                       # login screen
      directory/                   # Employee Directory — table + card views
      workforce-health/            # Module 2: overview, employee drill-down, HR-only fairness audit; ExportControls.tsx is Module 4's export UI
      risk-analysis/                # Module 3: demonstration-dataset overview + per-employee SHAP drill-down
      departures/                    # Module 4: RLS-scoped departure list + record form
  .env.example
design/
  stitch/                          # Stitch design exports: 9 screens + DESIGN.md (design-system doc)
```

## Org structure (authoritative — replaces any placeholder data)

Two-level hierarchy: **Business Unit → Department**. Department names are only unique *within* a business unit (e.g. "Growth" exists under both "Business Function and Media" and "Enabling Functions" as distinct departments; "Finance" and "Finance and Accounting" are likewise distinct). The schema enforces uniqueness as `UNIQUE(business_unit_id, name)`, not a global uniqueness constraint on department name.

| Business Unit | Departments |
|---|---|
| Business Function and Media | Bidable Performance, Client Success, Growth and Strategy, Growth, Pragmatic Buying, SEO |
| Data Quark | Data Quark Sales, Digital Analytics, Product and Consulting, Unified Data Solutions |
| Enabling Functions | Finance, Growth, Marketing and PR, People Management |
| SP Creative | Administration, Finance and Accounting, Social, Strategy and Growth |
| UI/UX | Design |

## Schema shape (Module 1)

Tables: `business_unit`, `department`, `employee`, `app_user`, `departure_event`. Singular names throughout; `app_user` because `user` is a reserved word in Postgres.

- **business_unit** — reference data, the 5 rows above.
- **department** — reference data, FK'd to `business_unit`, the ~19 rows above.
- **employee** — the baseline panel target shape (~27 columns in the source dataset this build is anchored to). Holds a denormalized `business_unit_id` that a trigger keeps in sync with `department_id` (so it can never drift), a self-referential `manager_id`, and the fields the Module 2 scorecard and Module 3 model will read: tenure inputs (`date_of_joining`), `engagement_score`, `manager_effectiveness_score`, `ctc_annual`, promotion/increment dates, `performance_rating` (real range ~2.0–4.7, not a clean 1–5 scale), `grade` (L1–L6). `gender` is stored here but is excluded from Module 2's scoring function signature by design, and is only surfaced through a dedicated HR-only fairness-audit endpoint later — never through the ordinary directory view a BU Head sees.
- **app_user** — auth accounts. `role` is `hr` or `bu_head`; a `bu_head` row is scoped by `business_unit_id`. Role comes entirely from which account logs in — there is no role-toggle anywhere in the UI.
- **departure_event** — separation-event capture, built into the schema now even though no historical events exist yet. Snapshots `business_unit_id`/`department_id` at time of departure (so BU/department history is preserved even if org structure later changes), and a trigger flips the employee's `employment_status` to `separated` on insert. This is infrastructure only in V1 — the entry-mechanism UI is Module 4, and survival analysis is explicitly deferred until real events accumulate.

## The baseline dataset is not live data

The ~320-employee panel this build is anchored to was constructed by the original hackathon team as a stand-in for real HR data. It must never be described in UI copy or docs as real/live company data. It has no attrition/departure label — Module 2's scorecard and Module 3's model are both explicit about this rather than pretending otherwise.

## ML methodology guardrail

Module 2 is a transparent, hand-weighted scorecard computed on demand — not a trained model, and never presented as one. Its scoring function signature structurally excludes gender, BU, department, manager, and location as direct inputs. Those excluded attributes are retained for a separate fairness/proxy audit (disparate impact / proxy leakage via CTC, grade, dept-attrition-rate), gated behind an HR-only endpoint.

**Built** (see `MODULE2_REFERENCE.md` for the full reasoning): `app/scoring/model.py` (five-factor weighted scorecard: promotion stagnation, compensation trajectory vs. same-grade peers, engagement, manager effectiveness, a performance-recognition-gap bonus — 0-100 score, four risk bands, a genuine per-driver breakdown), `app/scoring/recommendations.py` (deterministic driver -> intervention lookup, no LLM involved), `app/scoring/fairness_audit.py` (group-distribution + manager-team checks with an honest small-sample confidence bucket), and `app/routers/workforce_health.py` (`/workforce-health/summary`, `/workforce-health/employees/{id}`, `/workforce-health/fairness-audit` — the last gated by `require_hr`, adversarially verified against every seeded BU Head account).

Module 3 trains a real model with SHAP explainability, on a separate, larger, synthetic dataset built on the same schema, own table namespace, clearly labeled in the UI as a demonstration dataset distinct from the baseline panel. IBM HR Attrition's correlation patterns inform label generation; names, BUs, and departments in the synthetic set still follow the Indian-names and real-org-structure rules below.

**Built** (see `MODULE3_REFERENCE.md` for the full reasoning, especially the label-generation approach): `app/synthetic/generate.py` (3000-row synthetic workforce, own `synthetic_employee` table, same RLS pattern as `employee`), `app/synthetic/label.py` (the departure label — a logistic/log-odds generator structurally and numerically unrelated to Module 2's linear scorecard, with Gaussian noise in log-odds space so the label is never a deterministic function of the features), `app/synthetic/features.py` (shared feature engineering, structurally excludes gender/BU/department/manager/location — same discipline as `app/scoring/model.py`'s `ScoringInputs`), `app/synthetic/train.py` (real stratified 80/20 train/test split, `RandomForestClassifier`, held-out ROC-AUC 0.728, real per-employee SHAP `TreeExplainer` values persisted for the active/current-workforce subset), and `app/routers/risk_analysis.py` (`/risk-analysis/summary`, `/risk-analysis/employees`, `/risk-analysis/employees/{id}` — same RLS/allow-list pattern as every other router; no fairness-audit endpoint here, that stays Module 2's). Offline-only ML dependencies (numpy/scikit-learn/shap) live in `backend/requirements-ml.txt`, separate from the app's runtime `requirements.txt` — predictions/SHAP are precomputed and persisted, not inferred per live request.

## Module 4 — departure capture + shareable exports

**Departure capture** (`app/routers/departure_events.py`) is the entry mechanism on top of `departure_event`/`mark_employee_separated`, both already present from Module 1 — no schema migration needed. A BU Head may record a departure for an employee in their own BU; HR for anyone — this mirrors, not invents, a decision Module 1 already made (`departure_event_bu_head_scoped`'s RLS policy was already `FOR ALL`, not just `SELECT`). `business_unit_id`/`department_id` are snapshotted server-side from the employee's current values, never accepted from the client. `GET /employees`'s `employment_status` now defaults to `"active"` (was unfiltered) so a separated employee doesn't silently mix into the ordinary directory — `"separated"`/`"all"` are explicit opt-ins.

**Shareable exports** (`app/routers/exports.py`, `GET /exports/workforce-health?format=html|pdf`) render one self-contained HTML template (`app/exports/workforce_health_report.py`) two ways: served directly as the HTML export, or printed to PDF by a real headless Chromium (`app/exports/pdf.py`, via `playwright`) — one template, so the two formats can't visually drift apart. `business_unit_id` is an additional filter on top of RLS; for a BU Head it's always forced server-side to their own BU regardless of what's requested, so their peer-group computation (not just row visibility) is correctly BU-scoped — see `app/scoring/employee_scoring.py`, extracted from `workforce_health.py` so the export can't silently diverge from what the live views compute. Deliberately excludes Module 3's demonstration dataset and the fairness audit from every export, in every scope, for every role — see `MODULE4_REFERENCE.md`. `playwright` is a genuine **runtime** dependency (in `requirements.txt`, not `-ml`) since the PDF is generated per live request and can't be precomputed; the backend host needs a `playwright install chromium` step at deploy time (see `backend/README.md`'s "PDF export").

## Security guardrails

- **Auth**: JWT HS256, 15-minute expiry, no refresh tokens, httpOnly + Secure cookie — never localStorage. Logout clears the cookie client-side but does not revoke the token server-side (no denylist) — a copied/stolen token remains valid for up to 15 minutes after logout. This is an accepted tradeoff for internal office use on shared/unlocked machines, where the realistic risk is device access rather than token interception in transit; deliberately not building revocation for that threat model.
- **Defense in depth**: an app-level role-scoping FastAPI dependency is the primary access control. Postgres Row-Level Security is a second, independent layer on `employee` and `departure_event` (see `backend/db/roles.sql`). The app connects as `fri_app`, a non-owner role with `NOBYPASSRLS`; migrations run as `fri_migrator`, the table owner. RLS policies read `current_setting('app.current_role', true)` / `current_setting('app.current_bu_id', true)`, set via `SET LOCAL` at the start of each request's transaction. If those session variables are unset, `current_setting(..., true)` returns `NULL` and every policy fails closed — no rows are visible.
- **Queries**: parameterized everywhere (SQLAlchemy Core/ORM bound parameters). Any sort/filter query param is validated against a hardcoded column allow-list — never `getattr()`-based dynamic sorting.
- **CORS**: explicit origin allowlist from config, never a wildcard. `allow_origins=["*"]` is never combined with `allow_credentials=True`. `expose_headers=["Content-Disposition"]` (added for Module 4's exports) is the one non-default header exposed to the frontend — found necessary live: without it, a cross-origin `fetch()` can't read the filename an export response sets, since `Content-Disposition` isn't in the browser's small CORS-safelisted header set by default.

## Deployment

Frontend and backend deploy to **different origins**, not a same-origin reverse proxy: frontend on Vercel or Netlify, backend on Render or Railway. This makes the auth cookie genuinely cross-site, which changes the cookie/CORS requirements from what a same-origin local setup would need:

- **Cookie**: `SameSite=None; Secure; HttpOnly`. `Secure` requires HTTPS, which Render/Railway provide by default — so this is just what production gets, no extra config. `Settings.environment` (`app/config.py`) defaults to `"production"`, which selects this. Setting `ENVIRONMENT=local` selects a relaxed dev-only pair instead (`SameSite=Lax`, no `Secure`) so login works over plain `http://localhost` without a local TLS cert. This flag must never be set on a deployed build — the default is the strict/safe behavior specifically so a forgotten env var fails safe, not open.
- **CORS**: explicit origin allowlist read from `CORS_ORIGINS` (config, not hardcoded), `allow_credentials=True`, never a wildcard — enforced by `Settings.cors_origin_list` raising if `"*"` appears. Once the frontend's Vercel/Netlify URL is chosen, it goes in that env var on the backend host; it is not yet fixed in code anywhere.
- **PDF export's Chromium** (Module 4): the backend host's build step needs `playwright install chromium` — Render/Railway both support a custom build command for this, but it's a real deploy-time step neither host provides automatically, unlike Postgres connectivity. `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` must stay unset on any deployed build (dev-sandbox-only override — see `backend/README.md`'s "PDF export" and `app/config.py`).

## UI guardrails

Single sidebar shell, no top navbar. Product name is "Flight Risk Intelligence" everywhere. HR gets an org-wide view; BU Heads get one shared template scoped by their login, not three hardcoded copies — the frontend's `useEmployeeDirectory` hook sends only the filters the user picked and renders back whatever the API returns; there is no client-side role/BU branching anywhere in it, by design (see `frontend/README.md`). Fixed layout for V1 — no drag/drop widget customization.

The frontend never touches the auth token directly: it relies entirely on the httpOnly session cookie (`credentials: 'include'` on every request) and sources "who is logged in" from `GET /auth/me`, never from decoding the cookie client-side.

## Names

All names — real, synthetic, or in AI-generated avatars — are Indian, never Western. No exceptions, in seed data, synthetic Module 3 data, or any example/placeholder text.

## Deferred to V2

Dataset upload / column-mapping, drag-drop widget customization, real External Market Intelligence backend, succession/bench-strength overlay, survival analysis.

# Flight Risk Intelligence — Architecture

Proof-of-concept HR attrition dashboard for LS Digital. This document is a working reference, updated as modules land — not a spec written in advance.

## Stack

- **Backend**: FastAPI (Python 3.11+), SQLAlchemy 2.0, Alembic migrations, `psycopg` (v3) driver.
- **Database**: PostgreSQL 16, Row-Level Security enabled on employee-related tables.
- **Frontend** (not started yet): React + Vite.
- **ML**: scikit-learn + SHAP (`TreeExplainer`) — Module 3 only. Module 2 is a hand-weighted scorecard, not a model.
- **Charts**: Recharts.
- **Auth**: JWT (HS256, 30-minute access tokens, no refresh tokens), stored in an httpOnly/Secure cookie.
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
    routers/                # FastAPI routers (auth first; directory/module routers land later)
    main.py                  # app factory, CORS, router registration
  alembic/                    # schema migrations (source of truth for DB shape)
  scripts/
    seed_reference_data.py     # idempotent seed: business units, departments, test accounts
  db/
    roles.sql                   # documents the fri_migrator / fri_app role split for RLS
  requirements.txt
  .env.example
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

Module 3 trains a real model with SHAP explainability, but on a separate, larger, synthetic dataset built on the same schema, own table namespace, clearly labeled in the UI as a demonstration dataset distinct from the baseline panel. IBM HR Attrition's correlation patterns inform label generation; names, BUs, and departments in the synthetic set still follow the Indian-names and real-org-structure rules below.

## Security guardrails

- **Auth**: JWT HS256, 30-minute expiry, no refresh tokens, httpOnly + Secure cookie — never localStorage.
- **Defense in depth**: an app-level role-scoping FastAPI dependency is the primary access control. Postgres Row-Level Security is a second, independent layer on `employee` and `departure_event` (see `backend/db/roles.sql`). The app connects as `fri_app`, a non-owner role with `NOBYPASSRLS`; migrations run as `fri_migrator`, the table owner. RLS policies read `current_setting('app.current_role', true)` / `current_setting('app.current_bu_id', true)`, set via `SET LOCAL` at the start of each request's transaction. If those session variables are unset, `current_setting(..., true)` returns `NULL` and every policy fails closed — no rows are visible.
- **Queries**: parameterized everywhere (SQLAlchemy Core/ORM bound parameters). Any sort/filter query param is validated against a hardcoded column allow-list — never `getattr()`-based dynamic sorting.
- **CORS**: explicit origin allowlist from config, never a wildcard. `allow_origins=["*"]` is never combined with `allow_credentials=True`.

## Deployment

Frontend and backend deploy to **different origins**, not a same-origin reverse proxy: frontend on Vercel or Netlify, backend on Render or Railway. This makes the auth cookie genuinely cross-site, which changes the cookie/CORS requirements from what a same-origin local setup would need:

- **Cookie**: `SameSite=None; Secure; HttpOnly`. `Secure` requires HTTPS, which Render/Railway provide by default — so this is just what production gets, no extra config. `Settings.environment` (`app/config.py`) defaults to `"production"`, which selects this. Setting `ENVIRONMENT=local` selects a relaxed dev-only pair instead (`SameSite=Lax`, no `Secure`) so login works over plain `http://localhost` without a local TLS cert. This flag must never be set on a deployed build — the default is the strict/safe behavior specifically so a forgotten env var fails safe, not open.
- **CORS**: explicit origin allowlist read from `CORS_ORIGINS` (config, not hardcoded), `allow_credentials=True`, never a wildcard — enforced by `Settings.cors_origin_list` raising if `"*"` appears. Once the frontend's Vercel/Netlify URL is chosen, it goes in that env var on the backend host; it is not yet fixed in code anywhere.

## UI guardrails (for when frontend work starts)

Single sidebar shell, no top navbar. Product name is "Flight Risk Intelligence" everywhere. HR gets an org-wide view; BU Heads get one shared template scoped by their login, not three hardcoded copies. Fixed layout for V1 — no drag/drop widget customization.

## Names

All names — real, synthetic, or in AI-generated avatars — are Indian, never Western. No exceptions, in seed data, synthetic Module 3 data, or any example/placeholder text.

## Deferred to V2

Dataset upload / column-mapping, drag-drop widget customization, real External Market Intelligence backend, succession/bench-strength overlay, survival analysis.

# Employee directory endpoint — design

Date: 2026-09-20
Status: approved

## Purpose

Module 1's first router with real query logic. Exposes the employee panel
to authenticated users, scoped by role: HR sees all business units, a BU
Head sees only their own. Scoping is enforced by Postgres RLS (already
live as of migration `5c6bf1a73a67`) — this endpoint adds no
role-derived filtering of its own, per the existing security guardrail
against divergent app-level/DB-level access logic.

Also serves as the first target for the pytest suite the backend README
calls for ("add a test suite alongside the first router that does real
query logic ... so the sort/filter column allow-list has something to
test against").

## Enforcement boundary

**Chosen: RLS is the only filter.** The router builds a query from
user-supplied filter/sort params only. It never adds
`WHERE business_unit_id = user.business_unit_id` or similar — that would
be a second, divergent source of truth alongside the RLS policies.
Scoping happens because `get_current_user` (via `_set_rls_context`, in
`app/security/deps.py`) sets `app.current_role` / `app.current_bu_id` as
`SET LOCAL` on the request's transaction, and FastAPI's `Depends(get_db)`
caching means the router's query runs in that same transaction.

Rejected alternatives:
- App-level filter *and* RLS ("belt and braces") — two sources of truth
  that can drift; the whole reason RLS exists here is to be the one
  layer that can't be bypassed by a bug in the other.
- A `security_barrier` view pushing shaping into the DB — unnecessary
  extra schema surface for what a plain RLS-scoped query already gives.

## Endpoints

- `GET /employees` — list, paginated, filterable, sortable.
- `GET /employees/{employee_id}` — single employee. Returns 404 (not 403)
  if RLS makes the row invisible — indistinguishable from "doesn't
  exist," which is correct: a 403 would itself confirm the row exists in
  another BU.

## Query parameters (list endpoint)

- `sort_by: Literal[...]` — closed set of allowed column names. Pydantic
  rejects anything outside the literal with a 422 before any SQL is
  built. The validated string then indexes a hardcoded
  `dict[str, InstrumentedAttribute]` — never `getattr()`.
- `sort_dir: Literal["asc", "desc"]`, default `asc`.
- `business_unit_id: int | None`, `department_id: int | None`,
  `grade: Literal[...] | None`, `employment_status: Literal["active","separated"] | None`,
  `location: str | None` — exact-match filters, all parameterized.
- `q: str | None` — parameterized `ILIKE` over `full_name`,
  `employee_code`, `designation`.
- `limit: int` (default 50, max 200), `offset: int` (default 0).

Response: `{items: [...], total: int, limit: int, offset: int}`.

## Response fields

Included: `id, employee_code, full_name, email, avatar_url, designation,
grade, location, employment_status, date_of_joining, tenure_years
(computed), department {id, name}, business_unit {id, name}, manager
{id, full_name} | null, ctc_annual, last_increment_date,
last_increment_pct, last_promotion_date, performance_rating,
engagement_score, manager_effectiveness_score`.

Excluded by design:
- `gender` — ARCHITECTURE.md: "only surfaced through a dedicated
  HR-only fairness-audit endpoint later — never through the ordinary
  directory view a BU Head sees."
- `date_of_birth` — age proxy; excluded in the same spirit as gender.
- `phone` — contact PII with no role in a flight-risk view.

Compensation and performance fields (`ctc_annual`, increments,
promotion date, scores) are included — they're expected to be core
signals for Module 2's scorecard and a BU Head already owns their own
team's comp. These fields are **row-scoped by the same RLS policies as
everything else**, not separately gated — confirmed explicitly in
testing (see below) so this doesn't become "rows are scoped correctly
but columns are returned flat to any authenticated caller regardless of
role," which is a different bug than row-level leakage and easy to miss.

`manager` is populated via a query against `employee` for the manager
row — also RLS-scoped. A manager in a different BU than the viewer
resolves to `manager: null`, not an error and not a leaked name. This is
an intentional, tested behavior the frontend should expect, not an edge
case being silently tolerated.

## Testing

New `backend/tests/` package, pytest, run in-process against the real
`fri_dev` database via `fri_app` (no mocking — the whole point is
proving RLS holds through the real request path, per the standing
instruction that manual curl verification was a stand-in, not a
substitute, for this).

Fixture: seed 6 employees across 3 BUs (reusing the pattern from the
manual verification session), with one employee whose manager sits in a
different BU. Teardown deletes them.

Required coverage:
1. HR sees all rows, across all BUs, via HTTP through `/employees`.
2. BU Head sees only their own BU's rows via HTTP.
3. BU Head requests another BU's employee by ID → 404.
4. BU Head requests `business_unit_id=<other BU>` filter → empty list,
   not an error.
5. BU Head field-level check: compensation/performance fields are
   present for their own BU's rows and never appear for another BU's
   rows (proves row-scoping isn't being bypassed by a flat column dump).
6. `gender` never appears in any response payload, either role.
7. Manager in a different BU → `manager: null` in the response, not an
   error, not a leaked name.
8. Missing/broken RLS session context → the query returns `[]`, not an
   error. This is the named test for the accepted "fails closed but
   silently" tradeoff of leaving all filtering to RLS — simulated by
   calling the list logic against a connection where `_set_rls_context`
   was never invoked.
9. `sort_by` with a disallowed value → 422, never reaches SQL.
10. `sort_by` with each allowed value → 200, correct ordering.

## Related changes (same round)

- `JWT_EXPIRE_MINUTES`: 30 → 15 (`app/config.py` default,
  `backend/.env.example`). Rationale: internal office use on
  potentially shared/unlocked machines — the realistic risk is device
  access, not token interception, so a shorter window is the
  proportionate fix. Explicitly not building a denylist/revocation.
- `ARCHITECTURE.md`: update both places the 30-minute token is
  documented (Stack section, Security guardrails section) to 15
  minutes, and add a note that logout clears the cookie client-side but
  does not revoke the token server-side — a copied/stolen token remains
  valid for up to 15 minutes after logout. Documented accepted
  tradeoff, not a bug.
- `backend/README.md`: point at the new `backend/tests/` suite and how
  to run it, replacing the current "Tests: None yet" section.

## Out of scope

- Frontend directory UI (Module 1 frontend, separate round).
- Write endpoints (create/update employee) — not requested.
- Fairness/proxy-audit endpoint (gender, disparate impact) — separate,
  HR-only, explicitly deferred in ARCHITECTURE.md.
- Token revocation/denylist — explicitly rejected by the user in favor
  of the shorter expiry.

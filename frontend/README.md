# FRI frontend

React + Vite + TypeScript. See `../ARCHITECTURE.md` for the full picture,
and `../PROJECT_VISION.md` for why this project exists.

## Local setup

```bash
cd frontend
npm install

cp .env.example .env.local   # VITE_API_BASE_URL, defaults to http://localhost:8000

npm run dev
```

Requires the backend running locally first (`cd ../backend`, see
`../backend/README.md`) — this app has no mock/offline mode, every
screen talks to the real API. The backend's `CORS_ORIGINS` must include
this app's origin; the checked-in default (`http://localhost:5173`) is
already Vite's default dev port, so a fresh clone of both repos needs no
config changes to talk to each other locally.

Log in with one of the seeded accounts (`backend/scripts/seed_reference_data.py`
— not real credentials):

| Role | Email | Business unit |
|---|---|---|
| HR | `priya.sharma@lsdigital-demo.com` | — (org-wide) |
| BU Head | `arjun.mehta@lsdigital-demo.com` | Data Quark |
| BU Head | `meenakshi.reddy@lsdigital-demo.com` | Business Function and Media |
| BU Head | `siddharth.agarwal@lsdigital-demo.com` | Enabling Functions |
| BU Head | `pooja.bhattacharya@lsdigital-demo.com` | SP Creative |
| BU Head | `aditya.choudhary@lsdigital-demo.com` | UI/UX |

Password for all seeded accounts: `ChangeMe123!`

## What's here

- `src/styles/tokens.css` — design tokens translated from
  `../design/stitch/DESIGN.md` (colors, type scale, spacing, radius,
  elevation). Read the file's own header comment before changing a
  color — one deliberate deviation from `DESIGN.md`'s literal frontmatter
  is explained there.
- `src/components/ui/` — the reusable component library the rest of the
  app is built from (Avatar, Badge, Card, Table, Button, form controls,
  plus `KpiCard`/`InsightCallout`/`RiskBandDistribution` — built ahead of
  Module 2, per `DESIGN.md`'s component patterns, and now wired to real
  data by both Module 2 and Module 3).
- `src/api/` — typed fetch client. Every request sends
  `credentials: 'include'`; nothing in this app reads, stores, or
  attaches an auth token itself — the httpOnly session cookie does all
  of that. `src/api/types.ts`'s `SORTABLE_FIELDS` is copied verbatim
  from the backend router's real allow-list, not guessed — keep the two
  in sync by hand if the backend adds a sortable column.
- `src/context/AuthContext.tsx` — session state sourced from
  `GET /auth/me`, never by decoding the cookie client-side.
- `src/pages/directory/` — the Employee Directory (table + card views).
  `useEmployeeDirectory.ts`'s header comment states the invariant this
  whole feature depends on: **no client-side role/BU filtering, ever**
  — the backend's Row-Level Security is the only thing that scopes rows,
  and this code only renders what it's given. Each row now links through
  to its Workforce Health score.
- `src/pages/workforce-health/` — Module 2's frontend: an org-wide (HR)
  or BU-scoped (BU Head, same component tree either way — see
  `WorkforceHealthPage.tsx`'s header comment) risk-band overview using
  `KpiCard`/`InsightCallout` for the first time, a per-employee
  score/driver-breakdown/recommendations drill-down
  (`EmployeeScoreDrilldownPage.tsx` — reachable from the directory or the
  overview's hotspot list), and an HR-only Fairness Audit view. The
  fairness audit page's role check is a UI courtesy only (skips the
  request and shows a message); the real enforcement is the backend's
  `require_hr` gate — see `MODULE2_REFERENCE.md`.
- `src/pages/risk-analysis/` — Module 3's frontend: an overview and
  per-employee drill-down structurally identical in shape to Module 2's
  (same RLS-scoped-by-the-server pattern, same component tree for both
  roles), but over `/risk-analysis/*` and a real trained model's SHAP
  output rather than Module 2's hand-weighted formula.
  `RiskDriverBreakdown` deliberately reuses `DriverBreakdown`'s visual
  language, adapted for signed SHAP contributions. `DemoDatasetBanner`
  renders on every screen in this module with a visually distinct
  (amber, not Module 2's cyan `InsightCallout`) treatment so it can
  never be mistaken for real baseline-panel data — see
  `MODULE3_REFERENCE.md`.

## Known rough edges (honest account, not hidden)

- **No `/business-units` endpoint.** The HR-only "filter by business
  unit" dropdown and a BU Head's sidebar business-unit-name label both
  work around this by deriving names from a directory fetch rather than
  a proper reference-data endpoint (see `useBusinessUnitFilterOptions.ts`
  and `AuthContext.tsx`'s `resolveBusinessUnitName`). Both are correct
  at today's ~18-row dataset size; the BU filter would silently miss
  business units past the backend's 200-row query cap if the panel
  grows substantially. A real endpoint would remove both workarounds.
- **`KpiCard`, `InsightCallout`, and `RiskBandDistribution`** are now
  wired to real Module 2 and Module 3 data (see
  `src/pages/workforce-health/` and `src/pages/risk-analysis/`).
- **No paginated Risk Analysis employee list/table view** — the backend's
  `GET /risk-analysis/employees` endpoint exists and is allow-list
  sorted/filtered like the directory, but the frontend only consumes the
  summary's hotspot list and per-employee drill-down, matching Module 2's
  own shipped scope (no full paginated table there either). A future
  session could add one using `useEmployeeDirectory.ts`'s pattern.

## Tests

None yet. The backend has a pytest suite proving Row-Level Security
holds through the real HTTP path (`../backend/tests/`); this frontend
was verified manually by logging in as HR and BU Head accounts through
the running app and checking each saw the correct, correctly-scoped
data — not by an automated frontend test suite, which doesn't exist yet.
Worth adding before this grows much further, especially around the
directory's filter/sort state.

Module 2's frontend was verified the same way: as HR, the Workforce
Health overview, an employee drill-down, and the Fairness Audit page
(including its small-sample "too small to assess" handling and the
manager team-risk table); as a BU Head, the same overview correctly
scoped to one business unit, a same-BU employee drill-down (with a
visibly smaller compensation peer group than HR sees for the same
grade — the intended effect of RLS-scoped peer comparisons, not a bug),
a cross-BU employee id resolving to "not found" exactly like the
directory already does, the Fairness Audit nav entry absent from the
sidebar, and direct navigation to `/workforce-health/fairness-audit`
showing the courtesy message rather than attempting the request.

Module 3's frontend was verified the same way, using Playwright to
drive a real Chromium browser against a real running server: as HR, the
Risk Analysis overview (KPIs, risk-band distribution, per-BU breakdown,
hotspot list) and a real SHAP driver breakdown on drill-down; as a BU
Head, the same overview correctly scoped to one business unit, and —
the adversarial check — navigating directly to an HR-visible employee's
`/risk-analysis/employees/{id}` URL, which resolved to a clean "Employee
not found" rather than leaking cross-BU data.

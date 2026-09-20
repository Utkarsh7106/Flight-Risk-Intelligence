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
  plus `KpiCard`/`InsightCallout` — built ahead of any screen that uses
  them, per `DESIGN.md`'s component patterns; nothing wires them to real
  data yet since Module 2/3 don't exist).
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
  and this code only renders what it's given.

## Known rough edges (honest account, not hidden)

- **No `/business-units` endpoint.** The HR-only "filter by business
  unit" dropdown and a BU Head's sidebar business-unit-name label both
  work around this by deriving names from a directory fetch rather than
  a proper reference-data endpoint (see `useBusinessUnitFilterOptions.ts`
  and `AuthContext.tsx`'s `resolveBusinessUnitName`). Both are correct
  at today's ~18-row dataset size; the BU filter would silently miss
  business units past the backend's 200-row query cap if the panel
  grows substantially. A real endpoint would remove both workarounds.
- **No employee detail page.** Only the list view exists — clicking a
  row doesn't go anywhere yet.
- **`KpiCard` and `InsightCallout`** exist as real, styled components
  but nothing renders them with real content — there's no Module 2/3
  data yet to put in them.

## Tests

None yet. The backend has a pytest suite proving Row-Level Security
holds through the real HTTP path (`../backend/tests/`); this frontend
was verified manually by logging in as HR and three different BU Head
accounts through the running app and checking each saw the correct,
correctly-scoped data — not by an automated frontend test suite, which
doesn't exist yet. Worth adding before this grows much further,
especially around the directory's filter/sort state.

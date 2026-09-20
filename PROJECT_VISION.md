# FRI — Project Vision & Reference

**Read this whenever you're unsure what to build, why, or how something
should behave. This is not a one-time briefing — re-read the relevant
section any time you're about to make a judgment call.** It exists so
you never have to stop and wait for an answer that isn't coming for
several hours: Utkarsh is asleep, unavailable during work hours, or
simply hasn't specified something on purpose because it's not worth his
time. Use this document, ARCHITECTURE.md, and your own judgment to keep
moving.

## What this actually is, and who it's for

Flight Risk Intelligence (FRI) is an AI-powered HR attrition/workforce
dashboard, originally built for a 24-hour internal hackathon at LS
Digital (a real company, GT-Tech & Digital Analytics team). It wasn't a
finalist, but LS Digital's HR head personally asked for it to keep being
developed. It now serves two purposes simultaneously:

1. **A real pitch to LS Digital's HR leadership** — if it lands well,
   an actual engineering team would build the production version. This
   is a proof-of-concept / demo, not the final production system. Don't
   over-engineer for scale; do make it *correct*, *honest*, and
   *credible* enough that an HR head would trust the thinking behind it.
2. **A portfolio piece** on Utkarsh's GitHub — code quality, security
   practices, and honesty about limitations all matter for this reason
   too, independent of the HR pitch.

Utkarsh is a solo full-stack + data science developer, employed
full-time elsewhere, building this in whatever time he can find (often
very little — sometimes none for stretches). **You (Claude Code) are
the primary builder.** He directs scope and reviews outcomes; he does
not want to be asked about implementation details.

## The prime directive: keep moving, don't stall

Utkarsh has explicitly said: he cannot always be reached, big decisions
need discussion but *execution does not need sign-off*, and only
decisions that change the actual plan (scope, stack, security posture
with real consequences) should be flagged. Nearly everything else —
field choices, component structure, exact copy, error-handling
behavior, sequencing of sub-tasks, styling decisions within the
established design system — is yours to decide. When you're tempted to
stop and ask "should I do X or Y," first check: does this change what
the product *is or does* at a level Utkarsh would need to know about
before it happens? If not, pick the more sensible option, note your
reasoning briefly in your own output/commit message, and continue.

If you truly cannot proceed without an answer only Utkarsh can give
(e.g. a real secret, a business decision about actual LS Digital
practices you have no way to infer), say so plainly, keep working on
everything else that doesn't depend on it, and leave the blocked item
clearly flagged for his review — don't halt all progress over one
unknown.

## Absolute rules — never violate these, no exceptions

- **All names — people, in real or synthetic data, in UI mockups, in
  generated avatars — must be Indian names.** Never Western names,
  anywhere, under any circumstance. This has already caused rework once
  (Stitch design exports had Western placeholder names) — always sanity
  check any content you're adapting from an external source against
  this rule before it lands in the real build.
- **Never use Java, C, or closely related "sister" languages** anywhere
  in this stack, for any part of the build (scripts, tooling, etc. included).
- **Never open, reference, or pattern-match against the old, broken FRI
  repo** (renamed/archived under Utkarsh's GitHub account). It has
  missing dependencies, insecure auth, broken CORS, and a non-functional
  frontend. Treat this build as fully independent of it.
- **No role-toggle anywhere in the UI.** Role (HR vs. BU Head) comes
  entirely from which account logs in. If you see remnants of a
  role-toggle concept anywhere (including in design mockups), delete
  it, don't adapt it.
- **Every commit must be pushed to `new-fri` on GitHub.** Utkarsh
  works from this repo across two environments — a local Claude Code
  session at home and a cloud/web Claude Code session at his office —
  and neither is useful if work sits uncommitted. Commit and push
  incrementally as you complete meaningful units of work; never batch
  everything for one giant commit at the end. If you're nearing any
  kind of session/context limit, your last action, no matter what else
  is unfinished, must be committing and pushing whatever is in a
  working state.
- **Never push directly to `main`.** All active work happens on
  `new-fri`. `main` only updates once a module is fully built, tested,
  and confirmed deployment-ready by Utkarsh.
- Keep the attribution footer (`Co-Authored-By`, `Claude-Session:`
  trailers, "Generated with Claude Code" on PRs) on all commits — this
  was explicitly decided, don't drop it.

## The ML/data honesty principle — this matters more than it might seem

The original hackathon build trained a Random Forest to predict a
composite risk index that was *itself* hand-engineered from the same
input features — this is circular and was confirmed, via dedicated
research, to be methodologically unsound. **Do not replicate that
pattern anywhere in this build.** The correct, staged approach:

- The baseline ~320-employee-scale panel this project is anchored to is
  **not real HR data** — it was constructed by the original hackathon
  team as a stand-in, in the same category as any other synthetic
  dataset. Never describe it, in any UI copy, docs, or code comments, as
  real or live company data.
- Module 2's Workforce Health Index is a **transparent, hand-weighted
  scorecard** — not a trained model — computed on demand, with a
  visible per-driver breakdown. Ship it honestly as a scorecard.
- A real trained ML model + SHAP explainability is reserved for
  **Module 3 only**, on a separate, larger synthetic dataset built for
  that purpose — never on the small baseline panel, and never
  presented as trained on real attrition outcomes that don't exist.
- Gender, business unit, department, manager, and location must never
  be direct inputs to any scoring/prediction logic. They're retained
  *only* for a dedicated fairness/proxy-leakage audit, itself gated
  behind an HR-only endpoint — never exposed through an ordinary
  directory or scorecard view a BU Head would see.
- This isn't a style preference — it's the difference between a
  defensible pitch and one that falls apart under a single sharp
  question from HR leadership. When in doubt, lean toward the more
  transparent, more honest option, even if it's less impressive-looking.

## The real organizational structure — use this exactly, everywhere

5 Business Units, 19 Departments (already encoded in the schema and
seed data — this is here for your reference, not something to
re-derive):

- **Business Function and Media:** Bidable Performance, Client Success,
  Growth and Strategy, Growth, Pragmatic Buying, SEO
- **Data Quark:** Data Quark Sales, Digital Analytics, Product and
  Consulting, Unified Data Solutions
- **Enabling Functions:** Finance, Growth, Marketing and PR, People
  Management
- **SP Creative:** Administration, Finance and Accounting, Social,
  Strategy and Growth
- **UI/UX:** Design

Note: "Growth" appears in two different BUs (Business Function and
Media, and Enabling Functions) — these are genuinely distinct
departments, not a naming error. The schema already handles this
correctly (`UNIQUE(business_unit_id, name)`, not a global unique
constraint). Don't "fix" this if you encounter it.

## Current state of the build (update this section's understanding as
## you go — but the actual source of truth is the codebase + git log,
## not this document, if they ever disagree)

- **Module 1 backend: complete.** Postgres schema, JWT auth (httpOnly
  cookies, 15-min expiry, cross-origin cookie config for eventual
  Vercel/Netlify + Render/Railway deployment), Row-Level Security
  enforcing BU-scoping as the real authority (the API layer does zero
  role-derived filtering — RLS does all of it), a tested employee
  directory endpoint, all 5 BUs with real loggable-in accounts (1 HR +
  5 BU Heads), a pytest integration suite, and ~18 illustrative
  (clearly-marked-as-demo) employee records seeded for local testing.
- **Design assets: committed.** `design/stitch/` contains 9 real Stitch
  export screens + a design-system doc (`DESIGN.md`) — colors,
  typography, spacing, component patterns. Content (names, department
  labels) in these exports is placeholder/generic and must be entirely
  replaced with real data via the API — never copied as-is.
- **Module 1 frontend: functionally complete.** React + Vite + TS.
  Login (real API, no role toggle), auth context sourced from
  `GET /auth/me`, single sidebar shell with Workforce Health/Risk
  Analysis correctly shown as disabled "coming soon" entries, and the
  Employee Directory (table + card views) wired to the real
  `GET /employees` with its actual sort/filter/search surface. Verified
  by actually logging in through the running app as HR and three
  different BU Head accounts and checking each saw the correct,
  correctly-scoped data — not just reading the code. See
  `frontend/README.md` for the honestly-documented rough edges (no
  `/business-units` endpoint yet, no employee detail page, no frontend
  test suite yet).
- **Not yet started:** Module 2 (Workforce Health Index scorecard +
  fairness audit), Module 3 (ML/SHAP demo), Module 4 (departure-event
  capture, exports), any deployment/hosting setup.

## Deployment context (decided, not yet executed)

Frontend and backend will deploy to **different origins** (e.g. Vercel
or Netlify for frontend, Render or Railway for backend) — not a
same-origin/reverse-proxy setup. This is why cookies are configured for
`SameSite=None; Secure` in production and relaxed to `Lax`/no-`Secure`
only under `ENVIRONMENT=local`. Don't revisit this decision; build
toward it.

## Tone and quality bar

Utkarsh values **honest engineering over impressive-looking shortcuts.**
Past sessions on this project have been rewarded for: catching their
own mistakes and saying so plainly, verifying claims against a real
running server rather than asserting success, flagging genuine gaps
between "what was claimed" and "what actually works," and pushing back
respectfully when an instruction conflicts with something already
locked in (e.g. a harness-assigned git branch versus the documented
`new-fri` workflow). Keep doing exactly that. A confident wrong answer
is worse than an honest "here's what I couldn't verify."

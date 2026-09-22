# Module 4 — Closing Features: Reference

**Read this whenever you're unsure what a Module 4 feature is actually
for, the same way you already use `PROJECT_VISION.md`,
`MODULE2_REFERENCE.md`, and `MODULE3_REFERENCE.md`.** This is the last
module in V1 — after this, the product is feature-complete for the
pitch, so it's worth building it carefully rather than rushing to
"done."

## What Module 4 is actually for

Modules 1-3 built the analytical core: real scoped data, a transparent
scorecard with fairness auditing, and an ML/SHAP demonstration track.
Module 4 closes two remaining gaps that matter for this being a real,
usable product rather than just an analytical engine:

1. **There is currently no way to record that an employee actually
   left.** Every risk score in this product is, definitionally, a
   *prediction* — but a prediction system with no mechanism to ever
   record the real outcome can never be checked against reality, never
   improved, and never asked "how did we do?" This module builds that
   mechanism. It does not need to *use* the data yet (survival analysis
   and any real predictive validation are explicitly future work, once
   enough real departures accumulate) — it needs to exist, be correct,
   and be genuinely usable by an HR person in the flow of their actual
   work.
2. **Nothing in this product can currently leave the app.** Everything
   built so far is only viewable by someone logged in, live, in a
   browser. For this to function as an actual pitch artifact — something
   an HRBP can attach to an email, or print and bring into a leadership
   review — there needs to be a way to get a report out of the system
   in a form other people can open without logging in or without a
   screen at all.

## Part A — Departure/separation event capture

### Why this needs real thought, not just a form

The schema already has a `departure_event` table and a
`mark_employee_separated` trigger from Module 1 — this was built
correctly from day one specifically so this moment wouldn't require a
schema migration. What's missing is the actual entry mechanism: how
does an HR person (or a BU Head, for their own team — think about
which roles should legitimately be able to record this) actually tell
the system "this person left, here's when, and here's why."

Think about this as a real HR workflow, not just a database insert.
Someone recording a departure needs at minimum: who left, when
(effective date), and some categorization of why (voluntary vs.
involuntary at minimum; a more granular reason — better offer,
relocation, retirement, performance-managed-out, etc. — is worth
considering, but don't over-engineer a reason taxonomy nobody asked
for). Consider what happens to that employee's other data once they're
marked separated — should they vanish from the ordinary directory view
by default, but remain visible somewhere (a "former employees" or
"separated" filter) for historical reference? An HR analytics tool that
makes departed employees simply disappear would lose exactly the data
this module exists to start capturing.

### Access control

Use your judgment, informed by the same role-scoping principles already
established: should a BU Head be able to record a departure for their
own team, or should this be HR-only? There's a reasonable case either
way — a BU Head is often the first to know when someone resigns, but
HR may want to be the system of record for something this consequential
(compensation/benefits implications, compliance record-keeping). Decide
and document your reasoning; this isn't a case where getting it "wrong"
breaks anything security-critical the way the fairness audit did, so
don't treat it with the same level of caution — just be deliberate
about it.

### What this explicitly does not need to do yet

No survival analysis, no "did our risk score correctly predict this
departure" comparison view, no cohort/retention-rate dashboards. Those
are legitimate future work once real departures exist in meaningful
numbers — building them now, against zero or a handful of real
departure events, would produce analysis with no real statistical
grounding, the same kind of premature-conclusion problem the project
has been careful to avoid elsewhere (see: why survival analysis was
explicitly deferred from the start of this project). Recording the
event correctly is the whole scope here.

## Part B — Shareable exports

### Why two formats, and what each is actually for

**Interactive HTML export** and **PDF download** serve genuinely
different purposes, and it's worth understanding why both were kept in
scope rather than picking one: an HTML export can remain somewhat
interactive (filterable, maybe even live-refreshing if you want to be
ambitious) and is the natural thing to open in a browser and click
through in a meeting; a PDF is the thing that gets attached to an email,
printed, or dropped into a slide deck — it needs to look finished and
professional as a static document, not like a webpage that was printed
by accident. Both should be able to represent, at minimum, an
org-wide view (HR) and a single-BU view (what a BU Head would want to
share about just their own team) — think about whether a further
filtered view (e.g. just the high-risk employees) is worth supporting
too.

### What actually needs to be in an export

Think about what someone would actually want to hand to a colleague or
bring into a meeting: some combination of the Workforce Health overview
(risk band distribution, hotspots), enough per-employee detail to be
useful without being an unwieldy wall of data, and — critically — the
same honesty standards already enforced everywhere else in this
product. If a shared export includes anything derived from Module 3's
demonstration dataset, the "this is a demonstration, not real data"
labeling must survive the export just as prominently as it does in the
live UI — an export that quietly drops that context because it wasn't
carried through the generation logic would be a real problem, not a
cosmetic one. Similarly, an export shared outside the live app also
needs to respect the same information-sensitivity boundaries — a BU
Head's exported report should contain exactly what they'd see live,
never more (e.g., never anything from the fairness audit, which is
categorically HR-only everywhere, including exports).

### Self-contained means self-contained

An HTML export that people will open outside the live app, potentially
much later or on a different machine, needs to actually work as a
standalone artifact — think about what "self-contained" really
requires (styling, any charts, any data it displays) so it doesn't
quietly depend on hitting your live API or loading assets that won't be
reachable once it's detached from this session.

## Consistency with everything already established

Same absolute rules apply: Indian names only (obviously already true of
any real employee data, but double-check nothing in a generated
export/report template reintroduces a placeholder Western name from a
template source), RLS/role-scoping as the real authority wherever
export content depends on what a specific role should see, same design
system for visual consistency, same testing rigor (verify exports live
by actually generating one and opening it, not just by confirming the
code runs without erroring).

## Judgment calls that are yours to make, without asking

The exact departure-reason taxonomy, who can record a departure
(BU Head vs HR-only), exactly what belongs in each export format,
whether/how much interactivity an HTML export retains, exact visual
layout of both export formats, and how filtered/scoped export options
should be. Document reasoning briefly wherever it's non-obvious.

## What would actually warrant stopping and waiting

A genuine security/access-control question with real consequences (in
the spirit of the earlier SameSite cookie decision), or discovering
something in an earlier module's foundation that blocks this one.
Otherwise, keep moving and document as you go.

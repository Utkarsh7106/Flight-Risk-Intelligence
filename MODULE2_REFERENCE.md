# Module 2 — Workforce Health Index: Reference

**Read this whenever you're unsure what a Module 2 feature is actually
for, or whether a judgment call is heading in the right direction.
Re-read the relevant section any time you're about to decide something
non-trivial, the same way you already use `PROJECT_VISION.md` and
`ARCHITECTURE.md`.** This exists so a long, unsupervised session doesn't
drift from intent even though no single decision in it needs Utkarsh's
sign-off.

This document explains **why** Module 2's features exist and what they
need to accomplish. It deliberately does not prescribe implementation —
formula weights, endpoint shapes, UI layout, and file structure are all
yours to decide, per `PROJECT_VISION.md`'s "keep moving" directive.

---

## What Module 2 is actually for

Module 1 proved the platform works. Module 2 is where FRI starts being
the product it was pitched as: something that tells an HR head *which*
employees are at risk of leaving, *why*, and *what to do about it*.

**The explanation matters more than the number.** A risk score alone is
not useful or trustworthy — anyone can produce a number. What makes
this valuable to a real HRBP is a score that comes with a clear,
inspectable breakdown of which factors drove it, in language a
non-technical HR person immediately understands and finds credible. If
a choice is ever between a more sophisticated-sounding score and a more
transparent, explainable one, choose transparency. This is a
hand-weighted scorecard by design, not a black box — that's a product
decision, not a limitation to work around.

**This must never resemble the original hackathon's flawed approach** —
training a model to predict a risk index that was itself constructed
from the same inputs. That was investigated and confirmed
methodologically circular (see `PROJECT_VISION.md`). Nothing in Module
2 involves training anything. It's a formula, applied consistently,
with its reasoning fully exposed. Module 3, not this module, is where a
real trained model eventually appears — on a separate dataset, never
this one.

## The scoring model

Legitimate inputs: anything reflecting the employee's own trajectory or
environment — time since last promotion, compensation trajectory
relative to grade/tenure, engagement score, manager effectiveness score
(this describes the employee's environment, not the employee — still
legitimate; a poor manager is a real retention driver), performance
rating, tenure. These mirror how an experienced HRBP already reasons
about flight risk informally — you're encoding existing sensible HR
thinking into a consistent, auditable rule, not inventing new theory.

**Forbidden inputs, absolutely, structurally, no exceptions:** gender,
business unit, department, manager *identity* (manager *effectiveness
score* is fine — the identity of who the manager is, is not), location.
This must be true at the level of "these values are never even read by
the scoring function," not just "the current formula happens not to use
them." An HR tool that scores people differently by BU or gender is
both ethically indefensible and an instant credibility-killer with real
HR leadership. This is the single most important constraint in the
entire module — weigh it above all other considerations, including
elegance or cleverness of the formula.

Weights and thresholds are your call. The test for a good design:
explainable in one sentence per factor, and directionally sensible to
anyone with basic HR intuition (longer promotion stagnation → higher
risk; stronger recent comp increase → lower risk; lower engagement →
higher risk; weaker manager effectiveness → higher risk). Document your
reasoning for the weights briefly wherever you land on them.

**The per-driver breakdown is not polish — it's the product.** Every
score must come with the top 2-4 contributing factors and a genuine
sense of how much each mattered relative to the others — not decorative
percentages bolted onto an opaque number. "This person scored 68,
driven mainly by 34 months since their last promotion and below-average
engagement" is something an HRBP can act on; a bare 68 is not.

## Retention recommendations — rule-based, never LLM-decided

The recommendation logic must be a deterministic lookup from dominant
driver(s) to intervention(s) — not because rules are simpler, but
because a deterministic table always works (no API key, no network
dependency, nothing that silently fails or hallucinates), is fully
auditable (anyone can see exactly why a recommendation fired), and is
consistent (identical driver profiles always produce identical
recommendations — this matters for fairness and for HR trusting the
tool). Two employees with the same driver profile getting different
recommendations because an LLM felt like it that day would undermine
the entire premise of the tool.

Illustrative starting points (reason from these, don't just replicate
verbatim): long promotion stagnation + strong performance → career
conversation + internal mobility. Compensation trajectory behind
grade/tenure expectations → compensation review. Low engagement + low
manager effectiveness → manager coaching / manager-relationship
conversation. Multiple recommendations firing at once when multiple
drivers are roughly equally dominant is fine and more honest than
forcing one answer.

An LLM, if used at all, may only take an already-decided recommendation
and turn it into more natural prose for display. It must never decide
*which* recommendation applies — that decision is complete before an
LLM (if involved at all) ever sees the output. Skipping LLM involvement
entirely and shipping clean rule-based bullet output is a completely
acceptable, arguably safer, complete version of this feature.

## Fairness / proxy-leakage audit — HR-only, non-negotiable access control

Excluding protected attributes as direct *inputs* isn't sufficient on
its own. A formula can be unfair by proxy even without using a
protected attribute directly, if an attribute it does use happens to
correlate with a protected one in this specific workforce — e.g. if
compensation or promotion timelines happen to differ systematically by
gender in the real data, a score built on those signals could produce
systematically different results by gender even though gender was never
an input. This is a well-documented real failure mode, and this audit
exists to actively check for it rather than assume exclusion of direct
inputs is enough.

For gender/BU/department/location: compare risk-score distributions
across groups within each attribute; a meaningful, unexplained
difference is a signal worth surfacing to HR for human review, not
proof of a problem by itself. For manager: a different, intentional
angle — check whether individual managers are producing systematically
elevated scores across their team, which is a valuable insight pointing
at a manager needing support, not something to mask.

Be honest about statistical confidence given small sample sizes (as few
as ~18 employees in the current seed data) — don't present a
noise-driven gap in a 3-person group with the same weight as a real
pattern in a larger one.

**This entire feature is reachable by HR-role accounts only — never a
BU Head, under any circumstance, not even their own BU's slice of it.**
The only reason it's permissible to compute this at all is that it's
gated behind a genuinely HR-only endpoint. Treat any accidental exposure
to a non-HR role as a serious defect, not a minor bug. This needs
adversarial verification (actually try to access it as a BU Head and
confirm refusal), not just an assumption that the role check is
correctly wired.

## Backend and RLS pattern — stay consistent with Module 1

Employee-level Module 2 endpoints (individual scores, BU-level
summaries) follow the exact same pattern already established for the
directory: RLS is the real authority, the endpoint itself does no
manual role-filtering, sortable/filterable fields go through a
hardcoded allow-list, never dynamic attribute access. Don't introduce a
second, divergent enforcement pattern for this module.

## Frontend visual language

Extend, don't diverge from, the design-system foundation already built
in Module 1 (`DESIGN.md` tokens, existing components). Module 2 should
read as a natural continuation of the directory, not a visually
different product bolted on. `KpiCard` and `InsightCallout`
(components built in Module 1, unused until now) are meant for exactly
this module. The `bu_strategic_risk_analysis` Stitch screen is useful
for layout/structure inspiration only — same rule as every other design
asset: structure yes, content (names, labels) no, ever.

## Judgment calls that are yours to make, without asking

Exact scoring formula and weights, exact risk-band thresholds and
naming, exact driver-to-recommendation mappings, whether to involve an
LLM for recommendation prose, the exact statistical approach for the
fairness audit, exact API endpoint shapes, every frontend
layout/component decision. Document reasoning briefly wherever you land
on something non-obvious; don't wait for approval to proceed.

## What would actually warrant stopping and waiting

Only: discovering the transparent-scorecard approach itself is
unworkable (it shouldn't be — it's well-specified above), a genuine
security decision with real consequences (like the earlier SameSite
cookie call), or finding the Module 1 foundation broken in a way that
blocks Module 2 entirely. Everything else in this document is designed
to be resolvable alone, tonight.

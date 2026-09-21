# Module 3 — ML/SHAP Demonstration: Reference

**Read this whenever you're unsure what a Module 3 feature is actually
for, or whether a judgment call is heading in the right direction.**
Same role as `MODULE2_REFERENCE.md` — re-read the relevant section
before deciding something non-trivial. This exists so a long,
unsupervised session doesn't drift from intent.

---

## What Module 3 is actually for, and what it must never become

Module 2 proved FRI can produce transparent, explainable risk scores
without any ML. Module 3 proves the *other* half of the pitch: that the
team can also stand up a real, honest ML pipeline — preprocessing,
feature engineering, a trained classifier, SHAP explainability — and
have it hold together end to end.

**This is a capability demonstration, not a claim that this specific
model validly predicts real LS Digital attrition.** Nobody at LS
Digital has ever actually left (the baseline panel and Module 2's seed
data have no attrition history at all), so there is no real label
anywhere in this system to train against, and no amount of clever
feature engineering changes that. Pretending otherwise — dressing up a
synthetic-data demo as if it were validated on real outcomes — would be
the single most credibility-destroying thing this module could do,
worse than the demo being technically modest. Every surface where this
module's output appears (UI, API responses conceptually, docs) must be
unmistakably, persistently labeled as running on a separate
demonstration dataset, never conflated with the Module 1/2 baseline
panel.

## Why a new, separate, larger synthetic dataset — not the existing panel

Two independent, both-sufficient-on-their-own reasons:

1. **Row count.** The baseline panel and Module 2's seed data top out
   at ~18-320 rows. A supervised model trained on that few rows doesn't
   learn a pattern — it memorizes noise. Nothing about feature
   engineering or model choice fixes too little data; the only fix is
   more data.
2. **No label exists.** Neither dataset has ever recorded a real
   departure. Module 2's scorecard and the directory don't need a
   label because they don't predict anything — they score against a
   fixed formula. A trained classifier has nothing to learn from
   without a target variable, and there is genuinely nothing in this
   system to supply one honestly.

So Module 3 needs its own dataset, generated specifically to have both
enough rows and a real (synthetic) binary label: did this employee
leave.

## How the label is generated — the single most important decision here

This is where the original hackathon build went wrong, and where it
would be easiest to accidentally repeat the mistake one level removed.
Read this section fully before touching `app/synthetic/generate.py`.

**The trap:** if the departure label is produced by running Module 2's
exact weighted formula and thresholding it into a binary outcome, then
training a classifier on the same five inputs to predict that label is
circular — the model would just be re-deriving Module 2's own formula
from its own output, dressed up as "the model discovered these are
important factors." That's a tautology, not a demonstration, and it's
exactly the failure mode the hackathon's Random-Forest-trained-on-its-
own-derived-index made. Module 3 must genuinely not do this.

**The approach actually used here** — deliberately different from
Module 2's formula on every axis that matters:

- **Different functional form.** Module 2 is a linear weighted average
  of five 0-100 sub-scores, banded into four tiers. The label generator
  instead builds a log-odds (logistic) score — each factor contributes
  an additive nudge to log-odds, not a share of a bounded 0-100 scale —
  and the final probability comes from a sigmoid over that log-odds
  sum. Structurally unrelated math, not just different numbers plugged
  into the same shape.
- **Genuine randomness, not a threshold.** Every synthetic employee's
  outcome is a single Bernoulli draw from their computed probability,
  not "probability >= cutoff -> left." Two employees with identical
  feature values can and do get different outcomes. This matters for
  two reasons: it's what real attrition actually looks like (people
  with the same risk profile don't all leave or all stay), and it
  structurally prevents the model from ever reaching perfect accuracy
  by memorizing a deterministic function of the inputs — a classifier
  that hit ~100% accuracy here would itself be a red flag that
  something leaked, so the noise is what keeps the eventual eval
  numbers honest and checkable.
- **Extra signals Module 2 never sees.** The label generator draws on a
  few additional synthetic features — `overtime_frequency`,
  `job_satisfaction_score` (a distinct day-to-day-satisfaction signal,
  not the same field as `engagement_score`), `distance_from_home_km`,
  and `years_since_last_promotion` as a raw numeric feature in its own
  right — none of which Module 2's scorecard ever reads. This isn't
  padding: it means the trained model has real signal available to it
  that didn't come from Module 2's own five-factor formula, so a
  feature-importance/SHAP result that lines up with genuine HR
  intuition is evidence of the pipeline actually working, not an
  artifact of copying Module 2's weights.
- **General correlation *directions*, not a copied dataset.** The
  relative sign and rough magnitude of each factor's contribution to
  log-odds is informed by the well-established, widely published
  correlation patterns from the IBM HR Attrition dataset (overtime,
  low job satisfaction, long promotion stagnation, compensation
  lagging peers, and short tenure are consistently its strongest
  attrition correlates across every public analysis of it) — used here
  purely as a source of *plausible real-world direction and rough
  relative weight*, not as literal training data, not fit against the
  actual IBM CSV, and never presented as validated. This keeps the
  synthetic dataset's patterns recognizable to an HR audience as
  realistic, without making Module 3 secretly a re-hosting of a public
  Kaggle dataset under FRI's own name.

**Same absolute exclusion as Module 2, and for the same reason:**
gender, business unit, department, manager identity, and location are
never inputs to the label-generation probability, and never inputs to
the trained model's feature set. This holds even though the real IBM
dataset does show some demographic correlations, and even though this
is a different, larger, purpose-built dataset — the exclusion is about
this product's ethics and defensibility, not about any one dataset's
size or provenance. `grade` remains legitimate for the same reason it
is in Module 2 (an org level, not a protected attribute).

Indian-names-only and the real 5-BU/19-department structure still
apply here — this is still an LS-Digital-flavored demonstration, even
though every employee and every outcome in it is invented.

## Dataset shape and where it lives

New table, own namespace: `synthetic_employee` — not a row in
`employee`, not mixed with the baseline panel anywhere. Reuses the real
`business_unit`/`department` reference tables (same 5 BUs, 19
departments — org structure isn't something that should ever need
duplicating), but every employee row, and the departure label itself,
is entirely synthetic.

Reuses `employee`'s `employment_status` ('active'/'separated') idea
deliberately, because it maps cleanly onto this dataset's two roles at
once:

- **`separated` rows** are the labeled training examples — synthetic
  employees whose (synthetic) departure the generator decided,
  probabilistically, happened. These exist to teach the model; they
  are not served through the demo API.
- **`active` rows** represent "the current synthetic workforce" — the
  set the demo actually scores and displays, because "who among our
  current people looks highest-risk" is the realistic, forward-looking
  question a real deployment would ask. Nobody would run inference on
  someone who's already gone.

Row-Level Security is applied to `synthetic_employee` exactly the way
it's applied to `employee` (same `app.current_role`/`app.current_bu_id`
session-variable policies, same HR-full-access / BU-head-scoped split).
Not because the security story strictly requires it for synthetic
data, but because introducing a second, divergent enforcement pattern
for this module would be the wrong lesson to encode, and because "even
the demo module respects the same access control as the real modules"
is itself a legitimate, honest thing to be able to say in a pitch.

## The model and SHAP

A real train/test split (stratified, held out, never evaluated on
training rows), a real scikit-learn tree-ensemble classifier, and real
SHAP (`TreeExplainer`) values — this needs to hold up as genuine ML,
not a demo that only looks like one.

**Deliberate proof-of-concept simplification, documented rather than
hidden:** predictions and SHAP driver values are computed once, during
the offline generation/training script, and persisted per synthetic
employee — not recomputed on every HTTP request. The values themselves
are genuinely produced by SHAP against the actual trained model for
that specific employee's feature vector; what's simplified is *when*
that computation happens, not whether it's real. This mirrors how a
real production system would likely work anyway (batch-score
periodically, serve from a store), keeps the live API process free of
needing `scikit-learn`/`shap` as runtime dependencies (only the offline
script needs them), and matches the ambition level this module is
scoped to — no live-inference service, no model-versioning
infrastructure, none of that is needed for a proof-of-concept.

**Relationship to Module 2's driver-breakdown UI, deliberately close:**
the whole point of SHAP here is the same "why, not just what" principle
already established — per-employee, per-prediction driver
explanations. Module 3's demo view reuses Module 2's driver-breakdown
visual pattern (`DriverBreakdown`) rather than inventing a second way
to show "what's driving this," specifically so a user doesn't have to
learn a new mental model to read Module 3's output versus Module 2's.
The two are conceptually different underneath (a fixed formula's
weighted shares vs. a trained model's SHAP values) but should *read*
the same on screen.

## What "done" looks like

Proof-of-concept ambition, not production ML infrastructure:

- A dataset-generation script that produces a large-enough synthetic
  panel with an honestly, non-circularly generated label.
- A training script with a real stratified train/test split and
  honestly reported evaluation metrics (accuracy, ROC-AUC) on the held-
  out test set — not cherry-picked, not evaluated on training data.
- A trained classifier + persisted per-employee SHAP driver
  explanations for the active/demo-facing subset.
- API endpoints following the exact RLS/allow-list patterns already
  established in Modules 1 and 2 — no new, divergent enforcement
  pattern.
- A clearly, persistently labeled "demonstration dataset" UI surface
  (the "Risk Analysis" nav item, currently a disabled placeholder)
  showing this working for real, reusing Module 2's visual language.

No hyperparameter-tuning pipeline, no model registry, no retraining-on-
schedule infrastructure — none of that is in scope or expected.

## Judgment calls that are mine to make, without asking

Exact model choice and hyperparameters, exact dataset size, exact
label-generation coefficients and noise level, exact feature set beyond
the exclusions above, exact API endpoint shapes, exact frontend layout.
Document reasoning briefly wherever something non-obvious is decided;
don't wait for approval to proceed.

## What would actually warrant stopping and waiting

Only: discovering the separate-dataset-plus-independently-generated-
label approach is fundamentally unworkable (it shouldn't be — it's
well-specified above), a genuine security decision with real
consequences, or finding an earlier module's foundation broken in a way
that blocks this one entirely. Everything else here is designed to be
resolvable alone.

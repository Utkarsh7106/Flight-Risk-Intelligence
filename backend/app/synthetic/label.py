"""The Module 3 label generator — the single most important design
decision in this module. Read MODULE3_REFERENCE.md's "How the label is
generated" section before touching this file; this docstring is the
condensed version.

This is a logistic (log-odds) data-generating process, structurally and
numerically unrelated to app/scoring/model.py's linear weighted-average
scorecard: different functional form, a partly different and larger
feature set (overtime/job satisfaction/commute distance are never read
by Module 2), and — critically — a Gaussian noise term added in
log-odds space before every employee's outcome is drawn as a Bernoulli
trial. Two employees with identical features can and do get different
outcomes. That randomness is what keeps this honest: it's what makes a
trained classifier's eventual test-set accuracy a real, checkable
number rather than a foregone conclusion, and what stops this from
being Module 2's formula thresholded into a binary one level removed.

Coefficient signs and rough relative magnitudes are informed by the
well-established, widely published correlation directions in the IBM
HR Attrition dataset (overtime, low job satisfaction, promotion
stagnation, compensation lagging peers, and short tenure are
consistently its strongest attrition correlates) — used here only as a
source of plausible real-world direction, not fit against that dataset
or presented as validated by it.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from app.synthetic.features import Features

# Target ~17% overall departure rate across the generated dataset — same
# ballpark as IBM HR Attrition's real ~16%, so the base rate itself reads
# as plausible to an HR audience. The intercept that actually achieves
# this is NOT hardcoded here — every term below is one-directional
# (risk-only; there are no protective terms that pull log-odds down), so
# the average employee's raw term sum is well above zero and a naively
# guessed intercept (log-odds of the base rate, as if terms averaged to
# zero) systematically overshoots the target rate. generate.py's
# calibrate_intercept() finds the intercept empirically instead — see
# that function for why this is the honest fix rather than hand-tuning
# magic numbers until a single run happens to look right.
BASE_RATE = 0.17

# Standard deviation of the log-odds noise term. This is what makes the
# label non-deterministic — see module docstring. Large enough that
# identical feature profiles routinely land on both sides of the outcome;
# small enough that the engineered features still carry real, learnable
# signal. 0.45 was chosen empirically (not the first value tried — 0.6
# pushed held-out ROC-AUC down to ~0.64, honest but too noisy to read as
# a convincing capability demo; see app/synthetic/train.py's held-out
# ROC-AUC print, which is the actual verification, not this comment).
NOISE_STD_DEV = 0.45


def departure_log_odds_terms(features: Features) -> float:
    """Additive log-odds contributions, EXCLUDING the intercept (that's
    supplied separately by the caller — see calibrate_intercept() in
    generate.py). Each term's sign is directionally justified in the
    comment beside it; magnitudes were tuned empirically (via
    app/synthetic/train.py's held-out ROC-AUC, checked with 5-fold
    cross-validation to average out single-split noise) rather than
    picked once and assumed correct. The first pass at these weights
    produced real but weak signal (~0.63-0.67 AUC, barely above chance,
    varying mostly with evaluation noise rather than the deliberate
    NOISE_STD_DEV changes intended to move it) — the relative *shape* of
    the weights was right (checked via the active-vs-separated mean
    comparisons in generate.py) but the *scale* was too small relative
    to NOISE_STD_DEV for a classifier to reliably separate signal from
    noise. Doubling every coefficient here (keeping NOISE_STD_DEV fixed)
    moved 5-fold AUC to ~0.75 — a credible, non-suspicious "real,
    learnable, but not perfect" result, in the same range commonly
    reported for actual HR-attrition-style classification tasks.
    """
    log_odds = 0.0

    # Overtime is consistently IBM's single strongest attrition correlate.
    log_odds += 1.80 if features.overtime >= 0.5 else 0.0

    # Low day-to-day job satisfaction — distinct from engagement_score.
    log_odds += 1.40 * max(0.0, (55.0 - features.job_satisfaction_score) / 55.0)

    # Promotion stagnation, saturating past 5 years.
    log_odds += 1.20 * min(1.0, features.months_since_promotion / 60.0)

    # Pay trailing same-grade peers.
    log_odds += 2.00 * max(0.0, 1.0 - features.ctc_ratio_to_grade_median)

    # Low engagement, independent of job satisfaction above.
    log_odds += 1.00 * max(0.0, (55.0 - features.engagement_score) / 55.0)

    # Weak manager effectiveness — describes the environment, same
    # legitimacy argument as Module 2's identical treatment of this field.
    log_odds += 0.80 * max(0.0, (55.0 - features.manager_effectiveness_score) / 55.0)

    # Longer commute, smaller effect, saturating past 40km.
    log_odds += 0.40 * min(1.0, features.distance_from_home_km / 40.0)

    # Short tenure: IBM shows markedly higher early-tenure attrition.
    log_odds += 0.80 if features.tenure_years < 2.0 else 0.0

    # Mild U-shape on performance: very low performers (pressure/managed
    # out) and very high performers (external options) both skew slightly
    # riskier than the middle of the distribution — deliberately not the
    # same "strong performer + stagnation" coupling Module 2's
    # performance-recognition-gap driver uses, to keep this independent.
    log_odds += 0.60 * min(1.0, abs(features.performance_rating - 3.2) / 1.5)

    return log_odds


def sigmoid(log_odds: float) -> float:
    return 1.0 / (1.0 + math.exp(-log_odds))


def departure_probability(features: Features, intercept: float, noise: float) -> float:
    return sigmoid(intercept + departure_log_odds_terms(features) + noise)


@dataclass(frozen=True)
class LabelDraw:
    probability: float  # the noised probability actually drawn from
    left_company: bool


def draw_label(features: Features, intercept: float, rng: random.Random) -> LabelDraw:
    noise = rng.gauss(0.0, NOISE_STD_DEV)
    probability = departure_probability(features, intercept, noise)
    left_company = rng.random() < probability
    return LabelDraw(probability=probability, left_company=left_company)

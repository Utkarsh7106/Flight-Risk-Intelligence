"""Shared feature engineering for Module 3 — used by both the label
generator (app/synthetic/generate.py, offline only) and the trained
model (app/synthetic/train.py, offline only) so the data-generating
process and the model that later tries to recover it work over the
same raw, legitimate signals. That's standard practice for any
simulated labeled dataset, not a shortcut: see MODULE3_REFERENCE.md for
why this isn't the original hackathon's mistake — the label itself is
not a deterministic function of this vector (generate.py adds real
noise), and the label's functional form (log-odds/logistic) is
unrelated to how app/scoring/model.py combines its own five factors.

STRUCTURAL EXCLUSION, same discipline as app/scoring/model.py's
ScoringInputs: `Features` below is the complete signature. gender,
business_unit, department, and location are simply not fields on it —
there is no manager identity in this dataset at all (Module 3 has no
per-manager audit, unlike Module 2's fairness audit).
"""

from __future__ import annotations

import datetime as dt
import statistics
from dataclasses import dataclass

GRADE_ORDER = {"L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5, "L6": 6}

# Fixed order — this is the exact column order the model is trained and
# scored on. Changing it requires retraining (app/synthetic/train.py).
FEATURE_ORDER = [
    "tenure_years",
    "months_since_promotion",
    "months_since_increment",
    "ctc_ratio_to_grade_median",
    "performance_rating",
    "engagement_score",
    "manager_effectiveness_score",
    "overtime",
    "job_satisfaction_score",
    "distance_from_home_km",
    "grade_ordinal",
]

FEATURE_LABELS = {
    "tenure_years": "Tenure",
    "months_since_promotion": "Time since last promotion",
    "months_since_increment": "Time since last increment",
    "ctc_ratio_to_grade_median": "Compensation vs. grade peers",
    "performance_rating": "Performance rating",
    "engagement_score": "Engagement",
    "manager_effectiveness_score": "Manager effectiveness",
    "overtime": "Frequent overtime",
    "job_satisfaction_score": "Job satisfaction",
    "distance_from_home_km": "Commute distance",
    "grade_ordinal": "Grade level",
}


@dataclass(frozen=True)
class RawSignals:
    """Everything about one synthetic employee that's legitimate to read
    for feature engineering. Deliberately excludes gender/BU/department/
    location — a caller with those on hand simply never passes them in.
    """

    date_of_joining: dt.date
    grade: str
    last_promotion_date: dt.date | None
    last_increment_date: dt.date | None
    ctc_annual: float
    performance_rating: float
    engagement_score: float
    manager_effectiveness_score: float
    overtime: bool
    job_satisfaction_score: float
    distance_from_home_km: float


@dataclass(frozen=True)
class Features:
    tenure_years: float
    months_since_promotion: float
    months_since_increment: float
    ctc_ratio_to_grade_median: float
    performance_rating: float
    engagement_score: float
    manager_effectiveness_score: float
    overtime: float  # 0.0/1.0 — kept numeric for direct use as a model input
    job_satisfaction_score: float
    distance_from_home_km: float
    grade_ordinal: int

    def to_vector(self) -> list[float]:
        return [float(getattr(self, name)) for name in FEATURE_ORDER]


def _months_between(start: dt.date, end: dt.date) -> float:
    return max(0.0, (end - start).days / 30.437)


def grade_medians(rows: list[RawSignals]) -> dict[str, float]:
    """Median CTC per grade across the whole dataset — computed once over
    all rows, same aggregate-only pattern as Module 2's peer comparison
    (app/routers/workforce_health.py's _peer_ctc_by_grade), just computed
    in bulk here instead of per-request.
    """
    by_grade: dict[str, list[float]] = {}
    for r in rows:
        by_grade.setdefault(r.grade, []).append(r.ctc_annual)
    return {grade: statistics.median(values) for grade, values in by_grade.items()}


def compute_features(signals: RawSignals, as_of: dt.date, grade_median_ctc: float) -> Features:
    promotion_anchor = signals.last_promotion_date or signals.date_of_joining
    increment_anchor = signals.last_increment_date or signals.date_of_joining

    return Features(
        tenure_years=_months_between(signals.date_of_joining, as_of) / 12.0,
        months_since_promotion=_months_between(promotion_anchor, as_of),
        months_since_increment=_months_between(increment_anchor, as_of),
        ctc_ratio_to_grade_median=(signals.ctc_annual / grade_median_ctc if grade_median_ctc else 1.0),
        performance_rating=signals.performance_rating,
        engagement_score=signals.engagement_score,
        manager_effectiveness_score=signals.manager_effectiveness_score,
        overtime=1.0 if signals.overtime else 0.0,
        job_satisfaction_score=signals.job_satisfaction_score,
        distance_from_home_km=signals.distance_from_home_km,
        grade_ordinal=GRADE_ORDER[signals.grade],
    )

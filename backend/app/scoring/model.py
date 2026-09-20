"""Workforce Health / Flight Risk scoring model — Module 2, Part 1.

A transparent, hand-weighted scorecard computed on demand. Not a trained
model, never presented as one — see MODULE2_REFERENCE.md's "The scoring
model" section and ARCHITECTURE.md's "ML methodology guardrail" for why.

STRUCTURAL EXCLUSION (read before touching this file): `ScoringInputs`
below is the *complete* signature of the scoring function. gender,
business_unit_id, department_id, manager_id, and location are simply not
fields on it — `score_employee()` cannot read them even by mistake,
because they never arrive as arguments. A future change that wants to
feed one of those in has to edit this dataclass first, in this file,
which is deliberately the single choke point. `grade` is not forbidden:
it is an org level, not a protected attribute, and is used only to place
`ctc_annual` in context against other employees at the same grade (see
`peer_median_ctc_at_grade` below — computed by the caller via a normal
RLS-scoped query, same as everything else in this codebase; see
`app/routers/workforce_health.py`). See `tests/test_scoring_structural.py`
for the regression test that enforces this.

## The five factors, one sentence each

- **Promotion stagnation** (weight 0.30): the longer since an employee's
  last promotion — or since they joined, if never promoted — the higher
  the risk, because unaddressed stagnation is the most concrete signal
  that reward has stalled.
- **Compensation trajectory** (weight 0.25): risk rises when this
  employee's pay lags same-grade peers and/or their last raise was a
  long time ago, because both suggest the market may be passing them by.
- **Engagement** (weight 0.22): lower self-reported engagement directly
  raises risk, because it is the most direct signal we have of how
  someone currently feels about staying.
- **Manager effectiveness** (weight 0.15): a less effective manager
  raises risk independent of the employee's own performance, because
  manager quality is a well-documented attrition driver in its own
  right — this describes the employee's environment, not the employee,
  so it stays a legitimate input even though manager *identity* is
  forbidden.
- **Performance-recognition gap** (weight 0.08): a strong performer
  (rating >= 4.0) who is *also* stagnating on promotion or compensation
  gets a modest extra bump, because skilled people with real external
  options are more likely to act on dissatisfaction than to wait it out
  — this is a deliberately small weight so it amplifies the other
  factors rather than dominating the score on its own.

Any factor whose underlying data is missing (e.g. no `engagement_score`
on file) is dropped and the remaining weights are renormalized to sum to
1.0, rather than silently treated as zero risk or maximum risk.
`ScoreResult.data_completeness` reports what fraction of the full
five-factor weight was actually backed by real data, so a score built on
partial data is never presented with false confidence.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, replace
from enum import Enum

# Design-time weights. Must sum to 1.0 — see module docstring for the
# one-sentence rationale behind each.
_WEIGHTS: dict[str, float] = {
    "promotion_stagnation": 0.30,
    "compensation_trajectory": 0.25,
    "engagement": 0.22,
    "manager_effectiveness": 0.15,
    "performance_recognition_gap": 0.08,
}
assert abs(sum(_WEIGHTS.values()) - 1.0) < 1e-9

# A driver is only surfaced as a "top driver" past the first two once its
# share of the final score clears this floor — keeps the breakdown from
# padding out to 4 entries with negligible contributors.
_MIN_DRIVER_SHARE_TO_SURFACE = 0.05

# Strong-performer threshold for the recognition-gap factor. The seed
# panel's real performance_rating range is ~2.0-4.7 (see
# app/models/employee.py), not a clean 1-5 scale, so 4.0 sits roughly in
# the observed top band rather than at the schema's nominal midpoint.
_STRONG_PERFORMER_THRESHOLD = 4.0


class RiskBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


RISK_BAND_LABELS: dict[RiskBand, str] = {
    RiskBand.LOW: "Low",
    RiskBand.MEDIUM: "Medium",
    RiskBand.HIGH: "High",
    RiskBand.CRITICAL: "Critical",
}


def _band_for_score(score: float) -> RiskBand:
    if score >= 80:
        return RiskBand.CRITICAL
    if score >= 60:
        return RiskBand.HIGH
    if score >= 35:
        return RiskBand.MEDIUM
    return RiskBand.LOW


@dataclass(frozen=True)
class ScoringInputs:
    """Everything `score_employee()` is allowed to see. Nothing else.

    `peer_median_ctc_at_grade` and `peer_group_size` describe *other*
    employees only in aggregate (a median and a count) — no individual
    peer's data, and no BU/department/gender/manager information about
    them ever passes through this type.
    """

    as_of: dt.date
    date_of_joining: dt.date
    grade: str
    last_promotion_date: dt.date | None
    last_increment_date: dt.date | None
    ctc_annual: float | None
    peer_median_ctc_at_grade: float | None
    peer_group_size: int
    performance_rating: float | None
    engagement_score: float | None
    manager_effectiveness_score: float | None


@dataclass(frozen=True)
class DriverContribution:
    key: str
    label: str
    explanation: str
    risk_points: float  # this driver's own 0-100 sub-score
    weight_share: float  # this driver's share of the final score, 0-1


@dataclass(frozen=True)
class ScoreResult:
    score: float  # 0-100
    band: RiskBand
    band_label: str
    drivers: list[DriverContribution] = field(default_factory=list)  # top 2-4, descending
    data_completeness: float = 1.0  # fraction of full weight backed by real data


def _months_since(start: dt.date, as_of: dt.date) -> float:
    return max(0.0, (as_of - start).days / 30.437)


def _linear_risk(value: float, low: float, high: float) -> float:
    """0 at/below `low`, 100 at/above `high`, linear in between."""
    if value <= low:
        return 0.0
    if value >= high:
        return 100.0
    return (value - low) / (high - low) * 100.0


def _inverse_linear_risk(value: float, low: float, high: float) -> float:
    """100 at/below `low`, 0 at/above `high`, linear in between."""
    if value <= low:
        return 100.0
    if value >= high:
        return 0.0
    return (high - value) / (high - low) * 100.0


def _promotion_stagnation(inputs: ScoringInputs) -> DriverContribution:
    anchor = inputs.last_promotion_date or inputs.date_of_joining
    months = _months_since(anchor, inputs.as_of)
    risk = _linear_risk(months, low=18, high=60)
    basis = "since last promotion" if inputs.last_promotion_date else "since joining (never promoted)"
    return DriverContribution(
        key="promotion_stagnation",
        label="Promotion stagnation",
        explanation=f"{months:.0f} months {basis}",
        risk_points=risk,
        weight_share=0.0,
    )


def _compensation_trajectory(inputs: ScoringInputs) -> DriverContribution:
    position_risk: float | None = None
    if (
        inputs.ctc_annual is not None
        and inputs.peer_median_ctc_at_grade
        and inputs.peer_group_size >= 2
    ):
        ratio = inputs.ctc_annual / inputs.peer_median_ctc_at_grade
        position_risk = _inverse_linear_risk(ratio, low=0.85, high=1.05)

    increment_anchor = inputs.last_increment_date or inputs.date_of_joining
    months_since_increment = _months_since(increment_anchor, inputs.as_of)
    # Never having been incremented at all is a stronger signal than a
    # merely-old increment, so the risk ramp starts hitting its ceiling sooner.
    momentum_high = 36 if inputs.last_increment_date else 24
    momentum_risk = _linear_risk(months_since_increment, low=12, high=momentum_high)

    parts = [p for p in (position_risk, momentum_risk) if p is not None]
    risk = sum(parts) / len(parts)

    if position_risk is not None:
        ratio_pct = (inputs.ctc_annual / inputs.peer_median_ctc_at_grade) * 100  # type: ignore[operator]
        position_note = f"CTC is {ratio_pct:.0f}% of same-grade peer median; "
    else:
        position_note = "peer group too small for a grade comparison; "
    raise_note = (
        f"last raised {months_since_increment:.0f} months ago"
        if inputs.last_increment_date
        else "never received an increment"
    )
    return DriverContribution(
        key="compensation_trajectory",
        label="Compensation trajectory",
        explanation=position_note + raise_note,
        risk_points=risk,
        weight_share=0.0,
    )


def _engagement(inputs: ScoringInputs) -> DriverContribution | None:
    if inputs.engagement_score is None:
        return None
    risk = max(0.0, min(100.0, 100.0 - inputs.engagement_score))
    return DriverContribution(
        key="engagement",
        label="Engagement",
        explanation=f"Engagement score {inputs.engagement_score:.0f}/100",
        risk_points=risk,
        weight_share=0.0,
    )


def _manager_effectiveness(inputs: ScoringInputs) -> DriverContribution | None:
    if inputs.manager_effectiveness_score is None:
        return None
    risk = max(0.0, min(100.0, 100.0 - inputs.manager_effectiveness_score))
    return DriverContribution(
        key="manager_effectiveness",
        label="Manager effectiveness",
        explanation=f"Manager effectiveness score {inputs.manager_effectiveness_score:.0f}/100",
        risk_points=risk,
        weight_share=0.0,
    )


def _performance_recognition_gap(
    inputs: ScoringInputs, promotion_risk: float, compensation_risk: float
) -> DriverContribution | None:
    if inputs.performance_rating is None:
        return None
    is_strong_performer = inputs.performance_rating >= _STRONG_PERFORMER_THRESHOLD
    is_stagnant = promotion_risk >= 50.0 or compensation_risk >= 50.0
    triggered = is_strong_performer and is_stagnant
    explanation = (
        f"Performance rating {inputs.performance_rating:.1f} despite stagnant "
        "promotion/compensation signals"
        if triggered
        else f"Performance rating {inputs.performance_rating:.1f}, no recognition gap detected"
    )
    return DriverContribution(
        key="performance_recognition_gap",
        label="Strong performer, limited recent reward",
        explanation=explanation,
        risk_points=100.0 if triggered else 0.0,
        weight_share=0.0,
    )


def score_employee(inputs: ScoringInputs) -> ScoreResult:
    """Compute a 0-100 Workforce Health / Flight Risk score with a driver breakdown.

    Pure function: same inputs always produce the same output, no I/O, no
    randomness, nothing trained. See the module docstring for the formula.
    """
    promotion = _promotion_stagnation(inputs)
    compensation = _compensation_trajectory(inputs)
    engagement = _engagement(inputs)
    manager_effectiveness = _manager_effectiveness(inputs)
    performance_recognition_gap = _performance_recognition_gap(
        inputs, promotion.risk_points, compensation.risk_points
    )

    candidates: dict[str, DriverContribution] = {"promotion_stagnation": promotion, "compensation_trajectory": compensation}
    if engagement is not None:
        candidates["engagement"] = engagement
    if manager_effectiveness is not None:
        candidates["manager_effectiveness"] = manager_effectiveness
    if performance_recognition_gap is not None:
        candidates["performance_recognition_gap"] = performance_recognition_gap

    total_weight = sum(_WEIGHTS[key] for key in candidates)
    data_completeness = round(total_weight, 4)

    if total_weight <= 0:
        # No usable data at all. Neutral midpoint, flagged via data_completeness=0
        # rather than silently reported as low or high risk.
        return ScoreResult(score=50.0, band=_band_for_score(50.0), band_label=RISK_BAND_LABELS[_band_for_score(50.0)], drivers=[], data_completeness=0.0)

    contributions = {key: driver.risk_points * (_WEIGHTS[key] / total_weight) for key, driver in candidates.items()}
    total_score = max(0.0, min(100.0, sum(contributions.values())))

    drivers_with_share: list[DriverContribution] = []
    for key, driver in candidates.items():
        share = contributions[key] / total_score if total_score > 0 else 1.0 / len(candidates)
        drivers_with_share.append(replace(driver, weight_share=round(share, 4)))
    drivers_with_share.sort(key=lambda d: d.weight_share, reverse=True)

    top_drivers = drivers_with_share[:2]
    for driver in drivers_with_share[2:4]:
        if driver.weight_share >= _MIN_DRIVER_SHARE_TO_SURFACE:
            top_drivers.append(driver)

    band = _band_for_score(total_score)
    return ScoreResult(
        score=round(total_score, 1),
        band=band,
        band_label=RISK_BAND_LABELS[band],
        drivers=top_drivers,
        data_completeness=data_completeness,
    )

"""Fairness / proxy-leakage audit — Module 2, Part 3.

Excluding gender/BU/department/manager identity/location as direct
*inputs* to score_employee() (see app/scoring/model.py) isn't sufficient
on its own — a formula can still be unfair by proxy if a legitimate input
it does use happens to correlate with a protected attribute in this
specific workforce (e.g. if compensation or promotion timing differs
systematically by gender in the real data). This module is where those
attributes are deliberately read, for exactly one purpose: checking
whether the *scores* end up differing systematically across groups, not
feeding them back into the score itself.

This is intentionally NOT full statistical rigor (no significance
testing) — MODULE2_REFERENCE.md is explicit that the confidence signal
here should be honest about small-sample sizes (as few as ~18 employees
total, often far fewer per group) rather than dressed up as more certain
than it is. `_confidence()` below is a plain bucket by group size, and
`flagged` groups are surfaced as "worth investigating", never as proof.

Manager is handled with a different framing per the reference doc: a
manager whose team shows elevated scores is a useful, *intended* insight
(pointing at where to invest manager support), not something to mask
like the protected-attribute checks above.

This entire module is meaningless to expose to anyone but HR — the
access gate lives in the router (app/routers/workforce_health.py), not
here, but nothing in this module should ever be called from a non-HR
code path.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

# Below this many employees in a group, don't even compute a confidence
# bucket — just report the group exists and how many are in it.
_MIN_GROUP_SIZE_TO_REPORT = 3
_MIN_GROUP_SIZE_FOR_MEDIUM_CONFIDENCE = 5
_MIN_GROUP_SIZE_FOR_HIGHER_CONFIDENCE = 10

# A manager's team is almost always smaller than a demographic group in
# this dataset, so it gets its own (smaller) size floor rather than being
# silently excluded from ever surfacing.
_MIN_MANAGER_TEAM_SIZE = 2

# Points on the 0-100 score scale a group's mean must differ from the
# overall population mean by before it's flagged as worth a look.
_FLAG_GAP_THRESHOLD = 10.0


@dataclass(frozen=True)
class EmployeeScoreForAudit:
    """One employee's already-computed score plus the protected/manager
    attributes the audit needs — and only the audit. Never pass this
    into score_employee()."""

    employee_id: int
    score: float
    gender: str | None
    business_unit_name: str
    department_name: str
    location: str | None
    manager_id: int | None
    manager_name: str | None


@dataclass(frozen=True)
class GroupStat:
    group_value: str
    n: int
    mean_score: float
    gap_from_overall: float
    confidence: str  # "insufficient_data" | "low" | "medium" | "higher"
    flagged: bool


@dataclass(frozen=True)
class AttributeAudit:
    attribute: str
    overall_mean: float
    overall_n: int
    groups: list[GroupStat] = field(default_factory=list)
    excluded_missing_data: int = 0


@dataclass(frozen=True)
class ManagerAudit:
    manager_id: int
    manager_name: str
    team_n: int
    team_mean_score: float
    gap_from_overall: float
    confidence: str
    flagged: bool


@dataclass(frozen=True)
class FairnessAuditResult:
    overall_mean_score: float
    overall_n: int
    attribute_audits: list[AttributeAudit]
    manager_audits: list[ManagerAudit]


def _confidence(n: int) -> str:
    if n < _MIN_GROUP_SIZE_TO_REPORT:
        return "insufficient_data"
    if n < _MIN_GROUP_SIZE_FOR_MEDIUM_CONFIDENCE:
        return "low"
    if n < _MIN_GROUP_SIZE_FOR_HIGHER_CONFIDENCE:
        return "medium"
    return "higher"


def _audit_attribute(
    scores: list[EmployeeScoreForAudit],
    attribute: str,
    value_getter,
    overall_mean: float,
) -> AttributeAudit:
    groups: dict[str, list[float]] = {}
    excluded = 0
    for s in scores:
        value = value_getter(s)
        if value is None or value == "":
            excluded += 1
            continue
        groups.setdefault(value, []).append(s.score)

    group_stats: list[GroupStat] = []
    for value, group_scores in sorted(groups.items()):
        n = len(group_scores)
        mean_score = statistics.mean(group_scores)
        gap = mean_score - overall_mean
        confidence = _confidence(n)
        flagged = confidence != "insufficient_data" and abs(gap) >= _FLAG_GAP_THRESHOLD
        group_stats.append(
            GroupStat(
                group_value=value,
                n=n,
                mean_score=round(mean_score, 1),
                gap_from_overall=round(gap, 1),
                confidence=confidence,
                flagged=flagged,
            )
        )
    group_stats.sort(key=lambda g: abs(g.gap_from_overall), reverse=True)

    return AttributeAudit(
        attribute=attribute,
        overall_mean=round(overall_mean, 1),
        overall_n=len(scores),
        groups=group_stats,
        excluded_missing_data=excluded,
    )


def _audit_managers(scores: list[EmployeeScoreForAudit], overall_mean: float) -> list[ManagerAudit]:
    teams: dict[int, tuple[str, list[float]]] = {}
    for s in scores:
        if s.manager_id is None:
            continue
        name, existing = teams.get(s.manager_id, (s.manager_name or "", []))
        existing.append(s.score)
        teams[s.manager_id] = (s.manager_name or name, existing)

    audits: list[ManagerAudit] = []
    for manager_id, (name, team_scores) in teams.items():
        n = len(team_scores)
        if n < _MIN_MANAGER_TEAM_SIZE:
            continue
        mean_score = statistics.mean(team_scores)
        gap = mean_score - overall_mean
        confidence = _confidence(n)
        flagged = confidence != "insufficient_data" and gap >= _FLAG_GAP_THRESHOLD
        audits.append(
            ManagerAudit(
                manager_id=manager_id,
                manager_name=name,
                team_n=n,
                team_mean_score=round(mean_score, 1),
                gap_from_overall=round(gap, 1),
                confidence=confidence,
                flagged=flagged,
            )
        )
    audits.sort(key=lambda m: m.gap_from_overall, reverse=True)
    return audits


def build_fairness_audit(scores: list[EmployeeScoreForAudit]) -> FairnessAuditResult:
    if not scores:
        return FairnessAuditResult(overall_mean_score=0.0, overall_n=0, attribute_audits=[], manager_audits=[])

    overall_mean = statistics.mean(s.score for s in scores)

    attribute_audits = [
        _audit_attribute(scores, "gender", lambda s: s.gender, overall_mean),
        _audit_attribute(scores, "business_unit", lambda s: s.business_unit_name, overall_mean),
        _audit_attribute(scores, "department", lambda s: s.department_name, overall_mean),
        _audit_attribute(scores, "location", lambda s: s.location, overall_mean),
    ]
    manager_audits = _audit_managers(scores, overall_mean)

    return FairnessAuditResult(
        overall_mean_score=round(overall_mean, 1),
        overall_n=len(scores),
        attribute_audits=attribute_audits,
        manager_audits=manager_audits,
    )

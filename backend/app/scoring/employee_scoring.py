"""Shared "fetch active employees + compute peer groups + score them" logic
used by both app/routers/workforce_health.py (the live views) and
app/exports/workforce_health_report.py (Module 4's export). Extracted from
workforce_health.py rather than duplicated, so the export can never quietly
drift from what the live Workforce Health views actually compute.

business_unit_id here is an additional filter on top of whatever the
caller's RLS scope already restricted `select(Employee)` to (see
app/database.py / app/security/deps.py) — for an HR export of a single BU,
this makes the peer group (and therefore every score) computed from
exactly that BU's employees, the same as what an actual BU Head sees live
for their own BU, rather than silently using org-wide peer groups for a
report titled as one BU's. See app/routers/exports.py's docstring for the
full reasoning.
"""

from __future__ import annotations

import datetime as dt
import statistics
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.employee import Employee
from app.scoring.model import ScoreResult, ScoringInputs, score_employee


def _with_relations(stmt):
    return stmt.options(
        selectinload(Employee.department),
        selectinload(Employee.business_unit),
        selectinload(Employee.manager),
    )


def fetch_active_employees(db: Session, *, business_unit_id: int | None = None) -> list[Employee]:
    stmt = _with_relations(select(Employee).where(Employee.employment_status == "active"))
    if business_unit_id is not None:
        stmt = stmt.where(Employee.business_unit_id == business_unit_id)
    return list(db.scalars(stmt).all())


def peer_ctc_by_grade(employees: list[Employee]) -> dict[str, list[tuple[int, float]]]:
    by_grade: dict[str, list[tuple[int, float]]] = {}
    for e in employees:
        if e.ctc_annual is not None:
            by_grade.setdefault(e.grade, []).append((e.id, float(e.ctc_annual)))
    return by_grade


def peer_median_and_size(employee: Employee, by_grade: dict[str, list[tuple[int, float]]]) -> tuple[float | None, int]:
    peers = [ctc for eid, ctc in by_grade.get(employee.grade, []) if eid != employee.id]
    if not peers:
        return None, 0
    return statistics.median(peers), len(peers)


def to_scoring_inputs(
    employee: Employee, peer_median: float | None, peer_size: int, as_of: dt.date
) -> ScoringInputs:
    return ScoringInputs(
        as_of=as_of,
        date_of_joining=employee.date_of_joining,
        grade=employee.grade,
        last_promotion_date=employee.last_promotion_date,
        last_increment_date=employee.last_increment_date,
        ctc_annual=float(employee.ctc_annual) if employee.ctc_annual is not None else None,
        peer_median_ctc_at_grade=peer_median,
        peer_group_size=peer_size,
        performance_rating=float(employee.performance_rating) if employee.performance_rating is not None else None,
        engagement_score=float(employee.engagement_score) if employee.engagement_score is not None else None,
        manager_effectiveness_score=(
            float(employee.manager_effectiveness_score)
            if employee.manager_effectiveness_score is not None
            else None
        ),
    )


@dataclass(frozen=True)
class ScoredEmployee:
    employee: Employee
    result: ScoreResult


def score_active_employees(db: Session, *, business_unit_id: int | None = None) -> list[ScoredEmployee]:
    """The one function both the live summary endpoint and the export call
    to get "every active employee in scope, scored" — peer groups are
    always computed from that same in-scope set, never a wider one.
    """
    employees = fetch_active_employees(db, business_unit_id=business_unit_id)
    by_grade = peer_ctc_by_grade(employees)
    as_of = dt.date.today()
    return [
        ScoredEmployee(employee=e, result=score_employee(to_scoring_inputs(e, *peer_median_and_size(e, by_grade), as_of)))
        for e in employees
    ]

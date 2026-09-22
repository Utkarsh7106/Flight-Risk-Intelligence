"""Workforce Health API — Module 2, Part 4.

Same enforcement pattern as app/routers/employees.py throughout: RLS is
the sole authority (every query below runs under whatever
app.current_role/app.current_bu_id get_current_user's RLS-context setup
established for this request; nothing here adds a manual role/BU
filter), and get_employee_score's 404-on-invisible-row behavior is
identical to employees.get_employee. There are no sort/filter query
params on any endpoint here, so there's no allow-list to build — the
guardrail from ARCHITECTURE.md (hardcoded allow-lists, never getattr())
has nothing to apply to in this module.

Peer-group compensation comparisons (grade -> median CTC) are computed
in-memory from whatever employees the current request's RLS scope makes
visible — an HR request sees the whole org, a BU Head's request
naturally only sees their own BU, entirely as a side effect of the same
query every other endpoint already runs. No BU/role branching is written
here to produce that; see app/scoring/model.py's docstring and the
Part 1 commit message for the full reasoning.
"""

from __future__ import annotations

import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.app_user import AppUser
from app.models.employee import Employee
from app.schemas.workforce_health import (
    AttributeAuditOut,
    BandCounts,
    BusinessUnitSummary,
    DriverOut,
    EmployeeScoreOut,
    FairnessAuditOut,
    HotspotEmployee,
    ManagerAuditOut,
    RecommendationOut,
    WorkforceHealthSummary,
)
from app.scoring.employee_scoring import (
    fetch_active_employees,
    peer_ctc_by_grade,
    peer_median_and_size,
    to_scoring_inputs,
)
from app.scoring.fairness_audit import EmployeeScoreForAudit, build_fairness_audit
from app.scoring.model import score_employee
from app.scoring.recommendations import recommend
from app.security.deps import get_current_user, require_hr

router = APIRouter(prefix="/workforce-health", tags=["workforce-health"])

_HOTSPOT_COUNT = 5


def _with_relations(stmt):
    return stmt.options(
        selectinload(Employee.department),
        selectinload(Employee.business_unit),
        selectinload(Employee.manager),
    )


def _get_employee_or_404(db: Session, employee_id: int) -> Employee:
    stmt = _with_relations(select(Employee).where(Employee.id == employee_id))
    employee = db.scalar(stmt)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return employee


@router.get("/summary", response_model=WorkforceHealthSummary)
def get_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[AppUser, Depends(get_current_user)],
) -> WorkforceHealthSummary:
    employees = fetch_active_employees(db)
    if not employees:
        empty_bands = BandCounts(low=0, medium=0, high=0, critical=0)
        return WorkforceHealthSummary(
            employee_count=0, average_score=0.0, band_counts=empty_bands, business_units=[], hotspots=[]
        )

    by_grade = peer_ctc_by_grade(employees)
    as_of = dt.date.today()
    scored = [
        (e, score_employee(to_scoring_inputs(e, *peer_median_and_size(e, by_grade), as_of)))
        for e in employees
    ]

    band_totals = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    bu_groups: dict[int, dict] = {}
    for employee, result in scored:
        band_totals[result.band.value] += 1
        bucket = bu_groups.setdefault(
            employee.business_unit_id,
            {"name": employee.business_unit.name, "scores": [], "bands": {"low": 0, "medium": 0, "high": 0, "critical": 0}},
        )
        bucket["scores"].append(result.score)
        bucket["bands"][result.band.value] += 1

    business_units = [
        BusinessUnitSummary(
            business_unit_id=bu_id,
            business_unit_name=data["name"],
            employee_count=len(data["scores"]),
            average_score=round(sum(data["scores"]) / len(data["scores"]), 1),
            band_counts=BandCounts(**data["bands"]),
        )
        for bu_id, data in bu_groups.items()
    ]
    business_units.sort(key=lambda b: b.average_score, reverse=True)

    hotspots = sorted(scored, key=lambda pair: pair[1].score, reverse=True)[:_HOTSPOT_COUNT]
    hotspot_out = [
        HotspotEmployee(
            employee_id=employee.id,
            full_name=employee.full_name,
            business_unit_name=employee.business_unit.name,
            department_name=employee.department.name,
            score=result.score,
            band=result.band.value,
        )
        for employee, result in hotspots
    ]

    all_scores = [result.score for _, result in scored]
    return WorkforceHealthSummary(
        employee_count=len(scored),
        average_score=round(sum(all_scores) / len(all_scores), 1),
        band_counts=BandCounts(**band_totals),
        business_units=business_units,
        hotspots=hotspot_out,
    )


@router.get("/employees/{employee_id}", response_model=EmployeeScoreOut)
def get_employee_score(
    employee_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[AppUser, Depends(get_current_user)],
) -> EmployeeScoreOut:
    employee = _get_employee_or_404(db, employee_id)
    peers = fetch_active_employees(db)
    by_grade = peer_ctc_by_grade(peers)
    peer_median, peer_size = peer_median_and_size(employee, by_grade)
    inputs = to_scoring_inputs(employee, peer_median, peer_size, dt.date.today())
    result = score_employee(inputs)
    recommendations = recommend(result)

    return EmployeeScoreOut(
        employee_id=employee.id,
        full_name=employee.full_name,
        avatar_url=employee.avatar_url,
        designation=employee.designation,
        grade=employee.grade,
        business_unit=employee.business_unit,
        department=employee.department,
        score=result.score,
        band=result.band.value,
        band_label=result.band_label,
        data_completeness=result.data_completeness,
        drivers=[DriverOut.model_validate(d) for d in result.drivers],
        recommendations=[RecommendationOut.model_validate(r) for r in recommendations],
    )


@router.get("/fairness-audit", response_model=FairnessAuditOut)
def get_fairness_audit(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[AppUser, Depends(require_hr)],
) -> FairnessAuditOut:
    employees = fetch_active_employees(db)
    by_grade = peer_ctc_by_grade(employees)
    as_of = dt.date.today()

    audit_inputs = []
    for employee in employees:
        peer_median, peer_size = peer_median_and_size(employee, by_grade)
        inputs = to_scoring_inputs(employee, peer_median, peer_size, as_of)
        result = score_employee(inputs)
        audit_inputs.append(
            EmployeeScoreForAudit(
                employee_id=employee.id,
                score=result.score,
                gender=employee.gender,
                business_unit_name=employee.business_unit.name,
                department_name=employee.department.name,
                location=employee.location,
                manager_id=employee.manager_id,
                manager_name=employee.manager.full_name if employee.manager else None,
            )
        )

    audit = build_fairness_audit(audit_inputs)
    return FairnessAuditOut(
        overall_mean_score=audit.overall_mean_score,
        overall_n=audit.overall_n,
        attribute_audits=[AttributeAuditOut.model_validate(a) for a in audit.attribute_audits],
        manager_audits=[ManagerAuditOut.model_validate(m) for m in audit.manager_audits],
    )

"""Risk Analysis API — Module 3, the ML/SHAP demonstration surface.

Same enforcement pattern as app/routers/employees.py and
app/routers/workforce_health.py throughout: RLS is the sole authority
(nothing here adds a manual role/BU filter), and sort/filter query
params go through a hardcoded allow-list, never getattr(). See
MODULE3_REFERENCE.md for why synthetic_employee carries RLS at all.

Every endpoint here filters to employment_status == 'active' — the
'separated' rows are labeled training examples only (see
app/synthetic/generate.py), never served through this API. There is no
fairness-audit endpoint in this module; that's Module 2's, over real
scoring inputs, and stays there.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.database import get_db
from app.models.app_user import AppUser
from app.models.synthetic_employee import SyntheticEmployee
from app.schemas.risk_analysis import (
    RiskAnalysisSummary,
    RiskBandCounts,
    RiskBusinessUnitSummary,
    RiskDriverOut,
    RiskHotspotEmployee,
    SyntheticEmployeeDetailOut,
    SyntheticEmployeeListResponse,
)
from app.security.deps import get_current_user

router = APIRouter(prefix="/risk-analysis", tags=["risk-analysis"])

_HOTSPOT_COUNT = 5

# Hardcoded allow-list — same discipline as app/routers/employees.py's
# SORT_COLUMNS. sort_by only ever indexes into this dict.
SORT_COLUMNS: dict[str, InstrumentedAttribute] = {
    "full_name": SyntheticEmployee.full_name,
    "employee_code": SyntheticEmployee.employee_code,
    "grade": SyntheticEmployee.grade,
    "predicted_probability": SyntheticEmployee.predicted_probability,
}
SortBy = Literal["full_name", "employee_code", "grade", "predicted_probability"]


def _with_relations(stmt: Select) -> Select:
    return stmt.options(selectinload(SyntheticEmployee.department), selectinload(SyntheticEmployee.business_unit))


def _active_stmt() -> Select:
    return select(SyntheticEmployee).where(SyntheticEmployee.employment_status == "active")


def _get_active_or_404(db: Session, employee_id: int) -> SyntheticEmployee:
    stmt = _with_relations(_active_stmt().where(SyntheticEmployee.id == employee_id))
    row = db.scalar(stmt)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return row


@router.get("/summary", response_model=RiskAnalysisSummary)
def get_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[AppUser, Depends(get_current_user)],
) -> RiskAnalysisSummary:
    rows = list(db.scalars(_with_relations(_active_stmt())))
    if not rows:
        empty_bands = RiskBandCounts(low=0, medium=0, high=0, critical=0)
        return RiskAnalysisSummary(
            employee_count=0, average_probability=0.0, band_counts=empty_bands, business_units=[], hotspots=[]
        )

    band_totals = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    bu_groups: dict[int, dict] = {}
    for row in rows:
        band_totals[row.risk_band] += 1
        bucket = bu_groups.setdefault(
            row.business_unit_id,
            {"name": row.business_unit.name, "probs": [], "bands": {"low": 0, "medium": 0, "high": 0, "critical": 0}},
        )
        bucket["probs"].append(float(row.predicted_probability))
        bucket["bands"][row.risk_band] += 1

    business_units = [
        RiskBusinessUnitSummary(
            business_unit_id=bu_id,
            business_unit_name=data["name"],
            employee_count=len(data["probs"]),
            average_probability=round(sum(data["probs"]) / len(data["probs"]), 4),
            band_counts=RiskBandCounts(**data["bands"]),
        )
        for bu_id, data in bu_groups.items()
    ]
    business_units.sort(key=lambda b: b.average_probability, reverse=True)

    hotspots = sorted(rows, key=lambda r: float(r.predicted_probability), reverse=True)[:_HOTSPOT_COUNT]
    hotspot_out = [
        RiskHotspotEmployee(
            employee_id=r.id,
            full_name=r.full_name,
            business_unit_name=r.business_unit.name,
            department_name=r.department.name,
            predicted_probability=float(r.predicted_probability),
            risk_band=r.risk_band,
        )
        for r in hotspots
    ]

    all_probs = [float(r.predicted_probability) for r in rows]
    return RiskAnalysisSummary(
        employee_count=len(rows),
        average_probability=round(sum(all_probs) / len(all_probs), 4),
        band_counts=RiskBandCounts(**band_totals),
        business_units=business_units,
        hotspots=hotspot_out,
    )


@router.get("/employees", response_model=SyntheticEmployeeListResponse)
def list_employees(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[AppUser, Depends(get_current_user)],
    business_unit_id: int | None = None,
    department_id: int | None = None,
    grade: Literal["L1", "L2", "L3", "L4", "L5", "L6"] | None = None,
    risk_band: Literal["low", "medium", "high", "critical"] | None = None,
    q: str | None = None,
    sort_by: SortBy = "predicted_probability",
    sort_dir: Literal["asc", "desc"] = "desc",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SyntheticEmployeeListResponse:
    stmt = _active_stmt()
    if business_unit_id is not None:
        stmt = stmt.where(SyntheticEmployee.business_unit_id == business_unit_id)
    if department_id is not None:
        stmt = stmt.where(SyntheticEmployee.department_id == department_id)
    if grade is not None:
        stmt = stmt.where(SyntheticEmployee.grade == grade)
    if risk_band is not None:
        stmt = stmt.where(SyntheticEmployee.risk_band == risk_band)
    if q is not None:
        pattern = f"%{q}%"
        stmt = stmt.where(SyntheticEmployee.full_name.ilike(pattern) | SyntheticEmployee.employee_code.ilike(pattern))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    column = SORT_COLUMNS[sort_by]
    order = column.asc() if sort_dir == "asc" else column.desc()
    paged = _with_relations(stmt).order_by(order).limit(limit).offset(offset)
    rows = db.scalars(paged).all()

    return SyntheticEmployeeListResponse(items=list(rows), total=total, limit=limit, offset=offset)


@router.get("/employees/{employee_id}", response_model=SyntheticEmployeeDetailOut)
def get_employee_detail(
    employee_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[AppUser, Depends(get_current_user)],
) -> SyntheticEmployeeDetailOut:
    row = _get_active_or_404(db, employee_id)
    drivers = [RiskDriverOut.model_validate(d) for d in (row.shap_drivers or [])]

    return SyntheticEmployeeDetailOut(
        id=row.id,
        employee_code=row.employee_code,
        full_name=row.full_name,
        avatar_url=row.avatar_url,
        designation=row.designation,
        grade=row.grade,
        business_unit=row.business_unit,
        department=row.department,
        predicted_probability=float(row.predicted_probability),
        risk_band=row.risk_band,
        drivers=drivers,
    )

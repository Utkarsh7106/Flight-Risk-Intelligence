from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.database import get_db
from app.models.app_user import AppUser
from app.models.employee import Employee
from app.schemas.employee import EmployeeListResponse, EmployeeOut
from app.security.deps import get_current_user

router = APIRouter(prefix="/employees", tags=["employees"])

# Hardcoded allow-list: sort_by only ever indexes into this dict, never
# getattr() on a user-supplied string. SortBy (below) also constrains the
# incoming value to this same set before it ever reaches this dict, so an
# invalid column is rejected by FastAPI/Pydantic (422) before any SQL is
# built. See ARCHITECTURE.md security guardrails.
SORT_COLUMNS: dict[str, InstrumentedAttribute] = {
    "full_name": Employee.full_name,
    "employee_code": Employee.employee_code,
    "date_of_joining": Employee.date_of_joining,
    "grade": Employee.grade,
    "designation": Employee.designation,
    "location": Employee.location,
    "ctc_annual": Employee.ctc_annual,
    "performance_rating": Employee.performance_rating,
}

SortBy = Literal[
    "full_name", "employee_code", "date_of_joining", "grade",
    "designation", "location", "ctc_annual", "performance_rating",
]


def _apply_filters(
    stmt: Select,
    *,
    business_unit_id: int | None,
    department_id: int | None,
    grade: str | None,
    employment_status: str,
    location: str | None,
    q: str | None,
) -> Select:
    if business_unit_id is not None:
        stmt = stmt.where(Employee.business_unit_id == business_unit_id)
    if department_id is not None:
        stmt = stmt.where(Employee.department_id == department_id)
    if grade is not None:
        stmt = stmt.where(Employee.grade == grade)
    if employment_status != "all":
        stmt = stmt.where(Employee.employment_status == employment_status)
    if location is not None:
        stmt = stmt.where(Employee.location == location)
    if q is not None:
        pattern = f"%{q}%"
        stmt = stmt.where(
            Employee.full_name.ilike(pattern)
            | Employee.employee_code.ilike(pattern)
            | Employee.designation.ilike(pattern)
        )
    return stmt


def _with_relations(stmt: Select) -> Select:
    return stmt.options(
        selectinload(Employee.department),
        selectinload(Employee.business_unit),
        selectinload(Employee.manager),
    )


@router.get("", response_model=EmployeeListResponse)
def list_employees(
    # employment_status defaults to "active", not unfiltered (Module 4):
    # once departure_events.py can actually create 'separated' rows, an
    # unfiltered default would mix departed employees into the ordinary
    # directory silently. "all" is the explicit opt-in to see everyone;
    # "separated" is the explicit "former employees" view. See
    # MODULE4_REFERENCE.md's "should vanish from the ordinary directory
    # view by default, but remain visible somewhere" and
    # frontend/src/pages/directory/DirectoryFilters.tsx's status dropdown.
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[AppUser, Depends(get_current_user)],
    business_unit_id: int | None = None,
    department_id: int | None = None,
    grade: Literal["L1", "L2", "L3", "L4", "L5", "L6"] | None = None,
    employment_status: Literal["active", "separated", "all"] = "active",
    location: str | None = None,
    q: str | None = None,
    sort_by: SortBy = "full_name",
    sort_dir: Literal["asc", "desc"] = "asc",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EmployeeListResponse:
    filtered = _apply_filters(
        select(Employee),
        business_unit_id=business_unit_id,
        department_id=department_id,
        grade=grade,
        employment_status=employment_status,
        location=location,
        q=q,
    )

    total = db.scalar(select(func.count()).select_from(filtered.subquery())) or 0

    column = SORT_COLUMNS[sort_by]
    order = column.asc() if sort_dir == "asc" else column.desc()
    paged = _with_relations(filtered).order_by(order).limit(limit).offset(offset)
    rows = db.scalars(paged).all()

    return EmployeeListResponse(items=list(rows), total=total, limit=limit, offset=offset)


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(
    employee_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[AppUser, Depends(get_current_user)],
) -> Employee:
    stmt = _with_relations(select(Employee).where(Employee.id == employee_id))
    employee = db.scalar(stmt)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return employee

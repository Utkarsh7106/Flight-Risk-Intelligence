"""Departure/separation event capture — Module 4, Part A.

The `departure_event` table, the `mark_employee_separated` trigger (flips
`employee.employment_status` to 'separated' on insert), and RLS policies
on this table all already existed from Module 1 (migration
5c6bf1a73a67) — nothing here needed a schema migration. This router is
just the first thing that actually writes to it.

Access control (documented per MODULE4_REFERENCE.md's explicit "decide
and document" ask): **a BU Head may record a departure for an employee
in their own BU; HR may record one for anyone.** This mirrors, rather
than invents, a decision Module 1 already made: the
`departure_event_bu_head_scoped` RLS policy is `FOR ALL` (not just
SELECT), scoped to `business_unit_id = current_bu_id` — i.e. the schema
was already built assuming BU Heads can write here, not just read.
Overriding that at the app layer to be HR-only would mean maintaining an
app-level restriction the database layer was deliberately built not to
have. It also matches the realistic workflow MODULE4_REFERENCE.md
describes: a BU Head is usually the first to know when their own report
resigns.

Enforcement follows every prior module's pattern: RLS is the real
authority, not a manual role/BU check in this file. A BU Head's request
body can *ask* for any employee_id; the SELECT on `employee` (Part 1
below) only returns rows already in the caller's BU, and even if that
read were ever buggy, the INSERT's WITH CHECK on `departure_event`
independently rejects a business_unit_id that doesn't match
`app.current_bu_id`. Two independent enforcement points, same as
ARCHITECTURE.md's defense-in-depth section describes everywhere else.
"""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.database import get_db
from app.models.app_user import AppUser
from app.models.departure_event import DepartureEvent
from app.models.employee import Employee
from app.schemas.departure_event import (
    DepartureEventCreate,
    DepartureEventListResponse,
    DepartureEventOut,
    DepartureType,
)
from app.security.deps import get_current_user

router = APIRouter(prefix="/departure-events", tags=["departure-events"])

# Same hardcoded allow-list discipline as every other router in this app.
SORT_COLUMNS: dict[str, InstrumentedAttribute] = {
    "departure_date": DepartureEvent.departure_date,
    "created_at": DepartureEvent.created_at,
}
SortBy = Literal["departure_date", "created_at"]


def _with_relations(stmt: Select) -> Select:
    return stmt.options(
        selectinload(DepartureEvent.employee),
        selectinload(DepartureEvent.business_unit),
        selectinload(DepartureEvent.department),
        selectinload(DepartureEvent.recorded_by),
    )


@router.post("", response_model=DepartureEventOut, status_code=status.HTTP_201_CREATED)
def record_departure(
    payload: DepartureEventCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[AppUser, Depends(get_current_user)],
) -> DepartureEvent:
    # RLS on `employee` already scopes this SELECT to what the caller may
    # see (all of it for HR, own-BU only for a BU Head) — same honest
    # "not found" as every other cross-BU lookup in this app, not a 403
    # that would confirm the id exists in a BU the caller can't see.
    employee = db.scalar(select(Employee).where(Employee.id == payload.employee_id))
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    if employee.employment_status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee is already recorded as separated",
        )

    if payload.departure_date < employee.date_of_joining:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="departure_date cannot be before the employee's date_of_joining",
        )
    if payload.departure_date > dt.date.today() + dt.timedelta(days=400):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="departure_date is too far in the future",
        )

    event = DepartureEvent(
        employee_id=employee.id,
        # Snapshotted from the employee's current values, never from the
        # request body — see DepartureEventCreate's docstring.
        business_unit_id=employee.business_unit_id,
        department_id=employee.department_id,
        departure_date=payload.departure_date,
        last_working_day=payload.last_working_day,
        departure_type=payload.departure_type,
        reason_category=payload.reason_category,
        reason_notes=payload.reason_notes,
        is_regretted=payload.is_regretted,
        notice_period_days=payload.notice_period_days,
        recorded_by_user_id=current_user.id,
    )
    db.add(event)
    db.flush()  # let the AFTER INSERT trigger flip employee.employment_status before commit
    db.refresh(event)

    row = db.scalar(_with_relations(select(DepartureEvent).where(DepartureEvent.id == event.id)))
    assert row is not None
    return row


@router.get("", response_model=DepartureEventListResponse)
def list_departures(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[AppUser, Depends(get_current_user)],
    business_unit_id: int | None = None,
    department_id: int | None = None,
    departure_type: DepartureType | None = None,
    sort_by: SortBy = "departure_date",
    sort_dir: Literal["asc", "desc"] = "desc",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DepartureEventListResponse:
    stmt = select(DepartureEvent)
    if business_unit_id is not None:
        stmt = stmt.where(DepartureEvent.business_unit_id == business_unit_id)
    if department_id is not None:
        stmt = stmt.where(DepartureEvent.department_id == department_id)
    if departure_type is not None:
        stmt = stmt.where(DepartureEvent.departure_type == departure_type)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    column = SORT_COLUMNS[sort_by]
    order = column.asc() if sort_dir == "asc" else column.desc()
    paged = _with_relations(stmt).order_by(order).limit(limit).offset(offset)
    rows = db.scalars(paged).all()

    return DepartureEventListResponse(items=list(rows), total=total, limit=limit, offset=offset)

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.schemas.employee import BusinessUnitRef, DepartmentRef

DepartureType = Literal["voluntary", "involuntary", "retirement", "other"]

# A deliberately small, flat reason taxonomy per departure_type — granular
# enough to be useful in a leadership review ("how much of our voluntary
# attrition is comp-driven vs. relocation?"), not so granular it becomes a
# form nobody finishes filling out. reason_category is optional at the API
# level (departure_type alone already satisfies "voluntary vs. involuntary
# at minimum" from MODULE4_REFERENCE.md) but validated against this table
# when provided, so the column never accumulates freehand near-duplicates
# ("Better Offer" vs "better offer" vs "Better $$"). The DB column itself
# stays a plain String(50) with no CHECK constraint (see
# models/departure_event.py) — this taxonomy is an application-layer
# decision, not a schema one, so it can be revised without a migration.
REASON_CATEGORIES: dict[DepartureType, tuple[str, ...]] = {
    "voluntary": (
        "better_opportunity",
        "compensation",
        "relocation",
        "higher_education",
        "career_change",
        "work_life_balance",
        "family_or_personal",
        "other_voluntary",
    ),
    "involuntary": (
        "performance_managed_out",
        "redundancy_or_restructuring",
        "policy_violation",
        "other_involuntary",
    ),
    "retirement": ("retirement",),
    "other": ("unspecified",),
}


class AppUserRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str


class EmployeeRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_code: str
    full_name: str
    grade: str
    designation: str | None


class DepartureEventCreate(BaseModel):
    """Request body for POST /departure-events.

    employee_id is the only thing the caller picks that determines
    access: the router looks the employee up under the caller's own RLS
    scope, so a BU Head supplying another BU's employee_id gets the same
    honest 404 as every other cross-BU lookup in this app (see
    app/routers/departure_events.py). business_unit_id/department_id are
    never accepted from the client — they're snapshotted server-side from
    the employee's current values, both because a client-supplied BU id
    would be a way to try to defeat the departure_event RLS INSERT policy,
    and because the whole point of snapshotting (see
    models/departure_event.py) is that it reflects where the employee
    actually was, not something a form could get wrong.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    employee_id: int
    departure_date: dt.date
    last_working_day: dt.date | None = None
    departure_type: DepartureType
    reason_category: str | None = None
    reason_notes: str | None = None
    is_regretted: bool | None = None
    notice_period_days: int | None = None

    @field_validator("reason_notes")
    @classmethod
    def _cap_notes_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 2000:
            raise ValueError("reason_notes must be 2000 characters or fewer")
        return v or None

    @field_validator("notice_period_days")
    @classmethod
    def _notice_period_nonnegative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("notice_period_days cannot be negative")
        return v

    @model_validator(mode="after")
    def _reason_category_matches_type(self) -> "DepartureEventCreate":
        if self.reason_category is not None:
            allowed = REASON_CATEGORIES[self.departure_type]
            if self.reason_category not in allowed:
                raise ValueError(
                    f"reason_category {self.reason_category!r} is not valid for departure_type "
                    f"{self.departure_type!r}; expected one of {allowed}"
                )
        if self.last_working_day is not None and self.last_working_day > self.departure_date:
            raise ValueError("last_working_day cannot be after departure_date")
        return self


class DepartureEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee: EmployeeRef
    business_unit: BusinessUnitRef
    department: DepartmentRef
    departure_date: dt.date
    last_working_day: dt.date | None
    departure_type: DepartureType
    reason_category: str | None
    reason_notes: str | None
    is_regretted: bool | None
    notice_period_days: int | None
    recorded_by: AppUserRef | None
    created_at: dt.datetime


class DepartureEventListResponse(BaseModel):
    items: list[DepartureEventOut]
    total: int
    limit: int
    offset: int

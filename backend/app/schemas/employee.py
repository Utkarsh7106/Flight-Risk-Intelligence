from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, computed_field


class DepartmentRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class BusinessUnitRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ManagerRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str


class EmployeeOut(BaseModel):
    """Directory view — table and card layouts both read from this shape.

    Deliberately excludes gender, date_of_birth, and phone. gender is
    ARCHITECTURE.md-mandated (HR-only fairness-audit endpoint later, never
    the ordinary directory). date_of_birth is an age proxy, excluded in
    the same spirit. phone is contact PII with no role in a flight-risk
    view. Do not add any of the three here without updating
    ARCHITECTURE.md and docs/superpowers/specs/2026-09-20-employee-directory-endpoint-design.md.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_code: str
    full_name: str
    email: str
    avatar_url: str | None
    designation: str | None
    grade: str
    location: str | None
    employment_status: str
    date_of_joining: dt.date

    department: DepartmentRef
    business_unit: BusinessUnitRef
    manager: ManagerRef | None

    ctc_annual: float | None
    last_increment_date: dt.date | None
    last_increment_pct: float | None
    last_promotion_date: dt.date | None
    performance_rating: float | None
    engagement_score: float | None
    manager_effectiveness_score: float | None

    @computed_field
    @property
    def tenure_years(self) -> float:
        days = (dt.date.today() - self.date_of_joining).days
        return round(days / 365.25, 1)


class EmployeeListResponse(BaseModel):
    items: list[EmployeeOut]
    total: int
    limit: int
    offset: int

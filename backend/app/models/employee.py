from __future__ import annotations

import datetime as dt

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Employee(Base):
    """Shape mirrors the ~27-column baseline panel this build is anchored to
    (see ARCHITECTURE.md — that panel is a hackathon-era stand-in, not live data).

    gender/business_unit_id/department_id/manager_id/location are stored here for
    the directory and for the Module 2 fairness/proxy audit, but Module 2's
    scoring function signature must not take them as direct inputs — that
    exclusion lives in the scoring code, not the schema.
    """

    __tablename__ = "employee"
    __table_args__ = (
        CheckConstraint("grade IN ('L1','L2','L3','L4','L5','L6')", name="ck_employee_grade"),
        CheckConstraint("gender IN ('Male','Female','Other') OR gender IS NULL", name="ck_employee_gender"),
        CheckConstraint("employment_status IN ('active','separated')", name="ck_employee_status"),
        CheckConstraint(
            "performance_rating IS NULL OR (performance_rating BETWEEN 1 AND 5)",
            name="ck_employee_performance_rating",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    date_of_birth: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    date_of_joining: Mapped[dt.date] = mapped_column(Date, nullable=False)

    department_id: Mapped[int] = mapped_column(ForeignKey("department.id"), nullable=False)
    # Kept in sync with department.business_unit_id by a DB trigger (see
    # migration 0002) so it can never drift. Denormalized here so RLS
    # policies and BU-scoped queries don't need a join on every row check.
    business_unit_id: Mapped[int] = mapped_column(ForeignKey("business_unit.id"), nullable=False)

    designation: Mapped[str | None] = mapped_column(String(120), nullable=True)
    grade: Mapped[str] = mapped_column(String(2), nullable=False)
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("employee.id"), nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    ctc_annual: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    last_increment_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    last_increment_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    last_promotion_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)

    # Real range in the baseline panel is ~2.0-4.7, not a clean 1-5 scale.
    performance_rating: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    engagement_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    manager_effectiveness_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    employment_status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="active", server_default="active"
    )

    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    department: Mapped["Department"] = relationship(foreign_keys=[department_id])
    business_unit: Mapped["BusinessUnit"] = relationship(foreign_keys=[business_unit_id])
    manager: Mapped["Employee | None"] = relationship(remote_side=[id])

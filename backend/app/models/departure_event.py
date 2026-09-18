from __future__ import annotations

import datetime as dt

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class DepartureEvent(Base):
    """Separation-event capture. Infrastructure for future survival analysis
    (explicitly deferred until real events accumulate) — the entry-mechanism
    UI is Module 4; this table just needs to exist and be correct now.
    """

    __tablename__ = "departure_event"
    __table_args__ = (
        CheckConstraint(
            "departure_type IN ('voluntary','involuntary','retirement','other')",
            name="ck_departure_event_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"), nullable=False)

    # Snapshotted at time of departure (not a live join) so BU/department
    # history survives later org-structure changes.
    business_unit_id: Mapped[int] = mapped_column(ForeignKey("business_unit.id"), nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("department.id"), nullable=False)

    departure_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    last_working_day: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    departure_type: Mapped[str] = mapped_column(String(15), nullable=False)
    reason_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reason_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_regretted: Mapped[bool | None] = mapped_column(nullable=True)
    notice_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    recorded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now(), nullable=False)

    employee: Mapped["Employee"] = relationship()

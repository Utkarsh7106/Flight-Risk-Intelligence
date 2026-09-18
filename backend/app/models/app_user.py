from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class AppUser(Base):
    """Auth account. Role is fixed per account — there is no role-toggle in
    the UI, so a bu_head account is structurally tied to exactly one BU.
    """

    __tablename__ = "app_user"
    __table_args__ = (
        CheckConstraint("role IN ('hr','bu_head')", name="ck_app_user_role"),
        CheckConstraint(
            "(role = 'hr' AND business_unit_id IS NULL) "
            "OR (role = 'bu_head' AND business_unit_id IS NOT NULL)",
            name="ck_app_user_bu_scope",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False)

    # NULL for hr (sees everything), required for bu_head — enforced by
    # ck_app_user_bu_scope above, not just application logic.
    business_unit_id: Mapped[int | None] = mapped_column(ForeignKey("business_unit.id"), nullable=True)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employee.id"), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now(), nullable=False)
    last_login_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)

    business_unit: Mapped["BusinessUnit | None"] = relationship()

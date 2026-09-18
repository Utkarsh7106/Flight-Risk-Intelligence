from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Department(Base):
    """Department names repeat across business units (e.g. "Growth" under two
    different BUs), so uniqueness is scoped to (business_unit_id, name), not global.
    """

    __tablename__ = "department"
    __table_args__ = (UniqueConstraint("business_unit_id", "name", name="uq_department_bu_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_unit_id: Mapped[int] = mapped_column(ForeignKey("business_unit.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    business_unit: Mapped["BusinessUnit"] = relationship(back_populates="departments")

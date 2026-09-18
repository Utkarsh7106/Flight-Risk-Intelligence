from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BusinessUnit(Base):
    """One of the 5 real business units (see ARCHITECTURE.md). Reference data."""

    __tablename__ = "business_unit"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    departments: Mapped[list["Department"]] = relationship(back_populates="business_unit")

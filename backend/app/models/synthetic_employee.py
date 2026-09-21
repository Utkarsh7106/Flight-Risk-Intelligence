from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class SyntheticEmployee(Base):
    """Module 3's demonstration dataset — own table, own namespace, never
    mixed with `employee`. See MODULE3_REFERENCE.md for why this dataset
    exists and how `employment_status`/label generation work here.

    `employment_status='separated'` rows are the synthetic labeled
    training examples (a probabilistic departure label was generated for
    them — see app/synthetic/generate.py); they are not served through
    the demo API. `employment_status='active'` rows are "the current
    synthetic workforce" — the set the trained model actually scores and
    the demo UI displays. `predicted_probability`/`risk_band`/
    `shap_drivers` are populated only for active rows, once, by
    app/synthetic/train.py — not recomputed per request (see reference
    doc's "deliberate proof-of-concept simplification").

    Feature exclusion mirrors Module 2 exactly: gender/business_unit_id/
    department_id/location are stored here (for display and because this
    dataset still follows the real org structure) but are not part of the
    model's feature vector — that exclusion lives in
    app/synthetic/features.py, the single choke point, same pattern as
    app/scoring/model.py's ScoringInputs.
    """

    __tablename__ = "synthetic_employee"
    __table_args__ = (
        CheckConstraint("grade IN ('L1','L2','L3','L4','L5','L6')", name="ck_synthetic_employee_grade"),
        CheckConstraint("gender IN ('Male','Female','Other') OR gender IS NULL", name="ck_synthetic_employee_gender"),
        CheckConstraint("employment_status IN ('active','separated')", name="ck_synthetic_employee_status"),
        CheckConstraint(
            "risk_band IS NULL OR risk_band IN ('low','medium','high','critical')",
            name="ck_synthetic_employee_risk_band",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    date_of_joining: Mapped[dt.date] = mapped_column(Date, nullable=False)

    department_id: Mapped[int] = mapped_column(ForeignKey("department.id"), nullable=False)
    # Same trigger-synced denormalization as employee.business_unit_id (see
    # migration for this table) — kept so RLS/BU-scoped queries never join.
    business_unit_id: Mapped[int] = mapped_column(ForeignKey("business_unit.id"), nullable=False)

    designation: Mapped[str | None] = mapped_column(String(120), nullable=True)
    grade: Mapped[str] = mapped_column(String(2), nullable=False)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)

    ctc_annual: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    last_increment_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    last_promotion_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)

    performance_rating: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    engagement_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    manager_effectiveness_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)

    # Signals Module 2's scorecard never reads (see MODULE3_REFERENCE.md —
    # deliberately so this model has real, independent signal available).
    overtime: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    job_satisfaction_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    distance_from_home_km: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)

    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    employment_status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")

    # Populated once by app/synthetic/train.py, for active rows only.
    predicted_probability: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    risk_band: Mapped[str | None] = mapped_column(String(10), nullable=True)
    shap_drivers: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now(), nullable=False)

    department: Mapped["Department"] = relationship(foreign_keys=[department_id])
    business_unit: Mapped["BusinessUnit"] = relationship(foreign_keys=[business_unit_id])

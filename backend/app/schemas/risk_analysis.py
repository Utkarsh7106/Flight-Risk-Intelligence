from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schemas.employee import BusinessUnitRef, DepartmentRef


class RiskDriverOut(BaseModel):
    """One SHAP-attributed feature contribution. Precomputed by
    app/synthetic/train.py, not recomputed per request — see
    MODULE3_REFERENCE.md."""

    feature: str
    label: str
    value: float
    shap_value: float
    explanation: str


class SyntheticEmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_code: str
    full_name: str
    avatar_url: str | None
    designation: str | None
    grade: str
    business_unit: BusinessUnitRef
    department: DepartmentRef
    predicted_probability: float
    risk_band: str


class SyntheticEmployeeListResponse(BaseModel):
    items: list[SyntheticEmployeeOut]
    total: int
    limit: int
    offset: int


class SyntheticEmployeeDetailOut(BaseModel):
    id: int
    employee_code: str
    full_name: str
    avatar_url: str | None
    designation: str | None
    grade: str
    business_unit: BusinessUnitRef
    department: DepartmentRef
    predicted_probability: float
    risk_band: str
    drivers: list[RiskDriverOut]


class RiskBandCounts(BaseModel):
    low: int
    medium: int
    high: int
    critical: int


class RiskBusinessUnitSummary(BaseModel):
    business_unit_id: int
    business_unit_name: str
    employee_count: int
    average_probability: float
    band_counts: RiskBandCounts


class RiskHotspotEmployee(BaseModel):
    employee_id: int
    full_name: str
    business_unit_name: str
    department_name: str
    predicted_probability: float
    risk_band: str


class RiskAnalysisSummary(BaseModel):
    employee_count: int
    average_probability: float
    band_counts: RiskBandCounts
    business_units: list[RiskBusinessUnitSummary]
    hotspots: list[RiskHotspotEmployee]

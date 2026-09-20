from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schemas.employee import BusinessUnitRef, DepartmentRef


class DriverOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    label: str
    explanation: str
    risk_points: float
    weight_share: float


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    title: str
    rationale: str


class EmployeeScoreOut(BaseModel):
    employee_id: int
    full_name: str
    avatar_url: str | None
    designation: str | None
    grade: str
    business_unit: BusinessUnitRef
    department: DepartmentRef
    score: float
    band: str
    band_label: str
    data_completeness: float
    drivers: list[DriverOut]
    recommendations: list[RecommendationOut]


class BandCounts(BaseModel):
    low: int
    medium: int
    high: int
    critical: int


class BusinessUnitSummary(BaseModel):
    business_unit_id: int
    business_unit_name: str
    employee_count: int
    average_score: float
    band_counts: BandCounts


class HotspotEmployee(BaseModel):
    employee_id: int
    full_name: str
    business_unit_name: str
    department_name: str
    score: float
    band: str


class WorkforceHealthSummary(BaseModel):
    employee_count: int
    average_score: float
    band_counts: BandCounts
    business_units: list[BusinessUnitSummary]
    hotspots: list[HotspotEmployee]


class GroupStatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    group_value: str
    n: int
    mean_score: float
    gap_from_overall: float
    confidence: str
    flagged: bool


class AttributeAuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attribute: str
    overall_mean: float
    overall_n: int
    groups: list[GroupStatOut]
    excluded_missing_data: int


class ManagerAuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    manager_id: int
    manager_name: str
    team_n: int
    team_mean_score: float
    gap_from_overall: float
    confidence: str
    flagged: bool


class FairnessAuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    overall_mean_score: float
    overall_n: int
    attribute_audits: list[AttributeAuditOut]
    manager_audits: list[ManagerAuditOut]

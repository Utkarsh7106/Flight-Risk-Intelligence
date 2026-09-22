/**
 * Mirrors backend/app/schemas/*.py exactly. Keep in sync by hand — there's
 * no shared codegen between the two right now, on purpose (small surface,
 * not worth the tooling yet).
 */

export type Role = 'hr' | 'bu_head';

export interface CurrentUser {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  business_unit_id: number | null;
}

export type Grade = 'L1' | 'L2' | 'L3' | 'L4' | 'L5' | 'L6';
export type EmploymentStatus = 'active' | 'separated';
/** GET /employees' employment_status query param — "all" is the explicit
 * opt-in to see everyone; the backend defaults this to "active" when the
 * param is omitted entirely (see backend/app/routers/employees.py). */
export type EmploymentStatusFilter = EmploymentStatus | 'all';

export interface DepartmentRef {
  id: number;
  name: string;
}

export interface BusinessUnitRef {
  id: number;
  name: string;
}

export interface ManagerRef {
  id: number;
  full_name: string;
}

/** Deliberately has no gender, date_of_birth, or phone field — the backend
 * never sends them (app/schemas/employee.py excludes them by design, per
 * ARCHITECTURE.md). Do not add them here to "complete" this type; there's
 * nothing in the API response to back them.
 */
export interface Employee {
  id: number;
  employee_code: string;
  full_name: string;
  email: string;
  avatar_url: string | null;
  designation: string | null;
  grade: Grade;
  location: string | null;
  employment_status: EmploymentStatus;
  date_of_joining: string;
  department: DepartmentRef;
  business_unit: BusinessUnitRef;
  manager: ManagerRef | null;
  ctc_annual: number | null;
  last_increment_date: string | null;
  last_increment_pct: number | null;
  last_promotion_date: string | null;
  performance_rating: number | null;
  engagement_score: number | null;
  manager_effectiveness_score: number | null;
  tenure_years: number;
}

export interface EmployeeListResponse {
  items: Employee[];
  total: number;
  limit: number;
  offset: number;
}

/** Matches SORT_COLUMNS in backend/app/routers/employees.py exactly — this
 * is the real allow-list, not a guess. If the backend adds a sortable
 * column, add it here too; the UI's sort dropdown reads from this list.
 */
export const SORTABLE_FIELDS = [
  'full_name',
  'employee_code',
  'date_of_joining',
  'grade',
  'designation',
  'location',
  'ctc_annual',
  'performance_rating',
] as const;

export type SortBy = (typeof SORTABLE_FIELDS)[number];
export type SortDir = 'asc' | 'desc';

export interface EmployeeQuery {
  business_unit_id?: number;
  department_id?: number;
  grade?: Grade;
  employment_status?: EmploymentStatusFilter;
  location?: string;
  q?: string;
  sort_by?: SortBy;
  sort_dir?: SortDir;
  limit?: number;
  offset?: number;
}

/**
 * Mirrors backend/app/schemas/workforce_health.py — Module 2. See
 * MODULE2_REFERENCE.md and backend/app/scoring/model.py for what these
 * fields mean; this file only mirrors shape, not logic.
 */
export type RiskBand = 'low' | 'medium' | 'high' | 'critical';

export interface Driver {
  key: string;
  label: string;
  explanation: string;
  risk_points: number;
  weight_share: number;
}

export interface Recommendation {
  key: string;
  title: string;
  rationale: string;
}

export interface EmployeeScore {
  employee_id: number;
  full_name: string;
  avatar_url: string | null;
  designation: string | null;
  grade: Grade;
  business_unit: BusinessUnitRef;
  department: DepartmentRef;
  score: number;
  band: RiskBand;
  band_label: string;
  data_completeness: number;
  drivers: Driver[];
  recommendations: Recommendation[];
}

export interface BandCounts {
  low: number;
  medium: number;
  high: number;
  critical: number;
}

export interface BusinessUnitSummary {
  business_unit_id: number;
  business_unit_name: string;
  employee_count: number;
  average_score: number;
  band_counts: BandCounts;
}

export interface HotspotEmployee {
  employee_id: number;
  full_name: string;
  business_unit_name: string;
  department_name: string;
  score: number;
  band: RiskBand;
}

export interface WorkforceHealthSummary {
  employee_count: number;
  average_score: number;
  band_counts: BandCounts;
  business_units: BusinessUnitSummary[];
  hotspots: HotspotEmployee[];
}

/** "insufficient_data" | "low" | "medium" | "higher" — a plain group-size
 * bucket, deliberately not a p-value. See fairness_audit.py's docstring.
 */
export type AuditConfidence = 'insufficient_data' | 'low' | 'medium' | 'higher';

export interface GroupStat {
  group_value: string;
  n: number;
  mean_score: number;
  gap_from_overall: number;
  confidence: AuditConfidence;
  flagged: boolean;
}

export interface AttributeAudit {
  attribute: 'gender' | 'business_unit' | 'department' | 'location';
  overall_mean: number;
  overall_n: number;
  groups: GroupStat[];
  excluded_missing_data: number;
}

export interface ManagerAudit {
  manager_id: number;
  manager_name: string;
  team_n: number;
  team_mean_score: number;
  gap_from_overall: number;
  confidence: AuditConfidence;
  flagged: boolean;
}

export interface FairnessAudit {
  overall_mean_score: number;
  overall_n: number;
  attribute_audits: AttributeAudit[];
  manager_audits: ManagerAudit[];
}

/**
 * Mirrors backend/app/schemas/risk_analysis.py — Module 3, the ML/SHAP
 * demonstration surface. This is a SEPARATE synthetic dataset, never the
 * Employee Directory or Workforce Health baseline panel — see
 * MODULE3_REFERENCE.md. `RiskDriver.shap_value` is a real, signed SHAP
 * contribution (positive = pushed predicted risk up), not a 0-100
 * risk_points/weight_share pair like Module 2's Driver — the two types
 * are deliberately not unified, since the underlying computation differs
 * even though the UI reuses the same visual pattern.
 */
export interface RiskDriver {
  feature: string;
  label: string;
  value: number;
  shap_value: number;
  explanation: string;
}

export interface SyntheticEmployeeSummary {
  id: number;
  employee_code: string;
  full_name: string;
  avatar_url: string | null;
  designation: string | null;
  grade: Grade;
  business_unit: BusinessUnitRef;
  department: DepartmentRef;
  predicted_probability: number;
  risk_band: RiskBand;
}

export interface SyntheticEmployeeListResponse {
  items: SyntheticEmployeeSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface SyntheticEmployeeDetail {
  id: number;
  employee_code: string;
  full_name: string;
  avatar_url: string | null;
  designation: string | null;
  grade: Grade;
  business_unit: BusinessUnitRef;
  department: DepartmentRef;
  predicted_probability: number;
  risk_band: RiskBand;
  drivers: RiskDriver[];
}

export interface RiskBusinessUnitSummary {
  business_unit_id: number;
  business_unit_name: string;
  employee_count: number;
  average_probability: number;
  band_counts: BandCounts;
}

export interface RiskHotspotEmployee {
  employee_id: number;
  full_name: string;
  business_unit_name: string;
  department_name: string;
  predicted_probability: number;
  risk_band: RiskBand;
}

export interface RiskAnalysisSummary {
  employee_count: number;
  average_probability: number;
  band_counts: BandCounts;
  business_units: RiskBusinessUnitSummary[];
  hotspots: RiskHotspotEmployee[];
}

/**
 * Mirrors backend/app/schemas/departure_event.py — Module 4, Part A. The
 * entry mechanism on top of the departure_event table/trigger that
 * existed since Module 1. See MODULE4_REFERENCE.md and
 * backend/app/routers/departure_events.py's docstring for the access-
 * control reasoning (a BU Head may record a departure for their own BU;
 * HR for anyone).
 */
export type DepartureType = 'voluntary' | 'involuntary' | 'retirement' | 'other';

/** Copied verbatim from backend/app/schemas/departure_event.py's
 * REASON_CATEGORIES — keep the two in sync by hand, same discipline as
 * SORTABLE_FIELDS above. reason_category is optional; when provided it
 * must be one of the values for the selected departure_type. */
export const REASON_CATEGORIES: Record<DepartureType, { value: string; label: string }[]> = {
  voluntary: [
    { value: 'better_opportunity', label: 'Better opportunity' },
    { value: 'compensation', label: 'Compensation' },
    { value: 'relocation', label: 'Relocation' },
    { value: 'higher_education', label: 'Higher education' },
    { value: 'career_change', label: 'Career change' },
    { value: 'work_life_balance', label: 'Work-life balance' },
    { value: 'family_or_personal', label: 'Family or personal' },
    { value: 'other_voluntary', label: 'Other' },
  ],
  involuntary: [
    { value: 'performance_managed_out', label: 'Performance managed out' },
    { value: 'redundancy_or_restructuring', label: 'Redundancy / restructuring' },
    { value: 'policy_violation', label: 'Policy violation' },
    { value: 'other_involuntary', label: 'Other' },
  ],
  retirement: [{ value: 'retirement', label: 'Retirement' }],
  other: [{ value: 'unspecified', label: 'Unspecified' }],
};

export interface DepartureEmployeeRef {
  id: number;
  employee_code: string;
  full_name: string;
  grade: Grade;
  designation: string | null;
}

export interface RecordedByRef {
  id: number;
  full_name: string;
}

export interface DepartureEvent {
  id: number;
  employee: DepartureEmployeeRef;
  business_unit: BusinessUnitRef;
  department: DepartmentRef;
  departure_date: string;
  last_working_day: string | null;
  departure_type: DepartureType;
  reason_category: string | null;
  reason_notes: string | null;
  is_regretted: boolean | null;
  notice_period_days: number | null;
  recorded_by: RecordedByRef | null;
  created_at: string;
}

export interface DepartureEventListResponse {
  items: DepartureEvent[];
  total: number;
  limit: number;
  offset: number;
}

export interface DepartureEventCreate {
  employee_id: number;
  departure_date: string;
  last_working_day?: string | null;
  departure_type: DepartureType;
  reason_category?: string | null;
  reason_notes?: string | null;
  is_regretted?: boolean | null;
  notice_period_days?: number | null;
}

export interface DepartureQuery {
  business_unit_id?: number;
  department_id?: number;
  departure_type?: DepartureType;
  sort_by?: 'departure_date' | 'created_at';
  sort_dir?: SortDir;
  limit?: number;
  offset?: number;
}

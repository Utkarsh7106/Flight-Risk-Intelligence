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
  employment_status?: EmploymentStatus;
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

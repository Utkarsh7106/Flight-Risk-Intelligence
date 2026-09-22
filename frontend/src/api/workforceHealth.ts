import { apiRequest } from './client';
import type { EmployeeScore, EmploymentStatusFilter, FairnessAudit, WorkforceHealthSummary } from './types';

/** No role/BU branching lives here, same rule as api/employees.ts — RLS
 * scopes the result, this function just calls the endpoint.
 */
export function getWorkforceHealthSummary(): Promise<WorkforceHealthSummary> {
  return apiRequest<WorkforceHealthSummary>('/workforce-health/summary');
}

/** employmentStatus mirrors listEmployees' same param (Module 4): the
 * backend defaults it to "active", so omitting it 404s a separated
 * employee's score the same way they're already hidden from the default
 * directory/summary views. Callers that already know an employee is
 * separated (e.g. a directory row shown under the "Separated"/"All
 * statuses" filter) pass "all" through to keep that row's score reachable.
 */
export function getEmployeeScore(
  employeeId: number,
  employmentStatus?: EmploymentStatusFilter,
): Promise<EmployeeScore> {
  return apiRequest<EmployeeScore>(`/workforce-health/employees/${employeeId}`, {
    query: { employment_status: employmentStatus },
  });
}

/** Backend 403s any non-HR caller regardless of what this function does —
 * only call it from a screen already gated on user.role === 'hr'. See
 * app/security/deps.py's require_hr and MODULE2_REFERENCE.md.
 */
export function getFairnessAudit(): Promise<FairnessAudit> {
  return apiRequest<FairnessAudit>('/workforce-health/fairness-audit');
}

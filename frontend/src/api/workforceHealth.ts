import { apiRequest } from './client';
import type { EmployeeScore, FairnessAudit, WorkforceHealthSummary } from './types';

/** No role/BU branching lives here, same rule as api/employees.ts — RLS
 * scopes the result, this function just calls the endpoint.
 */
export function getWorkforceHealthSummary(): Promise<WorkforceHealthSummary> {
  return apiRequest<WorkforceHealthSummary>('/workforce-health/summary');
}

export function getEmployeeScore(employeeId: number): Promise<EmployeeScore> {
  return apiRequest<EmployeeScore>(`/workforce-health/employees/${employeeId}`);
}

/** Backend 403s any non-HR caller regardless of what this function does —
 * only call it from a screen already gated on user.role === 'hr'. See
 * app/security/deps.py's require_hr and MODULE2_REFERENCE.md.
 */
export function getFairnessAudit(): Promise<FairnessAudit> {
  return apiRequest<FairnessAudit>('/workforce-health/fairness-audit');
}

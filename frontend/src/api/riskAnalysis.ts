import { apiRequest } from './client';
import type { RiskAnalysisSummary, SyntheticEmployeeDetail } from './types';

/** No role/BU branching lives here, same rule as api/employees.ts and
 * api/workforceHealth.ts — RLS scopes the result, this function just
 * calls the endpoint. This dataset is entirely synthetic — see
 * MODULE3_REFERENCE.md.
 */
export function getRiskAnalysisSummary(): Promise<RiskAnalysisSummary> {
  return apiRequest<RiskAnalysisSummary>('/risk-analysis/summary');
}

export function getRiskEmployeeDetail(employeeId: number): Promise<SyntheticEmployeeDetail> {
  return apiRequest<SyntheticEmployeeDetail>(`/risk-analysis/employees/${employeeId}`);
}

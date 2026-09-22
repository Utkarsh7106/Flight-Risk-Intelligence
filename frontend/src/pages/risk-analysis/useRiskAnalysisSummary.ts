import { useAsync } from '../../hooks/useAsync';
import { getRiskAnalysisSummary } from '../../api/riskAnalysis';
import type { RiskAnalysisSummary } from '../../api/types';

/** Talks to GET /risk-analysis/summary and nothing else — no role/BU
 * branching here, same invariant as useWorkforceHealthSummary.ts. An HR
 * login gets the whole synthetic panel; a BU Head gets their own BU's
 * slice purely because that's what the server returned for their session.
 */
export function useRiskAnalysisSummary() {
  const { data, loadState, errorMessage, retry } = useAsync<RiskAnalysisSummary>(
    getRiskAnalysisSummary,
    [],
    { fallbackErrorMessage: 'Something went wrong loading risk analysis.' },
  );
  return { data, loadState, errorMessage, retry };
}

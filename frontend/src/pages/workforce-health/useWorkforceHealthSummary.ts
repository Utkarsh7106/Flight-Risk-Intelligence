import { useAsync } from '../../hooks/useAsync';
import { getWorkforceHealthSummary } from '../../api/workforceHealth';
import type { WorkforceHealthSummary } from '../../api/types';

/** Talks to GET /workforce-health/summary and nothing else — no role/BU
 * branching here, same invariant as useEmployeeDirectory.ts. An HR login
 * gets an org-wide summary and a BU Head gets their own BU's slice purely
 * because that's what the server returned for their session.
 */
export function useWorkforceHealthSummary() {
  const { data, loadState, errorMessage, retry } = useAsync<WorkforceHealthSummary>(
    getWorkforceHealthSummary,
    [],
    { fallbackErrorMessage: 'Something went wrong loading workforce health.' },
  );
  return { data, loadState, errorMessage, retry };
}

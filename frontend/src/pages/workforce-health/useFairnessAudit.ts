import { useAsync } from '../../hooks/useAsync';
import { getFairnessAudit } from '../../api/workforceHealth';
import type { FairnessAudit } from '../../api/types';

/** `enabled` lets the caller skip the request entirely rather than
 * firing it and handling a 403 — used so a non-HR login never even
 * attempts the call (see FairnessAuditPage's role check). The backend's
 * require_hr gate is the actual security boundary either way; this is
 * only about not making a request the UI already knows will be refused.
 */
export function useFairnessAudit(enabled: boolean) {
  const { data, loadState, errorMessage, retry } = useAsync<FairnessAudit>(getFairnessAudit, [], {
    enabled,
    fallbackErrorMessage: 'Something went wrong loading the fairness audit.',
  });
  return { data, loadState, errorMessage, retry };
}

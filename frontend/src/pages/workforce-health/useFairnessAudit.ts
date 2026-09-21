import { useEffect, useState } from 'react';
import { getFairnessAudit } from '../../api/workforceHealth';
import { ApiError, NetworkError } from '../../api/client';
import type { FairnessAudit } from '../../api/types';

/** `enabled` lets the caller skip the request entirely rather than
 * firing it and handling a 403 — used so a non-HR login never even
 * attempts the call (see FairnessAuditPage's role check). The backend's
 * require_hr gate is the actual security boundary either way; this is
 * only about not making a request the UI already knows will be refused.
 */
export function useFairnessAudit(enabled: boolean) {
  const [data, setData] = useState<FairnessAudit | null>(null);
  const [loadState, setLoadState] = useState<'loading' | 'loaded' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    setLoadState('loading');

    getFairnessAudit()
      .then((response) => {
        if (cancelled) return;
        setData(response);
        setLoadState('loaded');
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError) {
          setErrorMessage(err.detail ?? `Request failed (${err.status}).`);
        } else if (err instanceof NetworkError) {
          setErrorMessage('Unable to reach the server.');
        } else {
          setErrorMessage('Something went wrong loading the fairness audit.');
        }
        setLoadState('error');
      });

    return () => {
      cancelled = true;
    };
  }, [enabled, reloadToken]);

  return { data, loadState, errorMessage, retry: () => setReloadToken((n) => n + 1) };
}

import { useEffect, useState } from 'react';
import { getRiskAnalysisSummary } from '../../api/riskAnalysis';
import { ApiError, NetworkError } from '../../api/client';
import type { RiskAnalysisSummary } from '../../api/types';

/** Talks to GET /risk-analysis/summary and nothing else — no role/BU
 * branching here, same invariant as useWorkforceHealthSummary.ts. An HR
 * login gets the whole synthetic panel; a BU Head gets their own BU's
 * slice purely because that's what the server returned for their session.
 */
export function useRiskAnalysisSummary() {
  const [data, setData] = useState<RiskAnalysisSummary | null>(null);
  const [loadState, setLoadState] = useState<'loading' | 'loaded' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoadState('loading');

    getRiskAnalysisSummary()
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
          setErrorMessage('Something went wrong loading risk analysis.');
        }
        setLoadState('error');
      });

    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  return { data, loadState, errorMessage, retry: () => setReloadToken((n) => n + 1) };
}

import { useEffect, useState } from 'react';
import { listDepartures } from '../../api/departureEvents';
import { ApiError, NetworkError } from '../../api/client';
import type { DepartureEventListResponse } from '../../api/types';

/** Talks to GET /departure-events and nothing else — no role/BU
 * branching here, same invariant as useEmployeeDirectory.ts and every
 * other list hook in this app. An HR login sees every recorded
 * departure; a BU Head sees only their own BU's, purely because that's
 * what the server returned for their session (RLS, not this hook).
 */
export function useDepartures() {
  const [data, setData] = useState<DepartureEventListResponse | null>(null);
  const [loadState, setLoadState] = useState<'loading' | 'loaded' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoadState('loading');

    listDepartures({ limit: 100 })
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
          setErrorMessage('Something went wrong loading departures.');
        }
        setLoadState('error');
      });

    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  return { data, loadState, errorMessage, retry: () => setReloadToken((n) => n + 1) };
}

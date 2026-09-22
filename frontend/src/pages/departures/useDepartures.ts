import { useAsync } from '../../hooks/useAsync';
import { listDepartures } from '../../api/departureEvents';
import type { DepartureEventListResponse } from '../../api/types';

/** Talks to GET /departure-events and nothing else — no role/BU
 * branching here, same invariant as useEmployeeDirectory.ts and every
 * other list hook in this app. An HR login sees every recorded
 * departure; a BU Head sees only their own BU's, purely because that's
 * what the server returned for their session (RLS, not this hook).
 */
export function useDepartures() {
  const { data, loadState, errorMessage, retry } = useAsync<DepartureEventListResponse>(
    () => listDepartures({ limit: 100 }),
    [],
    { fallbackErrorMessage: 'Something went wrong loading departures.' },
  );
  return { data, loadState, errorMessage, retry };
}

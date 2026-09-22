import { useEffect, useState } from 'react';
import { ApiError, NetworkError } from '../api/client';

export type LoadState = 'loading' | 'loaded' | 'error';

export interface UseAsyncOptions {
  /** Skip the request entirely while false, same as useFairnessAudit's
   * pre-existing `enabled` guard — used so a UI that already knows a
   * request will be refused never fires it. loadState stays 'loading'
   * while disabled. Defaults to true. */
  enabled?: boolean;
  /** Shown when the caught error is neither an ApiError nor a NetworkError. */
  fallbackErrorMessage: string;
  /** When true, a 404 ApiError sets `notFound` instead of `errorMessage`
   * (see useEmployeeScore.ts / useRiskEmployeeDetail.ts). Defaults to false. */
  treatNotFoundSeparately?: boolean;
}

export interface UseAsyncResult<T> {
  data: T | null;
  loadState: LoadState;
  errorMessage: string | null;
  notFound: boolean;
  retry: () => void;
}

/** Shared `data`/`loadState`/`errorMessage`/`reloadToken` + effect +
 * cancelled-flag + ApiError/NetworkError branching, factored out of the
 * seven page hooks that each hand-rolled it (workforce health summary,
 * employee score, fairness audit, risk analysis summary, risk employee
 * detail, employee directory, departures). Each of those keeps its own
 * thin wrapper with its own fetcher and error copy — this only owns the
 * boilerplate that was previously duplicated seven times.
 */
export function useAsync<T>(
  fetcher: () => Promise<T>,
  deps: readonly unknown[],
  options: UseAsyncOptions,
): UseAsyncResult<T> {
  const { enabled = true, fallbackErrorMessage, treatNotFoundSeparately = false } = options;

  const [data, setData] = useState<T | null>(null);
  const [loadState, setLoadState] = useState<LoadState>('loading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    setLoadState('loading');
    setNotFound(false);

    fetcher()
      .then((response) => {
        if (cancelled) return;
        setData(response);
        setLoadState('loaded');
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError) {
          if (treatNotFoundSeparately && err.status === 404) {
            setNotFound(true);
          } else {
            setErrorMessage(err.detail ?? `Request failed (${err.status}).`);
          }
        } else if (err instanceof NetworkError) {
          setErrorMessage('Unable to reach the server.');
        } else {
          setErrorMessage(fallbackErrorMessage);
        }
        setLoadState('error');
      });

    return () => {
      cancelled = true;
    };
    // deps is the caller's explicit dependency list (its own filter/id
    // state); enabled and reloadToken are this hook's own.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled, reloadToken]);

  return { data, loadState, errorMessage, notFound, retry: () => setReloadToken((n) => n + 1) };
}

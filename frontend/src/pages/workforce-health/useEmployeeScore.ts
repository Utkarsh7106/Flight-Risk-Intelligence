import { useEffect, useState } from 'react';
import { getEmployeeScore } from '../../api/workforceHealth';
import { ApiError, NetworkError } from '../../api/client';
import type { EmployeeScore } from '../../api/types';

export function useEmployeeScore(employeeId: number) {
  const [data, setData] = useState<EmployeeScore | null>(null);
  const [loadState, setLoadState] = useState<'loading' | 'loaded' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoadState('loading');
    setNotFound(false);

    getEmployeeScore(employeeId)
      .then((response) => {
        if (cancelled) return;
        setData(response);
        setLoadState('loaded');
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError) {
          if (err.status === 404) {
            setNotFound(true);
          } else {
            setErrorMessage(err.detail ?? `Request failed (${err.status}).`);
          }
        } else if (err instanceof NetworkError) {
          setErrorMessage('Unable to reach the server.');
        } else {
          setErrorMessage('Something went wrong loading this employee.');
        }
        setLoadState('error');
      });

    return () => {
      cancelled = true;
    };
  }, [employeeId, reloadToken]);

  return { data, loadState, errorMessage, notFound, retry: () => setReloadToken((n) => n + 1) };
}

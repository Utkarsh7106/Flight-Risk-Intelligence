import { useEffect, useState } from 'react';
import { listEmployees } from '../../api/employees';
import { ApiError, NetworkError } from '../../api/client';
import type { EmployeeListResponse, EmploymentStatus, Grade, SortBy, SortDir } from '../../api/types';

export interface DirectoryFilters {
  q: string;
  grade: Grade | '';
  employment_status: EmploymentStatus | '';
  business_unit_id: number | '';
}

const DEFAULT_FILTERS: DirectoryFilters = { q: '', grade: '', employment_status: '', business_unit_id: '' };
const PAGE_SIZE = 50;
const SEARCH_DEBOUNCE_MS = 300;

/** Owns every piece of state the directory page's data view needs, and —
 * critically — is the one place that talks to GET /employees. It sends
 * exactly the filters the user picked as query params and renders back
 * exactly what the server returns. There is no client-side `.filter()`
 * anywhere in this hook or its callers: the backend's Row-Level Security
 * is the only thing that scopes rows by BU, and duplicating that logic
 * here would be exactly the "second, divergent source of truth" the
 * backend's design explicitly avoided. If a future change adds any kind
 * of role/BU-based filtering to this file, that's a regression.
 */
export function useEmployeeDirectory() {
  const [filters, setFiltersState] = useState<DirectoryFilters>(DEFAULT_FILTERS);
  const [debouncedQ, setDebouncedQ] = useState('');
  const [sortBy, setSortByState] = useState<SortBy>('full_name');
  const [sortDir, setSortDirState] = useState<SortDir>('asc');
  const [offset, setOffset] = useState(0);
  const [reloadToken, setReloadToken] = useState(0);

  const [data, setData] = useState<EmployeeListResponse | null>(null);
  const [loadState, setLoadState] = useState<'loading' | 'loaded' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const handle = setTimeout(() => setDebouncedQ(filters.q), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(handle);
  }, [filters.q]);

  useEffect(() => {
    let cancelled = false;
    setLoadState('loading');

    listEmployees({
      q: debouncedQ || undefined,
      grade: filters.grade || undefined,
      employment_status: filters.employment_status || undefined,
      business_unit_id: filters.business_unit_id === '' ? undefined : filters.business_unit_id,
      sort_by: sortBy,
      sort_dir: sortDir,
      limit: PAGE_SIZE,
      offset,
    })
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
          setErrorMessage('Something went wrong loading the directory.');
        }
        setLoadState('error');
      });

    return () => {
      cancelled = true;
    };
  }, [
    debouncedQ,
    filters.grade,
    filters.employment_status,
    filters.business_unit_id,
    sortBy,
    sortDir,
    offset,
    reloadToken,
  ]);

  function setFilters(next: Partial<DirectoryFilters>) {
    setFiltersState((prev) => ({ ...prev, ...next }));
    setOffset(0);
  }

  function toggleSort(field: SortBy) {
    if (field === sortBy) {
      setSortDirState((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortByState(field);
      setSortDirState('asc');
    }
    setOffset(0);
  }

  function nextPage() {
    if (!data) return;
    if (offset + data.limit < data.total) setOffset(offset + data.limit);
  }

  function previousPage() {
    setOffset(Math.max(0, offset - PAGE_SIZE));
  }

  return {
    filters,
    setFilters,
    sortBy,
    sortDir,
    toggleSort,
    offset,
    pageSize: PAGE_SIZE,
    data,
    loadState,
    errorMessage,
    nextPage,
    previousPage,
    retry: () => setReloadToken((n) => n + 1),
  };
}

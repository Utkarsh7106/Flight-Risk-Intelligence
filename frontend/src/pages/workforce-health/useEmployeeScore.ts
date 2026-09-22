import { useAsync } from '../../hooks/useAsync';
import { getEmployeeScore } from '../../api/workforceHealth';
import type { EmployeeScore, EmploymentStatusFilter } from '../../api/types';

/** employmentStatus threads straight through to getEmployeeScore — see
 * that function's doc for why a separated employee's caller needs to
 * pass "all" explicitly. Omitted (the common case, an active employee),
 * the backend's own "active" default applies. */
export function useEmployeeScore(employeeId: number, employmentStatus?: EmploymentStatusFilter) {
  const { data, loadState, errorMessage, notFound, retry } = useAsync<EmployeeScore>(
    () => getEmployeeScore(employeeId, employmentStatus),
    [employeeId, employmentStatus],
    {
      fallbackErrorMessage: 'Something went wrong loading this employee.',
      treatNotFoundSeparately: true,
    },
  );
  return { data, loadState, errorMessage, notFound, retry };
}

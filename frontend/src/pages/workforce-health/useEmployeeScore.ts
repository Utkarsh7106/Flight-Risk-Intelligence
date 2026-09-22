import { useAsync } from '../../hooks/useAsync';
import { getEmployeeScore } from '../../api/workforceHealth';
import type { EmployeeScore } from '../../api/types';

export function useEmployeeScore(employeeId: number) {
  const { data, loadState, errorMessage, notFound, retry } = useAsync<EmployeeScore>(
    () => getEmployeeScore(employeeId),
    [employeeId],
    {
      fallbackErrorMessage: 'Something went wrong loading this employee.',
      treatNotFoundSeparately: true,
    },
  );
  return { data, loadState, errorMessage, notFound, retry };
}

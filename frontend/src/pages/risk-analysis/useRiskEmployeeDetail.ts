import { useAsync } from '../../hooks/useAsync';
import { getRiskEmployeeDetail } from '../../api/riskAnalysis';
import type { SyntheticEmployeeDetail } from '../../api/types';

export function useRiskEmployeeDetail(employeeId: number) {
  const { data, loadState, errorMessage, notFound, retry } = useAsync<SyntheticEmployeeDetail>(
    () => getRiskEmployeeDetail(employeeId),
    [employeeId],
    {
      fallbackErrorMessage: 'Something went wrong loading this employee.',
      treatNotFoundSeparately: true,
    },
  );
  return { data, loadState, errorMessage, notFound, retry };
}

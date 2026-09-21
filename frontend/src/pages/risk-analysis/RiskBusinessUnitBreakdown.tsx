import type { RiskBusinessUnitSummary } from '../../api/types';
import { Table } from '../../components/ui/Table';
import { RiskBandDistribution } from '../../components/ui/RiskBandDistribution';
import styles from './RiskBusinessUnitBreakdown.module.css';

interface RiskBusinessUnitBreakdownProps {
  businessUnits: RiskBusinessUnitSummary[];
}

/** Same pattern as workforce-health/BusinessUnitBreakdown.tsx — HR sees
 * every business unit, a BU Head sees a one-row table of their own,
 * purely because that's the only row RLS returns. Reuses
 * RiskBandDistribution directly (it's generic over BandCounts, which
 * this module's summary shape also carries).
 */
export function RiskBusinessUnitBreakdown({ businessUnits }: RiskBusinessUnitBreakdownProps) {
  return (
    <Table>
      <thead>
        <tr>
          <th>Business Unit</th>
          <th>Employees</th>
          <th>Average Predicted Risk</th>
          <th>Risk Distribution</th>
        </tr>
      </thead>
      <tbody>
        {businessUnits.map((bu) => (
          <tr key={bu.business_unit_id}>
            <td className="text-body-md">{bu.business_unit_name}</td>
            <td className="text-mono-data">{bu.employee_count}</td>
            <td className="text-mono-data">{(bu.average_probability * 100).toFixed(1)}%</td>
            <td className={styles.distributionCell}>
              <RiskBandDistribution counts={bu.band_counts} />
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

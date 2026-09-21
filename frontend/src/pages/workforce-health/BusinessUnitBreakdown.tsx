import type { BusinessUnitSummary } from '../../api/types';
import { Table } from '../../components/ui/Table';
import { RiskBandDistribution } from './RiskBandDistribution';
import styles from './BusinessUnitBreakdown.module.css';

interface BusinessUnitBreakdownProps {
  businessUnits: BusinessUnitSummary[];
}

/** For HR this lists every business unit — the "BU-specific hotspots"
 * at-a-glance view. For a BU Head it renders as a one-row table of their
 * own BU, because that's the only row RLS ever returns to them; nothing
 * here branches on role to decide that.
 */
export function BusinessUnitBreakdown({ businessUnits }: BusinessUnitBreakdownProps) {
  return (
    <Table>
      <thead>
        <tr>
          <th>Business Unit</th>
          <th>Employees</th>
          <th>Average Score</th>
          <th>Risk Distribution</th>
        </tr>
      </thead>
      <tbody>
        {businessUnits.map((bu) => (
          <tr key={bu.business_unit_id}>
            <td className="text-body-md">{bu.business_unit_name}</td>
            <td className="text-mono-data">{bu.employee_count}</td>
            <td className="text-mono-data">{bu.average_score.toFixed(1)}</td>
            <td className={styles.distributionCell}>
              <RiskBandDistribution counts={bu.band_counts} />
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

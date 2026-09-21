import type { ManagerAudit } from '../../api/types';
import { Badge } from '../../components/ui/Badge';
import { Table } from '../../components/ui/Table';

/** Deliberately different framing from AttributeAuditTable per
 * MODULE2_REFERENCE.md: a manager whose team scores elevated is an
 * intended, actionable insight (where to invest manager support), not a
 * protected-group finding to soften — so this reads "Elevated," not
 * "worth investigating."
 */
export function ManagerAuditTable({ managers }: { managers: ManagerAudit[] }) {
  if (managers.length === 0) {
    return <p className="text-body-md">No manager has enough direct reports yet to assess.</p>;
  }

  return (
    <Table>
      <thead>
        <tr>
          <th>Manager</th>
          <th>Team Size</th>
          <th>Team Mean Score</th>
          <th>Gap vs. Overall</th>
          <th>Confidence</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {managers.map((manager) => (
          <tr key={manager.manager_id}>
            <td className="text-body-md">{manager.manager_name}</td>
            <td className="text-mono-data">{manager.team_n}</td>
            <td className="text-mono-data">{manager.team_mean_score.toFixed(1)}</td>
            <td className="text-mono-data">
              {manager.gap_from_overall > 0 ? '+' : ''}
              {manager.gap_from_overall.toFixed(1)}
            </td>
            <td>
              <Badge tone="neutral">{manager.confidence.replace('_', ' ')}</Badge>
            </td>
            <td>
              {manager.flagged ? <Badge tone="high">Elevated team risk</Badge> : <span className="text-body-md">—</span>}
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

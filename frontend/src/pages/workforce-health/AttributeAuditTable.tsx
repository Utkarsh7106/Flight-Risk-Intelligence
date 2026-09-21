import type { AttributeAudit, AuditConfidence } from '../../api/types';
import { Badge } from '../../components/ui/Badge';
import { Table } from '../../components/ui/Table';

const ATTRIBUTE_LABELS: Record<AttributeAudit['attribute'], string> = {
  gender: 'Gender',
  business_unit: 'Business Unit',
  department: 'Department',
  location: 'Location',
};

const CONFIDENCE_LABELS: Record<AuditConfidence, string> = {
  insufficient_data: 'Too small to assess',
  low: 'Low confidence',
  medium: 'Medium confidence',
  higher: 'Higher confidence',
};

interface AttributeAuditTableProps {
  audit: AttributeAudit;
}

/** Per MODULE2_REFERENCE.md: a flagged gap is "worth investigating," never
 * proof of a problem — the confidence column (a plain group-size bucket,
 * not a p-value) is shown with equal visual weight to the gap itself so
 * nobody reads a 2-person group's number as equivalent to a 15-person
 * group's.
 */
export function AttributeAuditTable({ audit }: AttributeAuditTableProps) {
  return (
    <div>
      <div className="text-body-md" style={{ marginBottom: 'var(--space-sm)' }}>
        {ATTRIBUTE_LABELS[audit.attribute]} — overall average {audit.overall_mean.toFixed(1)} across{' '}
        {audit.overall_n} employees
        {audit.excluded_missing_data > 0 && (
          <span> ({audit.excluded_missing_data} excluded — no {ATTRIBUTE_LABELS[audit.attribute].toLowerCase()} on file)</span>
        )}
      </div>
      <Table>
        <thead>
          <tr>
            <th>Group</th>
            <th>n</th>
            <th>Mean Score</th>
            <th>Gap vs. Overall</th>
            <th>Confidence</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {audit.groups.map((group) => (
            <tr key={group.group_value}>
              <td className="text-body-md">{group.group_value}</td>
              <td className="text-mono-data">{group.n}</td>
              <td className="text-mono-data">{group.mean_score.toFixed(1)}</td>
              <td className="text-mono-data">
                {group.gap_from_overall > 0 ? '+' : ''}
                {group.gap_from_overall.toFixed(1)}
              </td>
              <td>
                <Badge tone="neutral">{CONFIDENCE_LABELS[group.confidence]}</Badge>
              </td>
              <td>
                {group.flagged ? (
                  <Badge tone="medium">Worth investigating</Badge>
                ) : (
                  <span className="text-body-md">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
}

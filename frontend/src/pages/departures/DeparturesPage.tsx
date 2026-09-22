import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Table } from '../../components/ui/Table';
import { REASON_CATEGORIES } from '../../api/types';
import type { DepartureType } from '../../api/types';
import { formatDate } from '../directory/format';
import { useDepartures } from './useDepartures';
import styles from './DeparturesPage.module.css';

const TYPE_LABELS: Record<DepartureType, string> = {
  voluntary: 'Voluntary',
  involuntary: 'Involuntary',
  retirement: 'Retirement',
  other: 'Other',
};

const TYPE_BADGE_TONE: Record<DepartureType, 'neutral' | 'medium' | 'info'> = {
  voluntary: 'info',
  involuntary: 'medium',
  retirement: 'neutral',
  other: 'neutral',
};

function reasonLabel(type: DepartureType, category: string | null): string {
  if (category === null) return '—';
  return REASON_CATEGORIES[type].find((r) => r.value === category)?.label ?? category;
}

/** Module 4, Part A's read side. RLS-scoped the same way every other list
 * in this app is: HR sees every recorded departure, a BU Head sees only
 * their own BU's — see useDepartures.ts and MODULE4_REFERENCE.md.
 */
export function DeparturesPage() {
  const { user } = useAuth();
  const { data, loadState, errorMessage, retry } = useDepartures();
  const isHr = user?.role === 'hr';

  return (
    <div>
      <div className={styles.header}>
        <div>
          <h1 className={`${styles.title} text-headline-md`}>Departures</h1>
          <p className={`${styles.subtitle} text-body-md`}>
            {isHr ? 'Org-wide' : 'Scoped to your business unit by the server, not this screen'} — recorded
            separations, most recent first
          </p>
        </div>
        <Link to="/departures/new">
          <Button variant="primary">Record departure</Button>
        </Link>
      </div>

      {loadState === 'error' && (
        <div className={styles.errorBox}>
          <span className="text-body-md">{errorMessage}</span>
          <Button variant="secondary" onClick={retry}>
            Retry
          </Button>
        </div>
      )}

      {loadState === 'loading' && !data && <div className={styles.stateBox}>Loading departures…</div>}

      {data && data.items.length === 0 && (
        <div className={styles.stateBox}>No departures recorded yet.</div>
      )}

      {data && data.items.length > 0 && (
        <Table>
          <thead>
            <tr>
              <th>Employee</th>
              <th>Business Unit / Dept</th>
              <th>Departure date</th>
              <th>Type</th>
              <th>Reason</th>
              <th>Regretted</th>
              <th>Recorded by</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((item) => (
              <tr key={item.id}>
                <td>
                  <div className={styles.nameCell}>
                    <span className="text-body-md">{item.employee.full_name}</span>
                    <span className={`${styles.muted} text-label-md`}>{item.employee.employee_code}</span>
                  </div>
                </td>
                <td>
                  <div className={styles.orgCell}>
                    <span className="text-body-md">{item.business_unit.name}</span>
                    <span className={`${styles.muted} text-label-md`}>{item.department.name}</span>
                  </div>
                </td>
                <td className="text-mono-data">{formatDate(item.departure_date)}</td>
                <td>
                  <Badge tone={TYPE_BADGE_TONE[item.departure_type]}>{TYPE_LABELS[item.departure_type]}</Badge>
                </td>
                <td>{reasonLabel(item.departure_type, item.reason_category)}</td>
                <td>{item.is_regretted === null ? '—' : item.is_regretted ? 'Yes' : 'No'}</td>
                <td className={styles.muted}>{item.recorded_by?.full_name ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}

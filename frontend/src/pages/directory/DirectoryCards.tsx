import { Avatar } from '../../components/ui/Avatar';
import { Badge } from '../../components/ui/Badge';
import { Card } from '../../components/ui/Card';
import type { Employee } from '../../api/types';
import { formatCtc, formatScore, formatTenure } from './format';
import styles from './DirectoryCards.module.css';

interface DirectoryCardsProps {
  employees: Employee[];
}

/** Same data source and field set as DirectoryTable, different layout —
 * both read from the same GET /employees response passed down from
 * DirectoryPage, so there's no risk of the two views ever disagreeing.
 */
export function DirectoryCards({ employees }: DirectoryCardsProps) {
  return (
    <div className={styles.grid}>
      {employees.map((employee) => (
        <Card key={employee.id}>
          <div className={styles.cardHeader}>
            <Avatar fullName={employee.full_name} size="md" />
            <div className={styles.cardHeaderText}>
              <span className={`${styles.fullName} text-body-lg`}>{employee.full_name}</span>
              <span className={`${styles.designation} text-label-md`}>{employee.designation ?? '—'}</span>
            </div>
          </div>

          <div className={styles.metaRow}>
            <span className={`${styles.metaLabel} text-body-md`}>Business unit</span>
            <span className={`${styles.metaValue} text-body-md`}>{employee.business_unit.name}</span>
          </div>
          <div className={styles.metaRow}>
            <span className={`${styles.metaLabel} text-body-md`}>Department</span>
            <span className={`${styles.metaValue} text-body-md`}>{employee.department.name}</span>
          </div>
          <div className={styles.metaRow}>
            <span className={`${styles.metaLabel} text-body-md`}>Grade</span>
            <span className={`${styles.metaValue} text-body-md`}>{employee.grade}</span>
          </div>
          <div className={styles.metaRow}>
            <span className={`${styles.metaLabel} text-body-md`}>Location</span>
            <span className={`${styles.metaValue} text-body-md`}>{employee.location ?? '—'}</span>
          </div>
          <div className={styles.metaRow}>
            <span className={`${styles.metaLabel} text-body-md`}>Manager</span>
            <span className={`${styles.metaValue} text-body-md`}>{employee.manager?.full_name ?? '—'}</span>
          </div>
          <div className={styles.metaRow}>
            <span className={`${styles.metaLabel} text-body-md`}>Tenure</span>
            <span className={`${styles.metaValue} text-mono-data`}>{formatTenure(employee.tenure_years)}</span>
          </div>
          <div className={styles.metaRow}>
            <span className={`${styles.metaLabel} text-body-md`}>CTC (annual)</span>
            <span className={`${styles.metaValue} text-mono-data`}>{formatCtc(employee.ctc_annual)}</span>
          </div>
          <div className={styles.metaRow}>
            <span className={`${styles.metaLabel} text-body-md`}>Performance</span>
            <span className={`${styles.metaValue} text-mono-data`}>{formatScore(employee.performance_rating)}</span>
          </div>

          <div className={styles.footer}>
            {employee.employment_status === 'active' ? (
              <Badge tone="low" dot>
                Active
              </Badge>
            ) : (
              <Badge tone="neutral" dot>
                Separated
              </Badge>
            )}
          </div>
        </Card>
      ))}
    </div>
  );
}

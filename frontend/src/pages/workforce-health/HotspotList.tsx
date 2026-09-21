import { Link } from 'react-router-dom';
import type { HotspotEmployee } from '../../api/types';
import { Avatar } from '../../components/ui/Avatar';
import { Badge } from '../../components/ui/Badge';
import { Card } from '../../components/ui/Card';
import styles from './HotspotList.module.css';

interface HotspotListProps {
  hotspots: HotspotEmployee[];
}

/** The highest-scored employees currently visible to this login — already
 * scoped by RLS on the backend (see workforce_health.get_summary), so an
 * HR view's hotspots can span BUs and a BU Head's can only ever be their
 * own. Each row links straight to the individual drill-down screen.
 */
export function HotspotList({ hotspots }: HotspotListProps) {
  if (hotspots.length === 0) {
    return <p className="text-body-md">No employees to show.</p>;
  }

  return (
    <div className={styles.list}>
      {hotspots.map((employee) => (
        <Link key={employee.employee_id} to={`/workforce-health/employees/${employee.employee_id}`} className={styles.link}>
          <Card interactive className={styles.row}>
            <div className={styles.identity}>
              <Avatar fullName={employee.full_name} size="sm" />
              <div className={styles.identityText}>
                <span className="text-body-md">{employee.full_name}</span>
                <span className={`${styles.meta} text-label-md`}>
                  {employee.business_unit_name} · {employee.department_name}
                </span>
              </div>
            </div>
            <div className={styles.scoreCell}>
              <span className="text-mono-data">{employee.score.toFixed(1)}</span>
              <Badge tone={employee.band}>{employee.band}</Badge>
            </div>
          </Card>
        </Link>
      ))}
    </div>
  );
}

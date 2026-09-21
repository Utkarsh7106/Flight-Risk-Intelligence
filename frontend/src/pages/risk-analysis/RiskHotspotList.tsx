import { Link } from 'react-router-dom';
import type { RiskHotspotEmployee } from '../../api/types';
import { Avatar } from '../../components/ui/Avatar';
import { Badge } from '../../components/ui/Badge';
import { Card } from '../../components/ui/Card';
import styles from './RiskHotspotList.module.css';

interface RiskHotspotListProps {
  hotspots: RiskHotspotEmployee[];
}

/** Same pattern as workforce-health/HotspotList.tsx — already scoped by
 * RLS on the backend, so an HR view can span BUs and a BU Head's can
 * only ever be their own. Links to this module's own drill-down route.
 */
export function RiskHotspotList({ hotspots }: RiskHotspotListProps) {
  if (hotspots.length === 0) {
    return <p className="text-body-md">No employees to show.</p>;
  }

  return (
    <div className={styles.list}>
      {hotspots.map((employee) => (
        <Link key={employee.employee_id} to={`/risk-analysis/employees/${employee.employee_id}`} className={styles.link}>
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
              <span className="text-mono-data">{(employee.predicted_probability * 100).toFixed(0)}%</span>
              <Badge tone={employee.risk_band}>{employee.risk_band}</Badge>
            </div>
          </Card>
        </Link>
      ))}
    </div>
  );
}

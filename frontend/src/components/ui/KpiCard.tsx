import { Card } from './Card';
import styles from './KpiCard.module.css';

interface KpiCardProps {
  label: string;
  value: string;
  /** Percent change, e.g. 4.2 or -1.8. Omit if there's no trend to show. */
  changePct?: number;
}

/** DESIGN.md "Components": "Large numeric value (Display LG) with ... a
 * semantic 'percent change' indicator." Built now as real infrastructure
 * per Part 1's ask, but nothing in this build wires it to live data yet —
 * that's Module 2 (Workforce Health Index), not built this session. It
 * deliberately has no sparkline: DESIGN.md calls for one, but there's no
 * time-series data anywhere in the API to draw it from honestly, and a
 * fake one would violate the project's no-fabricated-data principle.
 */
export function KpiCard({ label, value, changePct }: KpiCardProps) {
  const trendClass = changePct === undefined ? '' : changePct >= 0 ? styles.trendUp : styles.trendDown;

  return (
    <Card>
      <div className={styles.header}>
        <span className={`${styles.label} text-label-md`}>{label}</span>
      </div>
      <div className={`${styles.value} text-display-lg`}>{value}</div>
      {changePct !== undefined && (
        <div className={`${trendClass} text-body-md`}>
          <span aria-hidden="true">{changePct >= 0 ? '▲' : '▼'}</span>
          <span>{Math.abs(changePct).toFixed(1)}%</span>
        </div>
      )}
    </Card>
  );
}

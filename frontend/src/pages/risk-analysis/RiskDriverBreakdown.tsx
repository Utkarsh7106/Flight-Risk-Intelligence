import type { RiskDriver } from '../../api/types';
import styles from './RiskDriverBreakdown.module.css';

interface RiskDriverBreakdownProps {
  drivers: RiskDriver[];
}

/** Module 3's counterpart to Module 2's DriverBreakdown — deliberately
 * the same visual shape (a labeled bar + explanation per driver) so a
 * user doesn't need a second mental model to read this versus the
 * Workforce Health drill-down, per MODULE3_REFERENCE.md. The underlying
 * numbers differ: `shap_value` is a real, signed SHAP contribution from
 * the trained model (TreeExplainer), not a 0-100 risk_points/weight_share
 * pair — bar length is scaled relative to this employee's own largest
 * |shap_value| (drivers are already the top few by magnitude, sent by
 * the backend), and bar color encodes direction: a driver can genuinely
 * reduce predicted risk, which Module 2's always-additive drivers never do.
 */
export function RiskDriverBreakdown({ drivers }: RiskDriverBreakdownProps) {
  if (drivers.length === 0) {
    return <p className="text-body-md">No driver breakdown available for this employee.</p>;
  }

  const maxAbs = Math.max(...drivers.map((d) => Math.abs(d.shap_value)), 0.0001);

  return (
    <div className={styles.list}>
      {drivers.map((driver) => {
        const increased = driver.shap_value > 0;
        const widthPct = Math.max(4, (Math.abs(driver.shap_value) / maxAbs) * 100);
        return (
          <div key={driver.feature} className={styles.row}>
            <div className={styles.rowHeader}>
              <span className="text-body-md">{driver.label}</span>
              <span className={`${styles.shapValue} text-label-md`}>
                {increased ? '+' : ''}
                {driver.shap_value.toFixed(3)}
              </span>
            </div>
            <div className={styles.track}>
              <div
                className={`${styles.fill} ${increased ? styles.increased : styles.decreased}`}
                style={{ width: `${widthPct}%` }}
              />
            </div>
            <p className={`${styles.explanation} text-body-md`}>{driver.explanation}</p>
          </div>
        );
      })}
    </div>
  );
}

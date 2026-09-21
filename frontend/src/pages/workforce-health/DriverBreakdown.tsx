import type { Driver } from '../../api/types';
import styles from './DriverBreakdown.module.css';

/** Same 35/60/80 thresholds app/scoring/model.py's _band_for_score uses,
 * applied here to a single driver's own 0-100 risk_points reading rather
 * than the overall score — so a driver's bar color answers "how
 * concerning is this factor on its own," independent of how much weight
 * it carried in the final number.
 */
function severityTone(riskPoints: number): 'low' | 'medium' | 'high' | 'critical' {
  if (riskPoints >= 80) return 'critical';
  if (riskPoints >= 60) return 'high';
  if (riskPoints >= 35) return 'medium';
  return 'low';
}

interface DriverBreakdownProps {
  drivers: Driver[];
}

/** The per-driver breakdown is the product, not decoration (see
 * MODULE2_REFERENCE.md's "scoring model" section) — bar length encodes
 * each driver's actual weight_share of the final score (how much it
 * mattered relative to the others), bar color encodes the driver's own
 * risk_points reading (how concerning it is in isolation). Both numbers
 * come straight from the backend's ScoreResult; nothing here recomputes
 * or approximates them.
 */
export function DriverBreakdown({ drivers }: DriverBreakdownProps) {
  return (
    <div className={styles.list}>
      {drivers.map((driver) => {
        const tone = severityTone(driver.risk_points);
        const widthPct = Math.max(4, driver.weight_share * 100);
        return (
          <div key={driver.key} className={styles.row}>
            <div className={styles.rowHeader}>
              <span className="text-body-md">{driver.label}</span>
              <span className={`${styles.sharePct} text-label-md`}>
                {(driver.weight_share * 100).toFixed(0)}% of score
              </span>
            </div>
            <div className={styles.track}>
              <div className={`${styles.fill} ${styles[tone]}`} style={{ width: `${widthPct}%` }} />
            </div>
            <p className={`${styles.explanation} text-body-md`}>{driver.explanation}</p>
          </div>
        );
      })}
    </div>
  );
}

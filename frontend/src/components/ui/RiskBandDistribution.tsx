import type { BandCounts } from '../../api/types';
import styles from './RiskBandDistribution.module.css';

const BANDS: { key: keyof BandCounts; label: string }[] = [
  { key: 'low', label: 'Low' },
  { key: 'medium', label: 'Medium' },
  { key: 'high', label: 'High' },
  { key: 'critical', label: 'Critical' },
];

interface RiskBandDistributionProps {
  counts: BandCounts;
}

/** A single proportional stacked bar plus a legend with counts — the
 * "genuinely visual, not decorative" breakdown the brief asks for, built
 * from the same four risk tokens Badge already uses (see tokens.css's
 * --color-risk-* additions for the "critical" tier).
 */
export function RiskBandDistribution({ counts }: RiskBandDistributionProps) {
  const total = counts.low + counts.medium + counts.high + counts.critical;

  return (
    <div>
      <div className={styles.bar} role="img" aria-label="Risk band distribution">
        {BANDS.map(({ key, label }) => {
          const value = counts[key];
          if (total === 0 || value === 0) return null;
          const widthPct = (value / total) * 100;
          return (
            <div
              key={key}
              className={`${styles.segment} ${styles[key]}`}
              style={{ width: `${widthPct}%` }}
              title={`${label}: ${value}`}
            />
          );
        })}
      </div>
      <div className={styles.legend}>
        {BANDS.map(({ key, label }) => (
          <div key={key} className={styles.legendItem}>
            <span className={`${styles.dot} ${styles[key]}`} aria-hidden="true" />
            <span className="text-body-md">
              {label} <span className={styles.count}>{counts[key]}</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

import type { ReactNode } from 'react';
import styles from './Badge.module.css';

export type BadgeTone = 'low' | 'medium' | 'high' | 'critical' | 'neutral' | 'info';

interface BadgeProps {
  tone?: BadgeTone;
  dot?: boolean;
  children: ReactNode;
}

/** Generic status/tag pill — DESIGN.md's "Status Badges" pattern
 * (low-saturation background, high-saturation text, pill shape). `tone`
 * maps to the semantic risk colors for risk levels, or neutral/info for
 * everything else (e.g. employment status, "coming soon" labels).
 */
export function Badge({ tone = 'neutral', dot = false, children }: BadgeProps) {
  return (
    <span className={`${styles.badge} ${styles[tone]}`}>
      {dot && <span className={styles.dot} aria-hidden="true" />}
      {children}
    </span>
  );
}

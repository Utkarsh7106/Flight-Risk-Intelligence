import type { ReactNode } from 'react';
import styles from './InsightCallout.module.css';

interface InsightCalloutProps {
  children: ReactNode;
}

/** DESIGN.md "Components": "AI-Insight Callouts: ... left-accent border
 * in Cyan and a small 'Sparkle' icon to denote algorithmic intelligence."
 * Infrastructure only tonight — no module in this build actually
 * generates AI/algorithmic commentary yet, so nothing renders this
 * component with real content. It exists so Module 2/3 have a ready,
 * on-system place to put that output rather than inventing a one-off
 * style later.
 */
export function InsightCallout({ children }: InsightCalloutProps) {
  return (
    <div className={styles.callout} role="note">
      <span className={styles.icon} aria-hidden="true">
        ✦
      </span>
      <div className={`${styles.body} text-body-md`}>{children}</div>
    </div>
  );
}

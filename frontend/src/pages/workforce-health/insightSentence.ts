import type { WorkforceHealthSummary } from '../../api/types';

/** A single deterministic, data-derived sentence — not LLM-generated text,
 * consistent with MODULE2_REFERENCE.md's "never LLM-decided" stance for
 * anything that could read as a judgment call. Rendered inside
 * InsightCallout, whose styling signals "the system analyzed this for
 * you," which this honestly is — an algorithmic summary, computed here,
 * of real aggregate numbers, not a fabricated or model-written claim.
 */
export function buildInsightSentence(summary: WorkforceHealthSummary): string {
  if (summary.employee_count === 0) {
    return 'No active employees are currently visible to score.';
  }

  const elevated = summary.band_counts.high + summary.band_counts.critical;
  const elevatedPct = Math.round((elevated / summary.employee_count) * 100);

  let sentence =
    elevated === 0
      ? `All ${summary.employee_count} scored employees are in the Low or Medium risk band.`
      : `${elevated} of ${summary.employee_count} employees (${elevatedPct}%) sit in the High or Critical risk band.`;

  if (summary.business_units.length > 1) {
    const highest = summary.business_units.reduce((a, b) => (b.average_score > a.average_score ? b : a));
    sentence += ` ${highest.business_unit_name} currently has the highest average score (${highest.average_score.toFixed(1)}).`;
  }

  return sentence;
}

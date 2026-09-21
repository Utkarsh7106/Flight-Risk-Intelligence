import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { KpiCard } from '../../components/ui/KpiCard';
import { InsightCallout } from '../../components/ui/InsightCallout';
import { useWorkforceHealthSummary } from './useWorkforceHealthSummary';
import { RiskBandDistribution } from '../../components/ui/RiskBandDistribution';
import { BusinessUnitBreakdown } from './BusinessUnitBreakdown';
import { HotspotList } from './HotspotList';
import { buildInsightSentence } from './insightSentence';
import styles from './WorkforceHealthPage.module.css';

/** HR and BU Head render the exact same component tree — no separate
 * implementation per role, per MODULE2_REFERENCE.md. What differs is only
 * what GET /workforce-health/summary returns for the caller's RLS scope:
 * every business unit for HR, exactly one row for a BU Head.
 */
export function WorkforceHealthPage() {
  const { user } = useAuth();
  const { data, loadState, errorMessage, retry } = useWorkforceHealthSummary();
  const isHr = user?.role === 'hr';

  const subtitle = isHr
    ? 'Org-wide — a transparent, hand-weighted scorecard, not a trained model (see MODULE2_REFERENCE.md)'
    : 'Scoped to your business unit by the server, not this screen';

  return (
    <div>
      <div className={styles.header}>
        <div>
          <h1 className={`${styles.title} text-headline-md`}>Workforce Health</h1>
          <p className={`${styles.subtitle} text-body-md`}>{subtitle}</p>
        </div>
      </div>

      {loadState === 'error' && (
        <div className={styles.errorBox}>
          <span className="text-body-md">{errorMessage}</span>
          <Button variant="secondary" onClick={retry}>
            Retry
          </Button>
        </div>
      )}

      {loadState === 'loading' && !data && <div className={styles.stateBox}>Loading workforce health…</div>}

      {data && (
        <>
          <div className={styles.kpiRow}>
            <KpiCard label="Employees scored" value={String(data.employee_count)} />
            <KpiCard label="Average score" value={data.average_score.toFixed(1)} />
          </div>

          <div className={styles.insightWrapper}>
            <InsightCallout>{buildInsightSentence(data)}</InsightCallout>
          </div>

          <Card className={styles.section}>
            <h2 className={`${styles.sectionTitle} text-headline-sm`}>Risk Band Distribution</h2>
            <RiskBandDistribution counts={data.band_counts} />
          </Card>

          {data.business_units.length > 0 && (
            <Card className={styles.section}>
              <h2 className={`${styles.sectionTitle} text-headline-sm`}>
                {isHr ? 'Business Units' : 'Your Business Unit'}
              </h2>
              <BusinessUnitBreakdown businessUnits={data.business_units} />
            </Card>
          )}

          <Card className={styles.section}>
            <h2 className={`${styles.sectionTitle} text-headline-sm`}>Highest-Risk Employees</h2>
            <HotspotList hotspots={data.hotspots} />
          </Card>
        </>
      )}
    </div>
  );
}

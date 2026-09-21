import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { KpiCard } from '../../components/ui/KpiCard';
import { RiskBandDistribution } from '../../components/ui/RiskBandDistribution';
import { DemoDatasetBanner } from './DemoDatasetBanner';
import { RiskBusinessUnitBreakdown } from './RiskBusinessUnitBreakdown';
import { RiskHotspotList } from './RiskHotspotList';
import { useRiskAnalysisSummary } from './useRiskAnalysisSummary';
import styles from './RiskAnalysisPage.module.css';

/** Module 3 overview — same shape as WorkforceHealthPage.tsx
 * deliberately: HR and BU Head render the exact same component tree,
 * with GET /risk-analysis/summary's RLS-scoped response being the only
 * thing that differs between them. See MODULE3_REFERENCE.md.
 */
export function RiskAnalysisPage() {
  const { user } = useAuth();
  const { data, loadState, errorMessage, retry } = useRiskAnalysisSummary();
  const isHr = user?.role === 'hr';

  return (
    <div>
      <div className={styles.header}>
        <div>
          <h1 className={`${styles.title} text-headline-md`}>Risk Analysis</h1>
          <p className={`${styles.subtitle} text-body-md`}>
            {isHr ? 'Org-wide' : 'Scoped to your business unit by the server, not this screen'} — a trained
            model with SHAP explainability, demonstrated on synthetic data
          </p>
        </div>
      </div>

      <DemoDatasetBanner />

      {loadState === 'error' && (
        <div className={styles.errorBox}>
          <span className="text-body-md">{errorMessage}</span>
          <Button variant="secondary" onClick={retry}>
            Retry
          </Button>
        </div>
      )}

      {loadState === 'loading' && !data && <div className={styles.stateBox}>Loading risk analysis…</div>}

      {data && (
        <>
          <div className={styles.kpiRow}>
            <KpiCard label="Employees scored" value={String(data.employee_count)} />
            <KpiCard label="Average predicted risk" value={`${(data.average_probability * 100).toFixed(1)}%`} />
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
              <RiskBusinessUnitBreakdown businessUnits={data.business_units} />
            </Card>
          )}

          <Card className={styles.section}>
            <h2 className={`${styles.sectionTitle} text-headline-sm`}>Highest Predicted Risk</h2>
            <RiskHotspotList hotspots={data.hotspots} />
          </Card>
        </>
      )}
    </div>
  );
}

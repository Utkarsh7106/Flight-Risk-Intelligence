import { Link, useParams } from 'react-router-dom';
import { Avatar } from '../../components/ui/Avatar';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { DemoDatasetBanner } from './DemoDatasetBanner';
import { RiskDriverBreakdown } from './RiskDriverBreakdown';
import { useRiskEmployeeDetail } from './useRiskEmployeeDetail';
import styles from './RiskEmployeeDrilldownPage.module.css';

/** Predicted risk + real SHAP driver breakdown for one synthetic
 * employee — Module 3's counterpart to
 * workforce-health/EmployeeScoreDrilldownPage.tsx. RLS decides whether
 * the id resolves at all, same honest-404 ambiguity as every other
 * per-employee lookup in this app; a 'separated' (training-only) row
 * 404s here too, for every role — see MODULE3_REFERENCE.md.
 */
export function RiskEmployeeDrilldownPage() {
  const { id } = useParams<{ id: string }>();
  const employeeId = Number(id);
  const { data, loadState, errorMessage, notFound, retry } = useRiskEmployeeDetail(employeeId);

  return (
    <div>
      <Link to="/risk-analysis" className={styles.backLink}>
        ← Back to Risk Analysis
      </Link>

      <DemoDatasetBanner />

      {notFound && (
        <div className={styles.stateBox}>
          <p className="text-body-md">Employee not found.</p>
        </div>
      )}

      {loadState === 'error' && !notFound && (
        <div className={styles.errorBox}>
          <span className="text-body-md">{errorMessage}</span>
          <Button variant="secondary" onClick={retry}>
            Retry
          </Button>
        </div>
      )}

      {loadState === 'loading' && !data && <div className={styles.stateBox}>Loading prediction…</div>}

      {data && (
        <>
          <Card className={styles.headerCard}>
            <div className={styles.identity}>
              <Avatar fullName={data.full_name} size="lg" />
              <div>
                <h1 className={`${styles.name} text-headline-md`}>{data.full_name}</h1>
                <p className={`${styles.meta} text-body-md`}>
                  {data.designation ?? '—'} · {data.grade} · {data.business_unit.name} / {data.department.name}
                </p>
              </div>
            </div>
            <div className={styles.scoreBlock}>
              <span className={`${styles.scoreValue} text-display-lg`}>
                {(data.predicted_probability * 100).toFixed(0)}%
              </span>
              <Badge tone={data.risk_band}>{data.risk_band}</Badge>
            </div>
          </Card>

          <Card className={styles.section}>
            <h2 className={`${styles.sectionTitle} text-headline-sm`}>What's driving this prediction</h2>
            <RiskDriverBreakdown drivers={data.drivers} />
          </Card>
        </>
      )}
    </div>
  );
}

import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { KpiCard } from '../../components/ui/KpiCard';
import { useFairnessAudit } from './useFairnessAudit';
import { AttributeAuditTable } from './AttributeAuditTable';
import { ManagerAuditTable } from './ManagerAuditTable';
import styles from './FairnessAuditPage.module.css';

/** HR-only. The role check below is a UI courtesy that skips the request
 * and shows a clean message — it is NOT the security boundary. The real
 * enforcement is backend/app/security/deps.py's require_hr on
 * GET /workforce-health/fairness-audit, which 403s any non-HR session
 * regardless of what this component does or whether the Sidebar link is
 * hidden. See MODULE2_REFERENCE.md: "treat any accidental exposure to a
 * non-HR role as a serious defect."
 */
export function FairnessAuditPage() {
  const { user } = useAuth();
  const isHr = user?.role === 'hr';
  const { data, loadState, errorMessage, retry } = useFairnessAudit(isHr);

  if (!isHr) {
    return (
      <div className={styles.stateBox}>
        <p className="text-body-md">The fairness audit is available to HR accounts only.</p>
      </div>
    );
  }

  return (
    <div>
      <div className={styles.header}>
        <div>
          <h1 className={`${styles.title} text-headline-md`}>Fairness Audit</h1>
          <p className={`${styles.subtitle} text-body-md`}>
            Checks whether legitimate scoring inputs correlate with protected attributes in this workforce —
            a flagged gap is worth investigating, never proof of a problem. See MODULE2_REFERENCE.md.
          </p>
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

      {loadState === 'loading' && !data && <div className={styles.stateBox}>Loading fairness audit…</div>}

      {data && (
        <>
          <div className={styles.kpiRow}>
            <KpiCard label="Employees audited" value={String(data.overall_n)} />
            <KpiCard label="Overall average score" value={data.overall_mean_score.toFixed(1)} />
          </div>

          {data.attribute_audits.map((audit) => (
            <Card key={audit.attribute} className={styles.section}>
              <AttributeAuditTable audit={audit} />
            </Card>
          ))}

          <Card className={styles.section}>
            <h2 className={`${styles.sectionTitle} text-headline-sm`}>Manager Team-Risk Signals</h2>
            <p className={`${styles.sectionSubtitle} text-body-md`}>
              A different check from the groups above: an elevated team average points at where to invest
              manager support, not a protected-attribute concern to mask.
            </p>
            <ManagerAuditTable managers={data.manager_audits} />
          </Card>
        </>
      )}
    </div>
  );
}

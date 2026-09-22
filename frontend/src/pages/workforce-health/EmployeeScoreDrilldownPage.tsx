import { Link, useParams, useSearchParams } from 'react-router-dom';
import { Avatar } from '../../components/ui/Avatar';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { useEmployeeScore } from './useEmployeeScore';
import { DriverBreakdown } from './DriverBreakdown';
import type { EmploymentStatusFilter } from '../../api/types';
import styles from './EmployeeScoreDrilldownPage.module.css';

/** Score + driver breakdown + recommendations for one employee — the
 * single most important individual screen in Module 2 per
 * MODULE2_REFERENCE.md. Reachable from the Workforce Health hotspot list
 * and from the Employee Directory (both link here by id); RLS decides
 * whether the id resolves at all, same as GET /employees/{id} already
 * does — a 404 here means either the id doesn't exist or this login
 * can't see it, indistinguishably, which is the same honest ambiguity
 * the directory's employee lookup already has.
 *
 * ?employment_status carries the same opt-in DirectoryFilters.tsx already
 * exposes (Module 4): the directory only links here with it set when the
 * row it's linking from is already shown under an explicit "Separated"/
 * "All statuses" filter, so a separated employee's score stays reachable
 * from the app, not just from a raw API call. No new control lives on
 * this page itself — it only forwards what the link already said.
 */
export function EmployeeScoreDrilldownPage() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const employeeId = Number(id);
  const employmentStatus = (searchParams.get('employment_status') as EmploymentStatusFilter | null) ?? undefined;
  const { data, loadState, errorMessage, notFound, retry } = useEmployeeScore(employeeId, employmentStatus);

  return (
    <div>
      <Link to="/workforce-health" className={styles.backLink}>
        ← Back to Workforce Health
      </Link>

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

      {loadState === 'loading' && !data && <div className={styles.stateBox}>Loading score…</div>}

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
              <span className={`${styles.scoreValue} text-display-lg`}>{data.score.toFixed(1)}</span>
              <Badge tone={data.band}>{data.band_label}</Badge>
            </div>
          </Card>

          {data.data_completeness < 1 && (
            <p className={`${styles.completenessNote} text-label-md`}>
              Based on {Math.round(data.data_completeness * 100)}% of the full signal set — one or more inputs
              (e.g. engagement or manager effectiveness score) weren't on file for this employee, so the score
              reflects only what's available rather than assuming the worst or the best.
            </p>
          )}

          <Card className={styles.section}>
            <h2 className={`${styles.sectionTitle} text-headline-sm`}>What's driving this score</h2>
            <DriverBreakdown drivers={data.drivers} />
          </Card>

          <Card className={styles.section}>
            <h2 className={`${styles.sectionTitle} text-headline-sm`}>Recommended actions</h2>
            <div className={styles.recommendations}>
              {data.recommendations.map((rec) => (
                <div key={rec.key} className={styles.recommendation}>
                  <h3 className="text-body-lg">{rec.title}</h3>
                  <p className={`${styles.rationale} text-body-md`}>{rec.rationale}</p>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

import { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/ui/Button';
import { DirectoryFilters } from './DirectoryFilters';
import { DirectoryTable } from './DirectoryTable';
import { DirectoryCards } from './DirectoryCards';
import { ViewToggle } from './ViewToggle';
import type { DirectoryView } from './ViewToggle';
import { useEmployeeDirectory } from './useEmployeeDirectory';
import { useBusinessUnitFilterOptions } from './useBusinessUnitFilterOptions';
import styles from './DirectoryPage.module.css';

/** Zero frontend-side role/BU filtering logic lives on this page or
 * anything it renders — see useEmployeeDirectory.ts's header comment.
 * What HR vs. a BU Head sees is entirely a function of what
 * GET /employees returns for their session; this component only chooses
 * how to display that response.
 */
export function DirectoryPage() {
  const { user } = useAuth();
  const [view, setView] = useState<DirectoryView>('table');

  const {
    filters,
    setFilters,
    sortBy,
    sortDir,
    toggleSort,
    data,
    loadState,
    errorMessage,
    nextPage,
    previousPage,
    retry,
  } = useEmployeeDirectory();

  const isHr = user?.role === 'hr';
  const businessUnitOptions = useBusinessUnitFilterOptions(isHr);

  const subtitle = isHr
    ? 'Org-wide — every business unit'
    : 'Scoped to your business unit by the server, not this screen';

  return (
    <div>
      <div className={styles.header}>
        <div>
          <h1 className={`${styles.title} text-headline-md`}>Employee Directory</h1>
          <p className={`${styles.subtitle} text-body-md`}>{subtitle}</p>
        </div>
        <ViewToggle value={view} onChange={setView} />
      </div>

      <DirectoryFilters
        filters={filters}
        onFiltersChange={setFilters}
        sortBy={sortBy}
        sortDir={sortDir}
        onToggleSort={toggleSort}
        businessUnitOptions={businessUnitOptions}
        showBusinessUnitFilter={isHr}
      />

      {loadState === 'error' && (
        <div className={styles.errorBox}>
          <span className="text-body-md">{errorMessage}</span>
          <Button variant="secondary" onClick={retry}>
            Retry
          </Button>
        </div>
      )}

      {loadState === 'loading' && !data && <div className={styles.stateBox}>Loading employees…</div>}

      {data && (
        <>
          {loadState === 'loading' && <p className={styles.updatingHint}>Updating…</p>}

          {data.items.length === 0 ? (
            <div className={styles.stateBox}>No employees match these filters.</div>
          ) : view === 'table' ? (
            <DirectoryTable employees={data.items} sortBy={sortBy} sortDir={sortDir} onToggleSort={toggleSort} />
          ) : (
            <DirectoryCards employees={data.items} />
          )}

          {data.total > 0 && (
            <div className={styles.pagination}>
              <span className={`${styles.pageInfo} text-body-md`}>
                Showing {data.offset + 1}–{Math.min(data.offset + data.items.length, data.total)} of {data.total}
              </span>
              <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
                <Button variant="secondary" onClick={previousPage} disabled={data.offset === 0}>
                  Previous
                </Button>
                <Button
                  variant="secondary"
                  onClick={nextPage}
                  disabled={data.offset + data.items.length >= data.total}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

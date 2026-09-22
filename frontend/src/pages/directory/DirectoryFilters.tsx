import { Field, Select, TextInput } from '../../components/ui/FormControls';
import { SORTABLE_FIELDS } from '../../api/types';
import type { BusinessUnitRef, EmploymentStatusFilter, Grade, SortBy } from '../../api/types';
import type { DirectoryFilters as Filters } from './useEmployeeDirectory';
import styles from './DirectoryFilters.module.css';

const GRADES: Grade[] = ['L1', 'L2', 'L3', 'L4', 'L5', 'L6'];
const STATUS_OPTIONS: { value: EmploymentStatusFilter; label: string }[] = [
  { value: 'active', label: 'Active' },
  { value: 'separated', label: 'Separated' },
  { value: 'all', label: 'All statuses' },
];

const SORT_LABELS: Record<SortBy, string> = {
  full_name: 'Name',
  employee_code: 'Employee code',
  date_of_joining: 'Date of joining',
  grade: 'Grade',
  designation: 'Designation',
  location: 'Location',
  ctc_annual: 'CTC',
  performance_rating: 'Performance rating',
};

interface DirectoryFiltersProps {
  filters: Filters;
  onFiltersChange: (next: Partial<Filters>) => void;
  sortBy: SortBy;
  sortDir: 'asc' | 'desc';
  onToggleSort: (field: SortBy) => void;
  businessUnitOptions: BusinessUnitRef[];
  showBusinessUnitFilter: boolean;
}

/** Every control here maps to a real, backend-supported query param —
 * SORT_LABELS is keyed off SORTABLE_FIELDS (api/types.ts), which is
 * copied verbatim from the router's SORT_COLUMNS allow-list, not guessed.
 * The business-unit filter only renders for HR (see showBusinessUnitFilter);
 * a bu_head is already scoped to one BU by RLS, so offering it to them
 * would be redundant chrome, not a feature.
 */
export function DirectoryFilters({
  filters,
  onFiltersChange,
  sortBy,
  sortDir,
  onToggleSort,
  businessUnitOptions,
  showBusinessUnitFilter,
}: DirectoryFiltersProps) {
  return (
    <div className={styles.bar}>
      <div className={styles.searchField}>
        <Field label="Search" htmlFor="directory-search">
          <TextInput
            id="directory-search"
            type="search"
            placeholder="Name, employee code, or designation"
            value={filters.q}
            onChange={(e) => onFiltersChange({ q: e.target.value })}
          />
        </Field>
      </div>

      <div className={styles.filterField}>
        <Field label="Grade" htmlFor="directory-grade">
          <Select
            id="directory-grade"
            value={filters.grade}
            onChange={(e) => onFiltersChange({ grade: e.target.value as Grade | '' })}
          >
            <option value="">All grades</option>
            {GRADES.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </Select>
        </Field>
      </div>

      <div className={styles.filterField}>
        <Field label="Status" htmlFor="directory-status">
          <Select
            id="directory-status"
            value={filters.employment_status}
            onChange={(e) => onFiltersChange({ employment_status: e.target.value as EmploymentStatusFilter })}
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </Select>
        </Field>
      </div>

      {showBusinessUnitFilter && (
        <div className={styles.filterField}>
          <Field label="Business unit" htmlFor="directory-bu">
            <Select
              id="directory-bu"
              value={filters.business_unit_id}
              onChange={(e) =>
                onFiltersChange({ business_unit_id: e.target.value === '' ? '' : Number(e.target.value) })
              }
            >
              <option value="">All business units</option>
              {businessUnitOptions.map((bu) => (
                <option key={bu.id} value={bu.id}>
                  {bu.name}
                </option>
              ))}
            </Select>
          </Field>
        </div>
      )}

      <div className={styles.sortRow}>
        <div className={styles.filterField}>
          <Field label="Sort by" htmlFor="directory-sort">
            <Select id="directory-sort" value={sortBy} onChange={(e) => onToggleSort(e.target.value as SortBy)}>
              {SORTABLE_FIELDS.map((field) => (
                <option key={field} value={field}>
                  {SORT_LABELS[field]}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <button
          type="button"
          className={styles.sortDirButton}
          onClick={() => onToggleSort(sortBy)}
          aria-label={sortDir === 'asc' ? 'Sort descending' : 'Sort ascending'}
          title={sortDir === 'asc' ? 'Ascending' : 'Descending'}
        >
          {sortDir === 'asc' ? '▲' : '▼'}
        </button>
      </div>
    </div>
  );
}

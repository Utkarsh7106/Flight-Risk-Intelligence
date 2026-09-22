import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { getEmployee, listEmployees } from '../../api/employees';
import { recordDeparture } from '../../api/departureEvents';
import { ApiError, NetworkError } from '../../api/client';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Field, Select, TextInput } from '../../components/ui/FormControls';
import { REASON_CATEGORIES } from '../../api/types';
import type { DepartureType, Employee } from '../../api/types';
import styles from './RecordDeparturePage.module.css';

const TYPE_OPTIONS: { value: DepartureType; label: string }[] = [
  { value: 'voluntary', label: 'Voluntary' },
  { value: 'involuntary', label: 'Involuntary' },
  { value: 'retirement', label: 'Retirement' },
  { value: 'other', label: 'Other' },
];

const SEARCH_DEBOUNCE_MS = 300;

/** Module 4, Part A's write side. Reachable two ways: with ?employee_id=
 * pre-filled (a "Record departure" link on an active Directory row —
 * see DirectoryTable.tsx/DirectoryCards.tsx), or bare from the
 * Departures page's own "Record departure" button, in which case this
 * page's own search box finds the employee. Either way, the only thing
 * that determines whether the POST succeeds is the backend's RLS scope
 * (see backend/app/routers/departure_events.py) — this page does not
 * pre-filter the search by BU/role itself, the same "no client-side
 * scoping" invariant as useEmployeeDirectory.ts.
 */
export function RecordDeparturePage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const prefilledId = searchParams.get('employee_id');

  const [selected, setSelected] = useState<Employee | null>(null);
  const [loadingPrefill, setLoadingPrefill] = useState(prefilledId !== null);
  const [prefillError, setPrefillError] = useState<string | null>(null);

  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [results, setResults] = useState<Employee[]>([]);
  const [searching, setSearching] = useState(false);

  const [departureDate, setDepartureDate] = useState('');
  const [lastWorkingDay, setLastWorkingDay] = useState('');
  const [departureType, setDepartureType] = useState<DepartureType>('voluntary');
  const [reasonCategory, setReasonCategory] = useState('');
  const [reasonNotes, setReasonNotes] = useState('');
  const [isRegretted, setIsRegretted] = useState<'' | 'yes' | 'no'>('');
  const [noticePeriodDays, setNoticePeriodDays] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (prefilledId === null) return;
    let cancelled = false;
    getEmployee(Number(prefilledId))
      .then((employee) => {
        if (cancelled) return;
        setSelected(employee);
        setLoadingPrefill(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setPrefillError(err instanceof ApiError ? (err.detail ?? 'Employee not found.') : 'Unable to reach the server.');
        setLoadingPrefill(false);
      });
    return () => {
      cancelled = true;
    };
  }, [prefilledId]);

  useEffect(() => {
    const handle = setTimeout(() => setDebouncedQuery(query), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(handle);
  }, [query]);

  useEffect(() => {
    if (selected || debouncedQuery.trim().length < 2) {
      setResults([]);
      return;
    }
    let cancelled = false;
    setSearching(true);
    listEmployees({ q: debouncedQuery, employment_status: 'active', limit: 8 })
      .then((response) => {
        if (cancelled) return;
        setResults(response.items);
      })
      .catch(() => {
        if (cancelled) return;
        setResults([]);
      })
      .finally(() => {
        if (!cancelled) setSearching(false);
      });
    return () => {
      cancelled = true;
    };
  }, [debouncedQuery, selected]);

  function handleDepartureTypeChange(next: DepartureType) {
    setDepartureType(next);
    setReasonCategory(''); // categories are per-type; a stale value from the previous type is never valid
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selected) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await recordDeparture({
        employee_id: selected.id,
        departure_date: departureDate,
        last_working_day: lastWorkingDay || null,
        departure_type: departureType,
        reason_category: reasonCategory || null,
        reason_notes: reasonNotes || null,
        is_regretted: isRegretted === '' ? null : isRegretted === 'yes',
        notice_period_days: noticePeriodDays === '' ? null : Number(noticePeriodDays),
      });
      navigate('/departures');
    } catch (err) {
      if (err instanceof ApiError) {
        setSubmitError(err.detail ?? `Request failed (${err.status}).`);
      } else if (err instanceof NetworkError) {
        setSubmitError('Unable to reach the server.');
      } else {
        setSubmitError('Something went wrong recording this departure.');
      }
      setSubmitting(false);
    }
  }

  return (
    <div>
      <Link to="/departures" className={styles.backLink}>
        ← Back to Departures
      </Link>

      <h1 className={`${styles.title} text-headline-md`}>Record a departure</h1>
      <p className={`${styles.subtitle} text-body-md`}>
        Marks the employee as separated and removes them from the default Directory, Workforce Health, and Risk
        Analysis views — they remain reachable via the Directory's "Separated" filter.
      </p>

      <Card className={styles.card}>
        {loadingPrefill && <p className="text-body-md">Loading employee…</p>}
        {prefillError && <p className={styles.errorText}>{prefillError}</p>}

        {!loadingPrefill && !selected && (
          <Field label="Employee" htmlFor="departure-employee-search">
            <TextInput
              id="departure-employee-search"
              type="search"
              placeholder="Search by name or employee code"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              autoComplete="off"
            />
            {searching && <p className={`${styles.hint} text-label-md`}>Searching…</p>}
            {results.length > 0 && (
              <ul className={styles.resultList}>
                {results.map((employee) => (
                  <li key={employee.id}>
                    <button
                      type="button"
                      className={styles.resultButton}
                      onClick={() => {
                        setSelected(employee);
                        setResults([]);
                        setQuery('');
                      }}
                    >
                      <span className="text-body-md">{employee.full_name}</span>
                      <span className={`${styles.hint} text-label-md`}>
                        {employee.employee_code} · {employee.business_unit.name} / {employee.department.name}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Field>
        )}

        {selected && (
          <>
            <div className={styles.selectedEmployee}>
              <div>
                <span className={`${styles.selectedName} text-body-lg`}>{selected.full_name}</span>
                <span className={`${styles.hint} text-label-md`}>
                  {selected.employee_code} · {selected.business_unit.name} / {selected.department.name}
                </span>
              </div>
              {prefilledId === null && (
                <button type="button" className={styles.changeLink} onClick={() => setSelected(null)}>
                  Change
                </button>
              )}
            </div>

            <form onSubmit={(e) => void handleSubmit(e)} className={styles.form}>
              <div className={styles.formRow}>
                <Field label="Departure date" htmlFor="departure-date">
                  <TextInput
                    id="departure-date"
                    type="date"
                    required
                    value={departureDate}
                    onChange={(e) => setDepartureDate(e.target.value)}
                  />
                </Field>
                <Field label="Last working day (optional)" htmlFor="last-working-day">
                  <TextInput
                    id="last-working-day"
                    type="date"
                    value={lastWorkingDay}
                    onChange={(e) => setLastWorkingDay(e.target.value)}
                  />
                </Field>
              </div>

              <div className={styles.formRow}>
                <Field label="Departure type" htmlFor="departure-type">
                  <Select
                    id="departure-type"
                    value={departureType}
                    onChange={(e) => handleDepartureTypeChange(e.target.value as DepartureType)}
                  >
                    {TYPE_OPTIONS.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Reason (optional)" htmlFor="reason-category">
                  <Select
                    id="reason-category"
                    value={reasonCategory}
                    onChange={(e) => setReasonCategory(e.target.value)}
                  >
                    <option value="">Unspecified</option>
                    {REASON_CATEGORIES[departureType].map((r) => (
                      <option key={r.value} value={r.value}>
                        {r.label}
                      </option>
                    ))}
                  </Select>
                </Field>
              </div>

              <div className={styles.formRow}>
                <Field label="Regretted? (optional)" htmlFor="is-regretted">
                  <Select
                    id="is-regretted"
                    value={isRegretted}
                    onChange={(e) => setIsRegretted(e.target.value as '' | 'yes' | 'no')}
                  >
                    <option value="">Unknown</option>
                    <option value="yes">Yes</option>
                    <option value="no">No</option>
                  </Select>
                </Field>
                <Field label="Notice period, in days (optional)" htmlFor="notice-period">
                  <TextInput
                    id="notice-period"
                    type="number"
                    min={0}
                    value={noticePeriodDays}
                    onChange={(e) => setNoticePeriodDays(e.target.value)}
                  />
                </Field>
              </div>

              <Field label="Notes (optional)" htmlFor="reason-notes">
                <textarea
                  id="reason-notes"
                  className={styles.textarea}
                  value={reasonNotes}
                  onChange={(e) => setReasonNotes(e.target.value)}
                  maxLength={2000}
                  rows={3}
                />
              </Field>

              {submitError && <p className={styles.errorText}>{submitError}</p>}

              <div className={styles.actions}>
                <Button type="submit" variant="primary" disabled={submitting || !departureDate}>
                  {submitting ? 'Recording…' : 'Record departure'}
                </Button>
                <Link to="/departures">
                  <Button type="button" variant="secondary">
                    Cancel
                  </Button>
                </Link>
              </div>
            </form>
          </>
        )}
      </Card>
    </div>
  );
}

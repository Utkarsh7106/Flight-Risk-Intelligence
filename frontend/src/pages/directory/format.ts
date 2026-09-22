const currencyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

const dateFormatter = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });

export function formatCtc(value: number | null): string {
  return value === null ? '—' : currencyFormatter.format(value);
}

export function formatDate(iso: string | null): string {
  if (iso === null) return '—';
  return dateFormatter.format(new Date(iso));
}

export function formatTenure(years: number): string {
  return `${years.toFixed(1)} yrs`;
}

export function formatScore(value: number | null): string {
  return value === null ? '—' : value.toFixed(1);
}

/** A directory row only shows a separated employee at all once the status
 * filter has already been set to "separated"/"all" (DirectoryFilters.tsx) —
 * that's the explicit ask. This carries it through to the score page so
 * GET /workforce-health/employees/{id}'s employment_status opt-in (Module 4)
 * doesn't 404 a link the directory itself just offered.
 */
export function scoreLink(employeeId: number, employmentStatus: 'active' | 'separated'): string {
  return employmentStatus === 'active'
    ? `/workforce-health/employees/${employeeId}`
    : `/workforce-health/employees/${employeeId}?employment_status=all`;
}

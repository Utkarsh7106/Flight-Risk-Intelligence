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

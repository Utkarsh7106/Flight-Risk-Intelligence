import { useEffect, useState } from 'react';
import { listEmployees } from '../../api/employees';
import type { BusinessUnitRef } from '../../api/types';

/** There's no dedicated /business-units endpoint, so the HR-only "filter
 * by business unit" dropdown derives its options from a one-time
 * unfiltered fetch of the directory (limit=200, the backend's own max —
 * comfortably above the current ~18-row seed). This is a real workaround,
 * not a shortcut to hide: it works correctly at today's data size, but
 * would silently miss BUs past 200 employees if the panel grows. Worth
 * a real /business-units endpoint if that ever happens — noted in the
 * frontend README, not fixed here.
 *
 * Never called for a bu_head — they only ever have one BU, RLS already
 * scopes them to it, and a filter dropdown with one fixed option would
 * be noise, not a feature.
 */
export function useBusinessUnitFilterOptions(enabled: boolean) {
  const [options, setOptions] = useState<BusinessUnitRef[]>([]);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;

    listEmployees({ limit: 200 })
      .then((page) => {
        if (cancelled) return;
        const seen = new Map<number, BusinessUnitRef>();
        for (const employee of page.items) {
          seen.set(employee.business_unit.id, employee.business_unit);
        }
        setOptions([...seen.values()].sort((a, b) => a.name.localeCompare(b.name)));
      })
      .catch(() => {
        // Non-critical — the filter dropdown just won't have options.
        // The rest of the directory page still works.
      });

    return () => {
      cancelled = true;
    };
  }, [enabled]);

  return options;
}

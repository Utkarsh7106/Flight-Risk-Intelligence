import { useState } from 'react';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Field, Select } from '../../components/ui/FormControls';
import { downloadWorkforceHealthExport, triggerBrowserDownload } from '../../api/exports';
import type { ExportFormat } from '../../api/exports';
import { ApiError, NetworkError } from '../../api/client';
import { useBusinessUnitFilterOptions } from '../directory/useBusinessUnitFilterOptions';
import styles from './ExportControls.module.css';

interface ExportControlsProps {
  isHr: boolean;
}

/** Module 4, Part B's entry point in the live app. For HR, an optional
 * business-unit picker narrows the export to exactly what that BU's own
 * BU Head would see live (see app/routers/exports.py's docstring) — ""
 * means org-wide. A BU Head gets no picker at all: their export is
 * always their own BU, which the backend forces server-side regardless
 * of what this UI would even send, so there's nothing to offer them here
 * beyond the two format buttons.
 */
export function ExportControls({ isHr }: ExportControlsProps) {
  const businessUnitOptions = useBusinessUnitFilterOptions(isHr);
  const [businessUnitId, setBusinessUnitId] = useState<number | ''>('');
  const [pending, setPending] = useState<ExportFormat | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleDownload(format: ExportFormat) {
    setPending(format);
    setError(null);
    try {
      const { blob, filename } = await downloadWorkforceHealthExport(
        format,
        isHr && businessUnitId !== '' ? businessUnitId : undefined,
      );
      triggerBrowserDownload(blob, filename);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail ?? `Export failed (${err.status}).`);
      } else if (err instanceof NetworkError) {
        setError('Unable to reach the server.');
      } else {
        setError('Something went wrong generating the export.');
      }
    } finally {
      setPending(null);
    }
  }

  return (
    <Card className={styles.card}>
      <h2 className={`${styles.title} text-headline-sm`}>Export report</h2>
      <p className={`${styles.subtitle} text-body-md`}>
        {isHr
          ? 'A self-contained report — HTML to open and share, or PDF to print or attach.'
          : "A self-contained report of your business unit's Workforce Health — HTML to open and share, or PDF to print or attach."}
      </p>

      <div className={styles.controls}>
        {isHr && (
          <Field label="Scope" htmlFor="export-scope">
            <Select
              id="export-scope"
              value={businessUnitId}
              onChange={(e) => setBusinessUnitId(e.target.value === '' ? '' : Number(e.target.value))}
            >
              <option value="">Org-wide</option>
              {businessUnitOptions.map((bu) => (
                <option key={bu.id} value={bu.id}>
                  {bu.name}
                </option>
              ))}
            </Select>
          </Field>
        )}

        <div className={styles.buttonRow}>
          <Button variant="secondary" disabled={pending !== null} onClick={() => void handleDownload('html')}>
            {pending === 'html' ? 'Generating…' : 'Download HTML'}
          </Button>
          <Button variant="primary" disabled={pending !== null} onClick={() => void handleDownload('pdf')}>
            {pending === 'pdf' ? 'Generating…' : 'Download PDF'}
          </Button>
        </div>
      </div>

      {error && <p className={styles.errorText}>{error}</p>}
    </Card>
  );
}

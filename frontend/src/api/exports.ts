import { API_BASE_URL, ApiError, NetworkError } from './client';

export type ExportFormat = 'html' | 'pdf';

interface ExportDownload {
  blob: Blob;
  filename: string;
}

/** Not built on apiRequest() (api/client.ts) because that helper always
 * parses the response as JSON — this endpoint returns raw HTML/PDF bytes
 * with a Content-Disposition header, so this fetches the same way
 * (credentials: 'include', same ApiError/NetworkError shape for the
 * caller to handle identically) but reads a Blob instead.
 */
export async function downloadWorkforceHealthExport(
  format: ExportFormat,
  businessUnitId?: number,
): Promise<ExportDownload> {
  const url = new URL('/exports/workforce-health', API_BASE_URL);
  url.searchParams.set('format', format);
  if (businessUnitId !== undefined) url.searchParams.set('business_unit_id', String(businessUnitId));

  let response: Response;
  try {
    response = await fetch(url.toString(), { credentials: 'include' });
  } catch {
    throw new NetworkError();
  }

  if (!response.ok) {
    let detail: string | null = null;
    try {
      const body = (await response.json()) as { detail?: string };
      detail = body.detail ?? null;
    } catch {
      // Non-JSON error body — no detail to surface.
    }
    throw new ApiError(response.status, detail);
  }

  const blob = await response.blob();
  const disposition = response.headers.get('Content-Disposition') ?? '';
  const match = /filename="([^"]+)"/.exec(disposition);
  const filename = match?.[1] ?? `workforce-health-export.${format}`;
  return { blob, filename };
}

/** Browser-native "save this blob as a file" — no library, this is a
 * handful of DOM APIs every modern browser supports.
 */
export function triggerBrowserDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

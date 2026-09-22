import { apiRequest } from './client';
import type { DepartureEvent, DepartureEventCreate, DepartureEventListResponse, DepartureQuery } from './types';

/** Same discipline as api/employees.ts: no role/BU filtering here — the
 * query params below are everything sent, and the backend's Row-Level
 * Security is what actually scopes the result set. */
export function listDepartures(query: DepartureQuery = {}): Promise<DepartureEventListResponse> {
  return apiRequest<DepartureEventListResponse>('/departure-events', {
    query: {
      business_unit_id: query.business_unit_id,
      department_id: query.department_id,
      departure_type: query.departure_type,
      sort_by: query.sort_by,
      sort_dir: query.sort_dir,
      limit: query.limit,
      offset: query.offset,
    },
  });
}

export function recordDeparture(payload: DepartureEventCreate): Promise<DepartureEvent> {
  return apiRequest<DepartureEvent>('/departure-events', { method: 'POST', body: payload });
}

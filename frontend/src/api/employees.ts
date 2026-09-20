import { apiRequest } from './client';
import type { Employee, EmployeeListResponse, EmployeeQuery } from './types';

/** No role/BU filtering logic lives here or anywhere in the frontend —
 * the query params below are literally everything sent; the backend's
 * Row-Level Security is what actually scopes the result set. This
 * function has no idea what BU the caller is in and must never be given
 * one to filter by client-side.
 */
export function listEmployees(query: EmployeeQuery = {}): Promise<EmployeeListResponse> {
  return apiRequest<EmployeeListResponse>('/employees', {
    query: {
      business_unit_id: query.business_unit_id,
      department_id: query.department_id,
      grade: query.grade,
      employment_status: query.employment_status,
      location: query.location,
      q: query.q,
      sort_by: query.sort_by,
      sort_dir: query.sort_dir,
      limit: query.limit,
      offset: query.offset,
    },
  });
}

export function getEmployee(id: number): Promise<Employee> {
  return apiRequest<Employee>(`/employees/${id}`);
}

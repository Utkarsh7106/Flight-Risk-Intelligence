import { Link } from 'react-router-dom';
import { Avatar } from '../../components/ui/Avatar';
import { Badge } from '../../components/ui/Badge';
import { Table, SortableHeader } from '../../components/ui/Table';
import type { Employee, SortBy, SortDir } from '../../api/types';
import { formatCtc, formatScore, formatTenure, scoreLink } from './format';
import styles from './DirectoryTable.module.css';

interface DirectoryTableProps {
  employees: Employee[];
  sortBy: SortBy;
  sortDir: SortDir;
  onToggleSort: (field: SortBy) => void;
}

/** Renders exactly the fields EmployeeOut sends — no gender/DOB/phone
 * (the backend never sends them), no client-side row filtering (the
 * `employees` prop is already the server's answer, used as-is).
 */
export function DirectoryTable({ employees, sortBy, sortDir, onToggleSort }: DirectoryTableProps) {
  return (
    <Table>
      <thead>
        <tr>
          <SortableHeader active={sortBy === 'full_name'} direction={sortDir} onToggle={() => onToggleSort('full_name')}>
            Employee
          </SortableHeader>
          <SortableHeader
            active={sortBy === 'employee_code'}
            direction={sortDir}
            onToggle={() => onToggleSort('employee_code')}
          >
            Code
          </SortableHeader>
          <th>Business Unit / Dept</th>
          <SortableHeader active={sortBy === 'grade'} direction={sortDir} onToggle={() => onToggleSort('grade')}>
            Grade
          </SortableHeader>
          <SortableHeader
            active={sortBy === 'location'}
            direction={sortDir}
            onToggle={() => onToggleSort('location')}
          >
            Location
          </SortableHeader>
          <th>Manager</th>
          <SortableHeader
            active={sortBy === 'date_of_joining'}
            direction={sortDir}
            onToggle={() => onToggleSort('date_of_joining')}
          >
            Tenure
          </SortableHeader>
          <SortableHeader
            active={sortBy === 'ctc_annual'}
            direction={sortDir}
            onToggle={() => onToggleSort('ctc_annual')}
          >
            CTC (annual)
          </SortableHeader>
          <SortableHeader
            active={sortBy === 'performance_rating'}
            direction={sortDir}
            onToggle={() => onToggleSort('performance_rating')}
          >
            Performance
          </SortableHeader>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {employees.map((employee) => (
          <tr key={employee.id}>
            <td>
              <div className={styles.nameCell}>
                <Avatar fullName={employee.full_name} size="sm" />
                <div className={styles.nameText}>
                  <Link to={scoreLink(employee.id, employee.employment_status)} className={`${styles.fullName} text-body-md`}>
                    {employee.full_name}
                  </Link>
                  <span className={`${styles.designation} text-label-md`}>{employee.designation ?? '—'}</span>
                </div>
              </div>
            </td>
            <td className="text-mono-data">{employee.employee_code}</td>
            <td>
              <div className={styles.orgCell}>
                <span className={`${styles.buName} text-body-md`}>{employee.business_unit.name}</span>
                <span className={`${styles.deptName} text-label-md`}>{employee.department.name}</span>
              </div>
            </td>
            <td>{employee.grade}</td>
            <td className={employee.location ? '' : styles.muted}>{employee.location ?? '—'}</td>
            <td className={employee.manager ? '' : styles.muted}>{employee.manager?.full_name ?? '—'}</td>
            <td className="text-mono-data">{formatTenure(employee.tenure_years)}</td>
            <td className="text-mono-data">{formatCtc(employee.ctc_annual)}</td>
            <td className="text-mono-data">{formatScore(employee.performance_rating)}</td>
            <td>
              {employee.employment_status === 'active' ? (
                <div className={styles.statusCell}>
                  <Badge tone="low" dot>
                    Active
                  </Badge>
                  <Link to={`/departures/new?employee_id=${employee.id}`} className={styles.recordDepartureLink}>
                    Record departure
                  </Link>
                </div>
              ) : (
                <Badge tone="neutral" dot>
                  Separated
                </Badge>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

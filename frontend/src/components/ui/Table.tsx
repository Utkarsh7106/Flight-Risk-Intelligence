import type { ReactNode } from 'react';
import styles from './Table.module.css';

interface TableProps {
  children: ReactNode;
}

/** DESIGN.md "Data Tables": high-density rows, sticky headers on scroll,
 * subtle zebra striping. A thin wrapper around a real <table> rather than
 * a div-grid, so screen readers and browser table semantics keep working.
 */
export function Table({ children }: TableProps) {
  return (
    <div className={styles.scrollContainer}>
      <table className={styles.table}>{children}</table>
    </div>
  );
}

interface SortableHeaderProps {
  active: boolean;
  direction: 'asc' | 'desc';
  onToggle: () => void;
  children: ReactNode;
}

export function SortableHeader({ active, direction, onToggle, children }: SortableHeaderProps) {
  return (
    <th
      className={styles.sortableHeader}
      onClick={onToggle}
      aria-sort={active ? (direction === 'asc' ? 'ascending' : 'descending') : 'none'}
    >
      {children} {active && (direction === 'asc' ? '▲' : '▼')}
    </th>
  );
}

export { styles as tableStyles };

import type { ReactNode } from 'react';
import { Button } from '../ui/Button';
import styles from './FullPageState.module.css';

interface FullPageStateProps {
  title: string;
  description?: string;
  spinner?: boolean;
  action?: { label: string; onClick: () => void };
  children?: ReactNode;
}

/** Shared full-viewport state for loading / error / empty conditions that
 * take over the whole page (auth check in flight, backend unreachable) —
 * as opposed to inline states scoped to one panel (see the directory
 * page's own loading/empty/error handling, which stays inline).
 */
export function FullPageState({ title, description, spinner, action, children }: FullPageStateProps) {
  return (
    <div className={styles.container}>
      <div className={styles.content}>
        {spinner && <div className={styles.spinner} role="status" aria-label="Loading" />}
        <h2 className={`${styles.title} text-headline-sm`}>{title}</h2>
        {description && <p className={`${styles.description} text-body-md`}>{description}</p>}
        {children}
        {action && <Button onClick={action.onClick}>{action.label}</Button>}
      </div>
    </div>
  );
}

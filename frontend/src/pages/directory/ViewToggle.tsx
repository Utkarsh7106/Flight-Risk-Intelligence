import styles from './ViewToggle.module.css';

export type DirectoryView = 'table' | 'cards';

interface ViewToggleProps {
  value: DirectoryView;
  onChange: (view: DirectoryView) => void;
}

export function ViewToggle({ value, onChange }: ViewToggleProps) {
  return (
    <div className={styles.toggle} role="group" aria-label="Directory view">
      <button
        type="button"
        className={`${styles.option} ${value === 'table' ? styles.optionActive : ''}`}
        onClick={() => onChange('table')}
        aria-pressed={value === 'table'}
      >
        Table
      </button>
      <button
        type="button"
        className={`${styles.option} ${value === 'cards' ? styles.optionActive : ''}`}
        onClick={() => onChange('cards')}
        aria-pressed={value === 'cards'}
      >
        Cards
      </button>
    </div>
  );
}

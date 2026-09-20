import type { InputHTMLAttributes, LabelHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react';
import styles from './FormControls.module.css';

interface FieldProps {
  label: string;
  htmlFor: string;
  children: ReactNode;
  labelProps?: LabelHTMLAttributes<HTMLLabelElement>;
}

export function Field({ label, htmlFor, children, labelProps }: FieldProps) {
  return (
    <div className={styles.field}>
      <label htmlFor={htmlFor} className={`${styles.label} text-label-md`} {...labelProps}>
        {label}
      </label>
      {children}
    </div>
  );
}

export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={styles.input} {...props} />;
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={styles.select} {...props} />;
}

export function ErrorText({ children }: { children: ReactNode }) {
  return <p className={`${styles.errorText} text-body-md`}>{children}</p>;
}

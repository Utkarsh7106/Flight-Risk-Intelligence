import type { ButtonHTMLAttributes } from 'react';
import styles from './Button.module.css';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost';
  fullWidth?: boolean;
}

/** DESIGN.md "Components": "Primary buttons are Solid Deep Navy.
 * Secondary are Outlined Slate. Ghost buttons are used for table actions."
 */
export function Button({ variant = 'primary', fullWidth = false, className = '', ...rest }: ButtonProps) {
  const classes = [styles.button, styles[variant], fullWidth ? styles.fullWidth : '', className]
    .filter(Boolean)
    .join(' ');
  return <button className={classes} {...rest} />;
}

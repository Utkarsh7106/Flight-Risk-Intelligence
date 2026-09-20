import type { HTMLAttributes } from 'react';
import styles from './Card.module.css';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  interactive?: boolean;
}

/** DESIGN.md "Elevation & Depth": Level 1 = white surface, 1px Slate-200
 * border, no shadow at rest. `interactive` adds the Level 2 hover
 * treatment (soft shadow + lift) for cards that act as links/buttons.
 */
export function Card({ interactive = false, className = '', ...rest }: CardProps) {
  const classes = [styles.card, interactive ? styles.interactive : '', className].filter(Boolean).join(' ');
  return <div className={classes} {...rest} />;
}

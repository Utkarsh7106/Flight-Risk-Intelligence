import styles from './Avatar.module.css';

/** No real avatar photos exist yet (avatar_url is always null in the
 * current seed data) — this renders initials on a deterministic color
 * instead of blocking on or faking a photo URL. The color is derived
 * from the name itself, not random, so the same person always gets the
 * same color across renders/sessions.
 */
const PALETTE = ['#0F172A', '#334155', '#0EA5E9', '#7C3AED', '#B45309', '#0D9488', '#BE185D', '#4338CA'];

function initialsOf(fullName: string): string {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function colorOf(seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  return PALETTE[hash % PALETTE.length];
}

interface AvatarProps {
  fullName: string;
  size?: 'sm' | 'md' | 'lg';
}

export function Avatar({ fullName, size = 'md' }: AvatarProps) {
  return (
    <span
      className={`${styles.avatar} ${styles[size]}`}
      style={{ background: colorOf(fullName) }}
      aria-hidden="true"
      title={fullName}
    >
      {initialsOf(fullName)}
    </span>
  );
}

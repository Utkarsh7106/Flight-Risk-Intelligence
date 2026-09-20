import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Avatar } from '../ui/Avatar';
import styles from './Sidebar.module.css';

/** Single sidebar, no top navbar — locked guardrail (ARCHITECTURE.md /
 * PROJECT_VISION.md "UI guardrails"). Workforce Health and Risk Analysis
 * are Module 2/3, not built yet: they render as disabled entries with a
 * "Coming soon" badge rather than real routes with placeholder data, per
 * the brief — there is nothing behind them to navigate to.
 */
export function Sidebar() {
  const { user, businessUnitName, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  if (!user) return null;

  const roleLabel = user.role === 'hr' ? 'HR' : businessUnitName ? `BU Head — ${businessUnitName}` : 'BU Head';

  return (
    <aside className={styles.sidebar}>
      <div className={`${styles.brand} text-headline-sm`}>Flight Risk Intelligence</div>

      <nav className={styles.nav} aria-label="Main">
        <NavLink
          to="/directory"
          className={({ isActive }) => `${styles.navLink} ${isActive ? styles.navLinkActive : ''}`}
        >
          <span className="text-body-md">Employee Directory</span>
        </NavLink>

        <span className={styles.navLinkDisabled} aria-disabled="true">
          <span className="text-body-md">Workforce Health</span>
          <span className={styles.comingSoonBadge}>Soon</span>
        </span>

        <span className={styles.navLinkDisabled} aria-disabled="true">
          <span className="text-body-md">Risk Analysis</span>
          <span className={styles.comingSoonBadge}>Soon</span>
        </span>
      </nav>

      <div className={styles.footer}>
        <div className={styles.identity}>
          <Avatar fullName={user.full_name} size="sm" />
          <div className={styles.identityText}>
            <span className={`${styles.identityName} text-body-md`}>{user.full_name}</span>
            <span className={`${styles.identityRole} text-label-md`}>{roleLabel}</span>
          </div>
        </div>
        <button type="button" className={styles.logoutButton} onClick={() => void handleLogout()}>
          Log out
        </button>
      </div>
    </aside>
  );
}

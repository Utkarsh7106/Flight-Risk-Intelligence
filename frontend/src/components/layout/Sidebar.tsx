import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Avatar } from '../ui/Avatar';
import styles from './Sidebar.module.css';

/** Single sidebar, no top navbar — locked guardrail (ARCHITECTURE.md /
 * PROJECT_VISION.md "UI guardrails"). Workforce Health (Module 2), Risk
 * Analysis (Module 3), and Departures (Module 4) are all real now.
 * Fairness Audit only renders for HR accounts — this is a UI courtesy
 * only, the real enforcement is backend/app/security/deps.py's
 * require_hr gate on the endpoint itself (see MODULE2_REFERENCE.md);
 * hiding the link here does not by itself make the audit HR-only. Risk
 * Analysis and Departures have no such gate — both render for both
 * roles, RLS-scoped like every other module (a BU Head can record and
 * see departures for their own BU — see MODULE4_REFERENCE.md).
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

        <NavLink
          to="/workforce-health"
          end
          className={({ isActive }) => `${styles.navLink} ${isActive ? styles.navLinkActive : ''}`}
        >
          <span className="text-body-md">Workforce Health</span>
        </NavLink>

        {user.role === 'hr' && (
          <NavLink
            to="/workforce-health/fairness-audit"
            className={({ isActive }) => `${styles.navLink} ${isActive ? styles.navLinkActive : ''}`}
          >
            <span className="text-body-md">Fairness Audit</span>
          </NavLink>
        )}

        <NavLink
          to="/risk-analysis"
          className={({ isActive }) => `${styles.navLink} ${isActive ? styles.navLinkActive : ''}`}
        >
          <span className="text-body-md">Risk Analysis</span>
        </NavLink>

        <NavLink
          to="/departures"
          className={({ isActive }) => `${styles.navLink} ${isActive ? styles.navLinkActive : ''}`}
        >
          <span className="text-body-md">Departures</span>
        </NavLink>
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

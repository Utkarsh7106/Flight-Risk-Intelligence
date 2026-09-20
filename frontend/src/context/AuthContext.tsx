import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { fetchCurrentUser, login as apiLogin, logout as apiLogout } from '../api/auth';
import { listEmployees } from '../api/employees';
import { ApiError, NetworkError } from '../api/client';
import type { CurrentUser } from '../api/types';

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated' | 'server_unreachable';

interface AuthContextValue {
  status: AuthStatus;
  user: CurrentUser | null;
  /** Only ever set for role === 'bu_head'. There's no /business-units
   * endpoint, so this is derived from the employee directory's nested
   * business_unit field on a one-row fetch right after login — see the
   * comment below. Null if that lookup fails or the BU has zero
   * employees; the UI falls back to just "BU Head" with no name in
   * that case rather than guessing.
   */
  businessUnitName: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [businessUnitName, setBusinessUnitName] = useState<string | null>(null);

  const resolveBusinessUnitName = useCallback(async (current: CurrentUser) => {
    if (current.role !== 'bu_head' || current.business_unit_id === null) {
      setBusinessUnitName(null);
      return;
    }
    try {
      const page = await listEmployees({ limit: 1 });
      const name = page.items[0]?.business_unit?.name ?? null;
      setBusinessUnitName(name);
    } catch {
      // No dedicated business-units endpoint exists to fall back to, and
      // this is a nice-to-have label, not a security boundary — RLS
      // already scopes /employees regardless of whether we know the name.
      setBusinessUnitName(null);
    }
  }, []);

  const refresh = useCallback(async () => {
    try {
      const current = await fetchCurrentUser();
      setUser(current);
      setStatus('authenticated');
      await resolveBusinessUnitName(current);
    } catch (err) {
      setUser(null);
      setBusinessUnitName(null);
      if (err instanceof NetworkError) {
        // Can't tell if the user is actually logged in — the backend
        // might be down, not the session. Don't claim "unauthenticated"
        // for something we genuinely don't know.
        setStatus('server_unreachable');
      } else {
        setStatus('unauthenticated');
      }
    }
  }, [resolveBusinessUnitName]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(
    async (email: string, password: string) => {
      const current = await apiLogin(email, password);
      setUser(current);
      setStatus('authenticated');
      await resolveBusinessUnitName(current);
    },
    [resolveBusinessUnitName],
  );

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } catch (err) {
      // Even if the network call fails, clear local state — the cookie
      // may or may not have been cleared server-side, but there's no
      // sane UI state where we keep pretending the user is logged in
      // after they asked to log out. Swallow ApiError/NetworkError here
      // deliberately; nothing actionable for the user in either case.
      if (!(err instanceof ApiError) && !(err instanceof NetworkError)) throw err;
    } finally {
      setUser(null);
      setBusinessUnitName(null);
      setStatus('unauthenticated');
    }
  }, []);

  return (
    <AuthContext.Provider value={{ status, user, businessUnitName, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}

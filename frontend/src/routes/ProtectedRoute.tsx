import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { FullPageState } from '../components/feedback/FullPageState';

/** Gates every route nested under it. Three non-authenticated states are
 * handled distinctly, not collapsed into one "redirect to login":
 * - loading: the initial GET /auth/me is still in flight.
 * - unauthenticated: the API confirmed there's no valid session ->
 *   redirect to /login, remembering where they were headed.
 * - server_unreachable: the request never reached the backend at all,
 *   so we genuinely don't know if there's a valid session — bouncing to
 *   login here would be misleading (it implies "you're logged out" when
 *   the truth is "we couldn't check").
 */
export function ProtectedRoute() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === 'loading') {
    return <FullPageState title="Loading…" spinner />;
  }

  if (status === 'server_unreachable') {
    return (
      <FullPageState
        title="Can't reach the server"
        description="The backend isn't responding. Confirm it's running, then try again."
        action={{ label: 'Retry', onClick: () => window.location.reload() }}
      />
    );
  }

  if (status === 'unauthenticated') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}

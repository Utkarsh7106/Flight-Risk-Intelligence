import { useState } from 'react';
import type { FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { ApiError, NetworkError } from '../../api/client';
import { Button } from '../../components/ui/Button';
import { Field, TextInput } from '../../components/ui/FormControls';
import styles from './LoginPage.module.css';

/** No role toggle here, deliberately. The Stitch login mockup
 * (design/stitch/simple_login_executive_hr_intelligence) had a
 * "Role Selection Toggle" comment wrapping an empty div — a leftover
 * from an earlier concept. Role comes entirely from which account logs
 * in (ARCHITECTURE.md, PROJECT_VISION.md); there is nothing to toggle,
 * and nothing here reintroduces the idea.
 */
export function LoginPage() {
  const { login, status } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setErrorMessage(null);
    try {
      await login(email, password);
      const redirectTo = (location.state as { from?: string } | null)?.from ?? '/directory';
      navigate(redirectTo, { replace: true });
    } catch (err) {
      // Surface exactly what the API said, nothing more — it already
      // returns the identical message for "wrong password" and "unknown
      // email" (no user enumeration). Don't add UI logic that tries to
      // be more specific than that.
      if (err instanceof ApiError) {
        setErrorMessage(err.detail ?? 'Sign-in failed. Please try again.');
      } else if (err instanceof NetworkError) {
        setErrorMessage('Unable to reach the server. Is the backend running?');
      } else {
        setErrorMessage('Something went wrong. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (status === 'authenticated') {
    return <Navigate to="/directory" replace />;
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h1 className={`${styles.brand} text-headline-md`}>Flight Risk Intelligence</h1>

        <form className={styles.form} onSubmit={handleSubmit}>
          {errorMessage && (
            <div className={`${styles.errorBanner} text-body-md`} role="alert">
              {errorMessage}
            </div>
          )}

          <Field label="Email" htmlFor="email">
            <TextInput
              id="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@lsdigital-demo.com"
            />
          </Field>

          <Field label="Password" htmlFor="password">
            <div className={styles.passwordRow}>
              <TextInput
                id="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
              <button
                type="button"
                className={styles.togglePassword}
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
          </Field>

          <Button type="submit" fullWidth disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign In'}
          </Button>
        </form>

        <p className={`${styles.hint} text-body-md`}>Use the account provided by your HR administrator.</p>
      </div>
    </div>
  );
}

import { useState } from "react";
import { Link, useLocation, useNavigate, type Location } from "react-router-dom";
import type { FormEvent } from "react";
import { ShieldCheck, LoaderCircle } from "lucide-react";
import { useAuth } from "../auth/useAuth";
import { getAuthErrorMessage } from "../auth/authErrors";
import "./Auth.css";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      await login(email.trim(), password);
      const from = (location.state as { from?: Location } | null)?.from;
      navigate(from ? `${from.pathname}${from.search ?? ""}` : "/dashboard", {
        replace: true,
      });
    } catch (err) {
      setError(getAuthErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <Link className="auth-brand" to="/">
          <span className="auth-brand-icon"><ShieldCheck size={19} /></span>
          Job Scam <strong>Radar</strong>
        </Link>
        <h1>Welcome back</h1>
        <p>Sign in to access your dashboard, analyzer, and private scan history.</p>
        {error && <div className="auth-message auth-error" role="alert">{error}</div>}
        <form className="auth-form" onSubmit={handleSubmit}>
          <label>Email<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          <button className="auth-submit" disabled={submitting} type="submit">
            {submitting && <LoaderCircle size={16} className="overview-spin" />}
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
        <div className="auth-links">
          <Link to="/forgot-password">Forgot password?</Link>
          <span>New here? <Link to="/register">Create an account</Link></span>
        </div>
      </section>
    </main>
  );
}

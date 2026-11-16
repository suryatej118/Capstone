import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { LoaderCircle, ShieldCheck } from "lucide-react";
import { useAuth } from "../auth/useAuth";
import { getAuthErrorMessage } from "../auth/authErrors";
import "./Auth.css";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");

    if (password.length < 6) {
      setError("Use a password with at least 6 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await register(email.trim(), password);
      navigate("/dashboard", { replace: true });
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
        <h1>Create your account</h1>
        <p>Keep your investigations private and available across sessions.</p>
        {error && <div className="auth-message auth-error" role="alert">{error}</div>}
        <form className="auth-form" onSubmit={handleSubmit}>
          <label>Email<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label>Password<input type="password" autoComplete="new-password" minLength={6} required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          <label>Confirm password<input type="password" autoComplete="new-password" minLength={6} required value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} /></label>
          <button className="auth-submit" disabled={submitting} type="submit">
            {submitting && <LoaderCircle size={16} className="overview-spin" />}
            {submitting ? "Creating account..." : "Create account"}
          </button>
        </form>
        <div className="auth-links">
          <span>Already registered? <Link to="/login">Sign in</Link></span>
        </div>
      </section>
    </main>
  );
}

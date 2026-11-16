import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { LoaderCircle, ShieldCheck } from "lucide-react";
import { useAuth } from "../auth/useAuth";
import { getAuthErrorMessage } from "../auth/authErrors";
import "./Auth.css";

export default function ForgotPassword() {
  const { resetPassword } = useAuth();
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setSubmitting(true);

    try {
      await resetPassword(email.trim());
      setSuccess("If an account exists for this email, a password reset link has been sent.");
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
        <h1>Reset your password</h1>
        <p>Enter your account email and we’ll send instructions to create a new password.</p>
        {error && <div className="auth-message auth-error" role="alert">{error}</div>}
        {success && <div className="auth-message auth-success" role="status">{success}</div>}
        <form className="auth-form" onSubmit={handleSubmit}>
          <label>Email<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <button className="auth-submit" disabled={submitting} type="submit">
            {submitting && <LoaderCircle size={16} className="overview-spin" />}
            {submitting ? "Sending..." : "Send reset link"}
          </button>
        </form>
        <div className="auth-links"><Link to="/login">Back to sign in</Link></div>
      </section>
    </main>
  );
}

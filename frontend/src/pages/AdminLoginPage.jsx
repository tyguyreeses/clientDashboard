import { useEffect, useState } from "react";

export function AdminLoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const signIn = () => { setLoading(true); window.location.assign("/api/auth/google/login"); };
  useEffect(() => {
    fetch("/api/auth/flash").then((response) => response.ok ? response.json() : {}).then((body) => {
      if (body.category === "unauthorized") setError("This Google account is not authorized.");
      else if (body.category) setError("Sign-in failed. Please try again.");
    }).catch(() => {});
  }, []);
  return (
    <main className="brand-page admin-login-page">
      <div className="brand-page-orb brand-page-orb-one" />
      <div className="brand-page-orb brand-page-orb-two" />
      <section className="brand-page-card">
        <img className="brand-page-logo" src="/logo_banner.PNG" alt="Hair By Maddie · Bridal Hairstylist" />
        <div className="brand-page-content">
          <h1>Welcome back</h1>
          <p>Sign in to manage your clients, inquiries, and wedding bookings.</p>
          {error && <p className="brand-page-error" role="alert">{error}</p>}
          <button className="brand-page-button" onClick={signIn} disabled={loading}>
            <span className="google-mark" aria-hidden="true">G</span>
            {loading ? "Redirecting…" : "Continue with Google"}
          </button>
          <p className="brand-page-secure">Secure admin access</p>
        </div>
      </section>
      <p className="brand-page-footnote">Hair By Maddie · Bridal Hairstylist</p>
    </main>
  );
}

import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import { App } from "./App";
import { AdminLoginPage } from "./pages/AdminLoginPage";
import { setCsrfToken } from "./utils";

function BrandPage({ children, className = "" }) {
  return (
    <main className={`brand-page ${className}`}>
      <div className="brand-page-orb brand-page-orb-one" />
      <div className="brand-page-orb brand-page-orb-two" />
      <section className="brand-page-card">
        <img className="brand-page-logo" src="/logo_banner.PNG" alt="Hair By Maddie · Bridal Hairstylist" />
        {children}
      </section>
      <p className="brand-page-footnote">Bridal hairstyling · New England</p>
    </main>
  );
}

function ComingSoon() {
  return (
    <BrandPage className="coming-soon-page">
      <div className="brand-page-content">
        <h1>We’re getting ready<br />for your big day</h1>
        <p>Our new online home is almost here. In the meantime, we’re busy creating beautiful bridal hair experiences for you.</p>
        <span className="brand-page-divider" aria-hidden="true">✦</span>
      </div>
    </BrandPage>
  );
}

function Root() {
  const path = window.location.pathname;
  if (path === "/") return <ComingSoon />;
  if (path === "/admin/login") return <AdminLoginPage />;
  if (path === "/admin") return <Admin />;
  return <ComingSoon />;
}

function Admin() {
  const [state, setState] = React.useState("loading");
  React.useEffect(() => { fetch("/api/auth/me").then(async response => {
    if (!response.ok) { window.location.replace("/admin/login"); return; }
    const body = await response.json(); setCsrfToken(body.csrf_token); setState("ready");
  }).catch(() => setState("error")); }, []);
  if (state !== "ready") {
    return (
      <BrandPage className="admin-login-page">
        <div className="brand-page-content brand-page-loading">
          <h1>{state === "error" ? "We couldn’t connect" : "One moment"}</h1>
          <p>{state === "error" ? "Please refresh and try again." : "Preparing your studio dashboard…"}</p>
        </div>
      </BrandPage>
    );
  }
  return <App />;
}

createRoot(document.getElementById("root")).render(<Root />);

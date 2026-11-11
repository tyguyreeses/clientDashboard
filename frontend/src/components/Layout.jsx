import { initials } from "../utils";

export function Header({ page, onNavigate, onAddClient, user }) {
  const identity = user?.display_name || user?.email?.split("@")[0] || "User";
  const userInitials = initials(identity) || "U";
  return (
    <header className="site-header">
      <a className="brand" href="#" onClick={() => onNavigate("dashboard")}>
        <img className="brand-favicon" src="/favicon.PNG" alt="" />
        <span>Hair By Maddie</span>
      </a>
      <nav>
        <a
          className={page === "dashboard" ? "active" : ""}
          href="#board"
          onClick={(event) => {
            event.preventDefault();
            onNavigate("dashboard");
          }}
        >
          Dashboard
        </a>
        <a
          className={page === "history" ? "active" : ""}
          href="#history"
          onClick={(event) => {
            event.preventDefault();
            onNavigate("history");
          }}
        >
          History
        </a>
        <a
          className={page === "pricing" ? "active" : ""}
          href="#pricing"
          onClick={(event) => {
            event.preventDefault();
            onNavigate("pricing");
          }}
        >
          Pricing
        </a>
        <a href="#calendar">
          Calendar <small>soon</small>
        </a>
        <a href="#finances">
          Finances <small>soon</small>
        </a>
      </nav>
      <button className="header-add" onClick={onAddClient}>
        ＋ New client
      </button>
      <button className="avatar" aria-label={`Open profile for ${identity}`}>
        {userInitials}
      </button>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="site-footer">
      <span className="footer-brand">
        <img src="/favicon.PNG" alt="" /> Hair By Maddie
      </span>
      <span>Connected to API</span>
    </footer>
  );
}

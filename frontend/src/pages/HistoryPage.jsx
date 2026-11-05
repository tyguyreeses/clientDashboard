import { useEffect, useMemo, useState } from "react";
import { STATUS, TRIAL_STATUS, formatDate, json, weddingView } from "../utils";

export function HistoryPage({ onSelect }) {
  const [clients, setClients] = useState([]);
  const [weddings, setWeddings] = useState([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [archive, setArchive] = useState("all");
  const [source, setSource] = useState("all");
  const [trial, setTrial] = useState("all");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      json("/clients?include_archived=true"),
      json("/weddings?include_archived=true"),
    ]).then(([clientData, weddingData]) => {
      setClients(clientData);
      setWeddings(weddingData.map(weddingView));
    }).catch((err) => setError(err.message)).finally(() => setLoading(false));
  }, []);

  const sources = useMemo(() => [...new Set(clients.map((client) => client.source).filter(Boolean))].sort(), [clients]);
  const results = useMemo(() => weddings.filter((wedding) => {
    const haystack = [wedding.name, wedding.email, wedding.phone, wedding.socialMedia, wedding.address, wedding.city, wedding.venue, wedding.source, wedding.notes]
      .filter(Boolean).join(" ").toLowerCase();
    const matchesQuery = !query.trim() || haystack.includes(query.trim().toLowerCase());
    const matchesStatus = status === "all" || String(wedding.status) === status;
    const matchesArchive = archive === "all" || String(Boolean(wedding.archived)) === archive;
    const matchesSource = source === "all" || wedding.source === source;
    const matchesTrial = trial === "all" || wedding.bridalTrialStatus === trial;
    const matchesFrom = !from || wedding.weddingDate >= from;
    const matchesTo = !to || wedding.weddingDate <= to;
    return matchesQuery && matchesStatus && matchesArchive && matchesSource && matchesTrial && matchesFrom && matchesTo;
  }), [weddings, query, status, archive, source, trial, from, to]);

  return <main className="history-page">
    <div className="page-heading"><div><p className="eyebrow">History</p><h1>Search everything</h1><p className="muted">Find current and archived client records, weddings, and inquiries.</p></div></div>
    <section className="history-filters">
      <input className="history-search" placeholder="Search names, contact details, venues, addresses, notes…" value={query} onChange={(event) => setQuery(event.target.value)} />
      <select value={archive} onChange={(event) => setArchive(event.target.value)}><option value="all">Current and archived</option><option value="false">Current only</option><option value="true">Archived only</option></select>
      <select value={status} onChange={(event) => setStatus(event.target.value)}><option value="all">All workflow statuses</option>{Object.entries(STATUS).map(([value, item]) => <option key={value} value={value}>{item.label}</option>)}</select>
      <select value={trial} onChange={(event) => setTrial(event.target.value)}><option value="all">All bridal trial statuses</option>{Object.entries(TRIAL_STATUS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
      <select value={source} onChange={(event) => setSource(event.target.value)}><option value="all">All sources</option>{sources.map((item) => <option key={item} value={item}>{item}</option>)}</select>
      <label>Wedding date from<input type="date" value={from} onChange={(event) => setFrom(event.target.value)} /></label>
      <label>Wedding date to<input type="date" value={to} onChange={(event) => setTo(event.target.value)} /></label>
    </section>
    {error && <div className="api-message error">{error}</div>}
    {loading ? <div className="loading-state">Loading history…</div> : <section className="history-results"><strong>{results.length} result{results.length === 1 ? "" : "s"}</strong>{results.map((wedding) => <button className="history-result" key={wedding.id} onClick={() => onSelect(wedding)}><span className="initials">{wedding.initials}</span><span><strong>{wedding.name}</strong><small>{formatDate(wedding.weddingDate)} · {wedding.venue || wedding.address}</small><small>{wedding.email || "No email"} · {wedding.phone || "No phone"}</small></span><span className="history-result-meta"><b>{STATUS[wedding.status]?.label}</b><small>{wedding.archived ? "Archived" : "Current"}</small></span></button>)}{!results.length && <p className="muted">No matching records.</p>}</section>}
  </main>;
}

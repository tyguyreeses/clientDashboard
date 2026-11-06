import { useEffect, useState } from "react";
import { json } from "../utils";

const fields = [
  ["bride_price", "Bride price", "money"],
  ["trial_price", "Trial price", "money"],
  ["bridesmaid_price", "Bridal-party price", "money"],
  ["flowergirl_price", "Flower-girl price", "money"],
  ["early_morning_fee", "Early-morning fee", "money"],
  ["assistant_fee", "Assistant fee", "money"],
  ["assistant_bridesmaid_cut", "Assistant pay per bridal-party service", "money"],
  ["base_travel_fee", "Base travel rate", "money"],
  ["travel_fee", "Per-mile rate", "money"],
  ["assistant_travel_fee_cut", "Travel amount retained", "money"],
  ["deposit_percentage", "Deposit percentage", "percent"],
  ["travel_discount_percentage", "Travel-discount percentage", "percent"],
  ["bride_duration_minutes", "Bride duration (minutes)", "minutes"],
  ["bridesmaid_updo_duration_minutes", "Bridal-party updo duration (minutes)", "minutes"],
  ["bridesmaid_down_duration_minutes", "Bridal-party half-up/down duration (minutes)", "minutes"],
  ["flowergirl_duration_minutes", "Flower-girl duration (minutes)", "minutes"],
];

const formFrom = (version) => ({
  name: version?.name || "",
  ...Object.fromEntries(fields.map(([key]) => [key, version?.[key] ?? ""])),
});

const dateLabel = (value) => {
  const [year, month, day] = value.split("-");
  return `${month}/${day}/${year}`;
};

const historyLabel = (version) => {
  const [year, month, day] = version.created_date.split("-");
  return `${version.name} - ${month}/${day}/${year}`;
};

export function PricingPage() {
  const [versions, setVersions] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [form, setForm] = useState(formFrom());
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setError("");
    try {
      const data = await json("/pricing-versions");
      setVersions(data);
      if (data.length) {
        setSelectedId(data[0].id);
        setForm(formFrom(data[0]));
      }
    } catch (err) {
      setError(err.message);
    }
  };
  useEffect(() => { load(); }, []);

  const selected = versions.find((item) => item.id === selectedId);
  const editable = Boolean(selected?.is_default);
  const update = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }));
    setPreview(null);
  };
  const requestPreview = async (event) => {
    event.preventDefault();
    setBusy(true); setError("");
    try { setPreview(await json("/pricing-versions/save-preview", { method: "POST", body: JSON.stringify(form) })); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  const save = async () => {
    setBusy(true); setError("");
    try {
      await json("/pricing-versions/save", {
        method: "POST",
        body: JSON.stringify({ ...form, confirmed: true, confirmation_fingerprint: preview.confirmation_fingerprint }),
      });
      setPreview(null);
      await load();
    } catch (err) {
      setPreview(null);
      setError(err.message);
    } finally { setBusy(false); }
  };
  const remove = async () => {
    if (!selected) return;
    const promotion = selected.is_default ? " The next-newest version will become the default." : "";
    if (!window.confirm(`Delete ${selected.name}?${promotion}`)) return;
    try {
      await json(`/pricing-versions/${selected.id}?confirmed=true&expected_default_id=${versions[0].id}`, { method: "DELETE" });
      await load();
    } catch (err) { setError(err.message); }
  };

  return <main className="pricing-page">
    <div className="pricing-heading"><div><h1>Pricing</h1><p>Manage pricing and service-time assumptions.</p></div></div>
    {error && <div className="api-message error">{error}</div>}
    {!selected ? <div className="loading-state">No pricing version found.</div> : <>
      <form className="pricing-form" onSubmit={requestPreview}>
        <label className="pricing-name">Version name<input required maxLength="15" value={form.name} readOnly={!editable} onChange={(event) => update("name", event.target.value)} /></label>
        <div className="pricing-grid">
          {fields.map(([key, label, kind]) => <label key={key}>{label}<input
            type="number" required min="0" max={kind === "percent" ? "100" : undefined}
            step={kind === "minutes" ? "1" : "0.01"} value={form[key]} readOnly={!editable}
            onChange={(event) => update(key, event.target.value)}
          /></label>)}
        </div>
        {editable && <button className="profile-save" disabled={busy}>{busy ? "Checking…" : "Review pricing save"}</button>}
      </form>
      {preview && <section className="pricing-confirmation">
        <h2>{preview.action === "correct" ? "Confirm pricing correction" : "Confirm new default pricing"}</h2>
        {preview.affected_records.length > 0 && <><p><strong>Pricing changed—these invoices must be regenerated manually:</strong></p><div className="pricing-impacts">{preview.affected_records.map((row) => <div key={row.invoice_id}>
          <strong>{row.client_name}</strong><span>{dateLabel(row.wedding_date)} · status {row.workflow_status}{row.archived ? " · archived" : ""}</span><span>Invoice ${row.grand_total} · paid ${row.payment_total} ({row.payment_state})</span>
        </div>)}</div></>}
        <div className="pricing-actions"><button onClick={() => setPreview(null)}>Cancel</button><button className="profile-save" disabled={busy} onClick={save}>Confirm save</button></div>
      </section>}
      <section className="pricing-history"><h2>Pricing history</h2><div className="pricing-history-controls"><select value={selectedId} onChange={(event) => {
        const id = Number(event.target.value); const version = versions.find((item) => item.id === id);
        setSelectedId(id); setForm(formFrom(version)); setPreview(null);
      }}>{versions.map((version) => <option key={version.id} value={version.id}>{historyLabel(version)}</option>)}</select>
      <button className="pricing-delete" disabled={!selected.can_delete} title={selected.delete_block_reason || ""} onClick={remove}>Delete version</button></div>
      {!editable && <p className="muted">Historical versions are read-only.</p>}</section>
    </>}
  </main>;
}

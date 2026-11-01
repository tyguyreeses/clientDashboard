import { useState } from "react";
import { Editable } from "../components/FormFields";
import {
  formatDate,
  json,
  STATUS,
  TRIAL_STATUS,
  weddingView,
  initials,
} from "../utils";

export function ProfilePage({ wedding, onClose, onSaved }) {
  const [draft, setDraft] = useState(wedding);
  const [saving, setSaving] = useState(false);
  const update = (field, value) =>
    setDraft((item) => ({ ...item, [field]: value }));
  const save = async () => {
    setSaving(true);
    try {
      const updated = await json(`/clients/${draft.clientId}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: draft.name,
          email: draft.email,
          phone: draft.phone,
          notes: draft.notes,
          source: draft.source,
        }),
      });
      const result = {
        ...draft,
        name: updated.name,
        email: updated.email || "",
        phone: updated.phone || "",
        notes: updated.notes || "",
        source: updated.source || "Unknown source",
        initials: initials(updated.name),
      };
      onSaved(result);
    } catch (err) {
      alert(err.message);
    } finally {
      setSaving(false);
    }
  };
  return (
    <main className="profile-page">
      <button className="back-button" onClick={onClose}>
        ← Back to wedding board
      </button>
      <div className="profile-hero">
        <span className="large-initials">{initials(draft.name)}</span>
        <div>
          <p className="eyebrow">Client</p>
          <h1>{draft.name}</h1>
          <p>
            {draft.email} · {draft.phone}
          </p>
        </div>
        <span className="profile-save">Connected to API</span>
      </div>
      <section className="profile-section">
        <div className="profile-section-title">
          <span className="section-number peach-number">01</span>
          <div>
            <p className="eyebrow">Details</p>
            <h2>Client details</h2>
          </div>
        </div>
        <div className="detail-grid editable-grid">
          <Editable
            label="Client name"
            value={draft.name}
            onChange={(value) => update("name", value)}
          />
          <Editable
            label="Email"
            value={draft.email}
            onChange={(value) => update("email", value)}
          />
          <Editable
            label="Phone"
            value={draft.phone}
            onChange={(value) => update("phone", value)}
          />
          <Editable
            label="Source"
            value={draft.source}
            onChange={(value) => update("source", value)}
          />
          <Detail label="Wedding date" value={formatDate(draft.weddingDate)} />
          <Detail label="Location" value={draft.location} />
          <div className="editable-select">
            <label>Workflow status</label>
            <select
              className={`status-select ${STATUS[draft.status].tone}`}
              value={draft.status}
              onChange={async (e) => {
                const updated = await json(`/weddings/${draft.id}`, {
                  method: "PATCH",
                  body: JSON.stringify({ status: Number(e.target.value) }),
                });
                const next = weddingView({
                  ...updated,
                  client: {
                    name: draft.name,
                    email: draft.email,
                    phone: draft.phone,
                    source: draft.source,
                    notes: draft.notes,
                  },
                });
                setDraft(next);
                onSaved(next);
              }}
            >
              {Object.entries(STATUS).map(([value, option]) => (
                <option key={value} value={value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <button className="full-button save-button" onClick={save}>
          {saving ? "Saving…" : "Save client details ✦"}
        </button>
      </section>
      <section className="profile-section trial-section">
        <div className="profile-section-title">
          <span className="section-number lilac-number">02</span>
          <div>
            <p className="eyebrow">Details</p>
            <h2>Wedding details</h2>
          </div>
        </div>
        <div className="detail">
          <small>Bridal trial status</small>
          <strong>{TRIAL_STATUS[draft.bridalTrialStatus]}</strong>
        </div>
        <div className="detail profile-detail">
          <small>Party</small>
          <strong>{draft.party}</strong>
        </div>
        <label className="notes-label">
          Notes
          <textarea
            value={draft.notes}
            onChange={(e) => update("notes", e.target.value)}
          />
        </label>
      </section>
    </main>
  );
}

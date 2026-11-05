import { useState } from "react";
import { BooleanField, Editable, SelectField } from "../components/FormFields";
import { formatDate, initials, json, STATUS } from "../utils";

export function ClientDetails({ client, weddings, onSaved, onArchived }) {
  const [draft, setDraft] = useState(client);
  const [saving, setSaving] = useState(false);
  const update = (field, value) =>
    setDraft((item) => ({ ...item, [field]: value }));
  const save = async () => {
    setSaving(true);
    try {
      const saved = await json(`/clients/${client.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: draft.name,
          email: draft.email,
          phone: draft.phone,
          source: draft.source,
          social_media: draft.social_media,
          inquiry_date: draft.inquiry_date,
          notes: draft.notes,
          planning_stage: draft.planning_stage,
          makeup_interest: draft.makeup_interest,
          recommendations_if_unavailable: draft.recommendations_if_unavailable,
          referral_name: draft.referral_name,
        }),
      });
      setDraft(saved);
      onSaved(saved);
    } catch (error) {
      alert(error.message);
    } finally {
      setSaving(false);
    }
  };
  return (
    <section className="client-detail-card">
      <div className="client-detail-heading">
        <span className="large-initials">{initials(draft.name)}</span>
        <div>
          <p className="eyebrow">Client</p>
          <h2>{draft.name}</h2>
        </div>
      </div>
      <div className="detail-grid editable-grid">
        <Editable
          label="Name"
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
        <Editable
          label="Social media"
          value={draft.social_media}
          onChange={(value) => update("social_media", value)}
        />
        <Editable
          label="Inquiry date"
          type="date"
          value={draft.inquiry_date}
          onChange={(value) => update("inquiry_date", value)}
        />
        <SelectField
          label="Planning stage"
          value={draft.planning_stage}
          onChange={(value) => update("planning_stage", value)}
          options={[
            ["looking", "Just looking around"],
            ["invoice", "Love your work — send pricing info"],
            ["book", "So excited to book!"],
          ]}
        />
        <BooleanField
          label="Interested in makeup"
          value={draft.makeup_interest}
          onChange={(value) => update("makeup_interest", value)}
        />
        <BooleanField
          label="Recommendations if unavailable"
          value={draft.recommendations_if_unavailable}
          onChange={(value) => update("recommendations_if_unavailable", value)}
        />
        <Editable
          label="Referral name"
          value={draft.referral_name}
          onChange={(value) => update("referral_name", value)}
        />
      </div>
      <label className="notes-label">
        Notes
        <textarea
          value={draft.notes || ""}
          onChange={(event) => update("notes", event.target.value)}
        />
      </label>
      <button className="full-button save-button" onClick={save}>
        {saving ? "Saving…" : "Save changes"}
      </button>
      <div className="client-danger-actions">
        <button
          type="button"
          onClick={async () => {
            if (
              !window.confirm(
                "Archive this client? They will be removed from the active dashboard.",
              )
            )
              return;
            await json(`/clients/${client.id}`, {
              method: "PATCH",
              body: JSON.stringify({ archived: true }),
            });
            onArchived(client.id);
          }}
        >
          Archive client
        </button>
        <button
          type="button"
          onClick={async () => {
            if (
              !window.confirm(
                "Permanently delete this client and all related records? This cannot be undone.",
              )
            )
              return;
            await json(`/clients/${client.id}`, { method: "DELETE" });
            onArchived(client.id);
          }}
        >
          Delete permanently
        </button>
      </div>
      <div className="related-weddings">
        <h3>Weddings</h3>
        {weddings.length ? (
          weddings.map((wedding) => (
            <div className="related-wedding" key={wedding.id}>
              <span>
                <strong>{formatDate(wedding.weddingDate)}</strong>
                <small>{wedding.address}</small>
              </span>
              <span className={`trial-pill ${STATUS[wedding.status].tone}`}>
                {STATUS[wedding.status].label}
              </span>
            </div>
          ))
        ) : (
          <p className="muted">No weddings.</p>
        )}
      </div>
    </section>
  );
}

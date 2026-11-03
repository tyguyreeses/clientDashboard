import { useState } from "react";
import { Editable, SelectField } from "./FormFields";
import { json } from "../utils";

export function AddClientModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    social_media: "",
    source: "",
    referral: "",
    inquiry_date: new Date().toISOString().slice(0, 10),
    notes: "",
    wedding_date: "",
    location: "",
    ready_by: "",
    party_details: "",
    makeup: "",
    bridal_trial: "",
    planning_stage: "",
    recommendations: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const update = (field, value) =>
    setForm((item) => ({ ...item, [field]: value }));
  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const client = await json("/clients", {
        method: "POST",
        body: JSON.stringify({
          name: form.name,
          email: form.email,
          phone: form.phone,
          social_media: form.social_media,
          source: form.source,
          inquiry_date: form.inquiry_date || null,
          notes: form.notes || null,
          planning_stage: form.planning_stage,
          makeup_interest: form.makeup === "yes",
          recommendations_if_unavailable: form.recommendations === "yes",
          referral_name: form.referral || "N/A",
        }),
      });
      const wedding = await json("/weddings", {
        method: "POST",
        body: JSON.stringify({
          client_id: client.id,
          wedding_date: form.wedding_date,
          location: form.location || null,
          ready_by: form.ready_by || null,
          hair_service_count: Number(form.party_details),
          status: 1,
          bridal_trial_status:
            form.bridal_trial === "yes" ? "interested" : "not_interested",
        }),
      });
      onCreated(client, wedding);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      <form className="client-modal" onSubmit={submit}>
        <button type="button" className="close-button" onClick={onClose}>
          ×
        </button>
        <h2>New client inquiry</h2>
        {error && <div className="api-message error">{error}</div>}
        <div className="modal-fields">
          <Editable
            label="Email *"
            type="email"
            value={form.email}
            required
            onChange={(value) => update("email", value)}
          />
          <Editable
            label="Full name *"
            value={form.name}
            required
            onChange={(value) => update("name", value)}
          />
          <Editable
            label="Phone number"
            value={form.phone}
            onChange={(value) => update("phone", value)}
          />
          <Editable
            label="Instagram / Facebook *"
            value={form.social_media}
            required
            onChange={(value) => update("social_media", value)}
          />
          <Editable
            label="Wedding date *"
            type="date"
            value={form.wedding_date}
            required
            onChange={(value) => update("wedding_date", value)}
          />
          <Editable
            label="Venue location / full address *"
            value={form.location}
            required
            onChange={(value) => update("location", value)}
          />
          <Editable
            label="People needing hair done *"
            type="number"
            min="0"
            step="1"
            value={form.party_details}
            required
            onChange={(value) => update("party_details", value)}
          />
          <Editable
            label="Ready-by time *"
            type="time"
            min="01:00"
            max="12:00"
            step={15 * 60}
            value={form.ready_by}
            required
            onChange={(value) => update("ready_by", value)}
          />
          <SelectField
            label="Interested in makeup services? *"
            value={form.makeup}
            onChange={(value) => update("makeup", value)}
            options={[
              ["yes", "Yes please!"],
              ["already", "Already got my girl!"],
            ]}
            required
          />
          <SelectField
            label="Interested in a bridal trial? *"
            value={form.bridal_trial}
            onChange={(value) => update("bridal_trial", value)}
            options={[
              ["yes", "Yes please!"],
              ["thinking", "I’m still thinking about it!"],
            ]}
            required
          />
          <SelectField
            label="Planning process *"
            value={form.planning_stage}
            onChange={(value) => update("planning_stage", value)}
            options={[
              ["looking", "Just looking around"],
              ["invoice", "Love your work — send pricing info"],
              ["book", "So excited to book!"],
            ]}
            required
          />
          <SelectField
            label="Recommendations if unavailable?"
            value={form.recommendations}
            onChange={(value) => update("recommendations", value)}
            options={[
              ["yes", "Yes, please"],
              ["no", "No thanks"],
            ]}
          />
          <Editable
            label="How did you hear about me? *"
            value={form.source}
            required
            onChange={(value) => update("source", value)}
          />
          <Editable
            label="Who referred you? *"
            value={form.referral}
            required
            onChange={(value) => update("referral", value)}
          />
        </div>
        <label className="notes-label">
          Anything else to know
          <textarea
            value={form.notes}
            onChange={(event) => update("notes", event.target.value)}
          />
        </label>
        <button className="full-button" disabled={saving}>
          {saving ? "Saving inquiry…" : "Create client & inquiry ✦"}
        </button>
      </form>
    </div>
  );
}

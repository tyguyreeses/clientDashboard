import { useRef, useState } from "react";
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
    party_details: "1",
    makeup: "",
    bridal_trial: "",
    planning_stage: "",
    recommendations: "",
  });
  const initialForm = useRef(form);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const requestClose = () => {
    const dirty = JSON.stringify(form) !== JSON.stringify(initialForm.current);
    if (dirty && !window.confirm("Current changes will be lost. Close without saving?")) return;
    onClose();
  };
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
      onMouseDown={(event) => event.target === event.currentTarget && requestClose()}
    >
      <form className="client-modal" onSubmit={submit}>
        <button type="button" className="close-button" onClick={requestClose}>
          ×
        </button>
        <h2>New client inquiry</h2>
        {error && <div className="api-message error">{error}</div>}
        <div className="modal-fields">
          <Editable
            label="Full name *"
            value={form.name}
            required
            onChange={(value) => update("name", value)}
          />
          <Editable
            label="Email *"
            type="email"
            value={form.email}
            required
            onChange={(value) => update("email", value)}
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
            label="Makeup recommendations? *"
            value={form.makeup}
            onChange={(value) => update("makeup", value)}
            options={[
              ["yes", "Yes"],
              ["already", "No"],
            ]}
            required
          />
          <SelectField
            label="Bridal trial? *"
            value={form.bridal_trial}
            onChange={(value) => update("bridal_trial", value)}
            options={[
              ["yes", "Yes"],
              ["thinking", "Still thinking"],
            ]}
            required
          />
          <SelectField
            label="Planning process *"
            value={form.planning_stage}
            onChange={(value) => update("planning_stage", value)}
            options={[
              ["looking", "Exploring"],
              ["invoice", "Send invoice"],
              ["book", "Book now"],
            ]}
            required
          />
          <SelectField
            label="Recommendations if unavailable?"
            value={form.recommendations}
            onChange={(value) => update("recommendations", value)}
            options={[
              ["yes", "Yes"],
              ["no", "No"],
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

import { useState } from "react";
import {
  BooleanField,
  Detail,
  Editable,
  SelectField,
} from "../components/FormFields";
import {
  formatDate,
  json,
  STATUS,
  TRIAL_STATUS,
  weddingView,
  HAIRSTYLE,
  PARTY_ROLE,
} from "../utils";

const TRIAL_STEPS = ["interested", "link_sent", "booked", "complete"];

function TrialBoard({ status, onChange }) {
  const [dragging, setDragging] = useState(false);
  if (["not_interested", "cancelled"].includes(status)) return null;
  return (
    <div className="trial-kanban">
      <div className="trial-kanban-label">Bridal trial</div>
      <div className="trial-kanban-columns">
        {TRIAL_STEPS.map((step) => (
          <div className={`trial-step ${status === step ? "active" : ""}`} key={step} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); setDragging(false); onChange(step); }}>
            <span>{TRIAL_STATUS[step]}</span>
            {status === step && <span className="trial-star" draggable onDragStart={() => setDragging(true)} onDragEnd={() => setDragging(false)} aria-label="Drag bridal trial">★</span>}
          </div>
        ))}
      </div>
      {dragging && <div className="trial-cancel-zone" onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); setDragging(false); onChange("cancelled"); }}>Cancel trial</div>}
    </div>
  );
}

export function ProfilePage({ wedding, onClose, onSaved }) {
  const [draft, setDraft] = useState(wedding);
  const [editingSection, setEditingSection] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const update = (field, value) =>
    setDraft((item) => ({ ...item, [field]: value }));
  const requestClose = () => {
    if (editingSection && !window.confirm("Current changes will be lost. Close without saving?")) return;
    onClose();
  };

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      const [client, updatedWedding] = await Promise.all([
        json(`/clients/${draft.clientId}`, {
          method: "PATCH",
          body: JSON.stringify({
            name: draft.name,
            email: draft.email,
            phone: draft.phone,
            inquiry_date: draft.inquiryDate || null,
            social_media: draft.socialMedia || null,
            source: draft.source || null,
            planning_stage: draft.planningStage || null,
            makeup_interest: draft.makeupInterest,
            recommendations_if_unavailable:
              draft.recommendationsIfUnavailable,
            referral_name: draft.referralName || null,
            notes: draft.notes || null,
          }),
        }),
        json(`/weddings/${draft.id}`, {
          method: "PATCH",
          body: JSON.stringify({
            wedding_date: draft.weddingDate,
            location: draft.location || null,
            ready_by: draft.readyBy || null,
            status: Number(draft.status),
            bridal_trial_status: draft.bridalTrialStatus,
          }),
        }),
      ]);
      const members = draft.partyMembers || [];
      await Promise.all(
        members.map((member) =>
          json(`/party-members/${member.id}`, {
            method: "PATCH",
            body: JSON.stringify({
              role: member.role,
              hairstyle: member.hairstyle,
              assistant: Boolean(member.assistant),
            }),
          }),
        ),
      );
      const refreshedWedding = await json(`/weddings/${draft.id}`);
      const result = weddingView({ ...refreshedWedding, client });
      onSaved(result);
      setDraft(result);
      setEditingSection(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop profile-backdrop" onMouseDown={(event) => event.target === event.currentTarget && requestClose()}>
      <main className="profile-page profile-modal">
        <button className="close-button" onClick={requestClose} aria-label="Close profile">×</button>
      {error && <div className="api-message error">{error}</div>}
      <div className="profile-hero">
        <div>
          <p className="eyebrow">Client</p>
          {editingSection === "header" ? (
            <input
              className="profile-name-input"
              value={draft.name}
              onChange={(event) => update("name", event.target.value)}
            />
          ) : (
            <h1>{draft.name}</h1>
          )}
          {editingSection === "header" ? (
            <div className="profile-contact-edit">
              <input
                value={draft.email}
                aria-label="Email"
                onChange={(event) => update("email", event.target.value)}
              />
              <span>·</span>
              <input
                value={draft.phone}
                aria-label="Phone"
                onChange={(event) => update("phone", event.target.value)}
              />
            </div>
          ) : (
            <p>{draft.email || "Email not provided"} · {draft.phone || "Phone not provided"}</p>
          )}
          {editingSection === "header" && (
            <input
              className="profile-inquiry-date"
              type="date"
              value={draft.inquiryDate || ""}
              aria-label="Inquiry date"
              onChange={(event) => update("inquiryDate", event.target.value)}
            />
          )}
          {editingSection !== "header" && <p>Inquiry: {formatDate(draft.inquiryDate)}</p>}
        </div>
        <div className="profile-actions">
          {editingSection === "header" ? (
            <>
              <button className="profile-save" onClick={save} disabled={saving}>{saving ? "Saving…" : "Save"}</button>
              <button className="profile-cancel" onClick={() => { setDraft(wedding); setEditingSection(null); }}>Cancel</button>
            </>
          ) : <button className="profile-save" onClick={() => setEditingSection("header")}>Edit</button>}
        </div>
      </div>

      <section className="profile-section trial-section">
        <div className="profile-section-title">
          <span className="section-number lilac-number">01</span>
          <div><p className="eyebrow">Details</p><h2>Wedding details</h2></div>
          {editingSection === "wedding" ? <div className="section-actions"><button className="profile-save" onClick={save} disabled={saving}>{saving ? "Saving…" : "Save"}</button><button className="profile-cancel" onClick={() => { setDraft(wedding); setEditingSection(null); }}>Cancel</button></div> : <button className="profile-save" onClick={() => setEditingSection("wedding")}>Edit</button>}
        </div>
        <div className="detail-grid">
          {editingSection === "wedding" ? (
            <Editable label="Wedding date" type="date" value={draft.weddingDate} onChange={(value) => update("weddingDate", value)} />
          ) : <Detail label="Wedding date" value={formatDate(draft.weddingDate)} />}
          {editingSection === "wedding" ? (
            <Editable label="Location" value={draft.location === "Location TBD" ? "" : draft.location} onChange={(value) => update("location", value)} />
          ) : <Detail label="Location" value={draft.location} />}
          {editingSection === "wedding" ? (
            <Editable label="Ready-by time" type="time" step={15 * 60} min="01:00" max="12:00" value={draft.readyBy} onChange={(value) => update("readyBy", value)} />
          ) : <Detail label="Ready by" value={draft.readyBy} />}
          {editingSection === "wedding" ? (
            <div className="editable-select"><label>Workflow status</label><select value={draft.status} onChange={(event) => update("status", event.target.value)}>{Object.entries(STATUS).map(([value, option]) => <option key={value} value={value}>{option.label}</option>)}</select></div>
          ) : <Detail label="Workflow status" value={STATUS[draft.status]?.label} />}
          {editingSection === "wedding" ? (
            <div className="editable-select"><label>Bridal trial status</label><select value={draft.bridalTrialStatus} onChange={(event) => update("bridalTrialStatus", event.target.value)}>{Object.entries(TRIAL_STATUS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
          ) : <Detail label="Bridal trial status" value={TRIAL_STATUS[draft.bridalTrialStatus]} />}
        </div>
        <TrialBoard status={draft.bridalTrialStatus} onChange={(value) => update("bridalTrialStatus", value)} />
        <div className="party-member-list">
          <div className="party-member-heading grouped-party-heading">
            <strong>Type</strong><strong>Style</strong><strong>Assistant</strong>
          </div>
          {(draft.partyMembers || []).map((member, index) => (
            <div className="party-member-row" key={member.id || `new-${index}`}>
              {editingSection === "wedding" ? (
                <select
                  value={member.role}
                  onChange={(event) =>
                    setDraft((item) => ({
                      ...item,
                      partyMembers: item.partyMembers.map((old, oldIndex) =>
                        oldIndex === index ? { ...old, role: event.target.value } : old,
                      ),
                    }))
                  }
                >
                  {Object.entries(PARTY_ROLE).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              ) : <span>{PARTY_ROLE[member.role] || "Other"}</span>}
              {editingSection === "wedding" ? (
                <select
                  value={member.hairstyle}
                  onChange={(event) =>
                    setDraft((item) => ({
                      ...item,
                      partyMembers: item.partyMembers.map((old, oldIndex) =>
                        oldIndex === index ? { ...old, hairstyle: event.target.value } : old,
                      ),
                    }))
                  }
                >
                  {Object.entries(HAIRSTYLE).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              ) : <span>{HAIRSTYLE[member.hairstyle]}</span>}
              <label className="assistant-checkbox">
                <input type="checkbox" checked={Boolean(member.assistant)} disabled={editingSection !== "wedding"} onChange={(event) => setDraft((item) => ({ ...item, partyMembers: item.partyMembers.map((old, oldIndex) => oldIndex === index ? { ...old, assistant: event.target.checked } : old) }))} />
                Assistant
              </label>
            </div>
          ))}
          {!draft.partyMembers?.length && <p className="muted">No party members added.</p>}
        </div>
      </section>

      <section className="profile-section">
        <div className="profile-section-title">
          <span className="section-number peach-number">02</span>
          <div><p className="eyebrow">Client information</p><h2>Additional details</h2></div>
          {editingSection === "additional" ? <div className="section-actions"><button className="profile-save" onClick={save} disabled={saving}>{saving ? "Saving…" : "Save"}</button><button className="profile-cancel" onClick={() => { setDraft(wedding); setEditingSection(null); }}>Cancel</button></div> : <button className="profile-save" onClick={() => setEditingSection("additional")}>Edit</button>}
        </div>
        <div className="detail-grid">
          {editingSection === "additional" ? <Editable label="Source" value={draft.source} onChange={(value) => update("source", value)} /> : <Detail label="Source" value={draft.source} />}
          {editingSection === "additional" ? <Editable label="Social media" value={draft.socialMedia} onChange={(value) => update("socialMedia", value)} /> : <Detail label="Social media" value={draft.socialMedia} />}
          {editingSection === "additional" ? <Editable label="Referral name" value={draft.referralName} onChange={(value) => update("referralName", value)} /> : <Detail label="Referral name" value={draft.referralName} />}
          {editingSection === "additional" ? (
            <SelectField
              label="Planning stage"
              value={draft.planningStage}
              onChange={(value) => update("planningStage", value)}
              options={[
                ["looking", "Just looking around"],
                ["invoice", "Love your work — send pricing info"],
                ["book", "So excited to book!"],
              ]}
            />
          ) : <Detail label="Planning stage" value={draft.planningStage} />}
          {editingSection === "additional" ? (
            <BooleanField
              label="Interested in makeup"
              value={draft.makeupInterest}
              onChange={(value) => update("makeupInterest", value)}
            />
          ) : <Detail label="Interested in makeup" value={draft.makeupInterest == null ? "Not specified" : draft.makeupInterest ? "Yes" : "No"} />}
          {editingSection === "additional" ? (
            <BooleanField
              label="Recommendations if unavailable"
              value={draft.recommendationsIfUnavailable}
              onChange={(value) => update("recommendationsIfUnavailable", value)}
            />
          ) : <Detail label="Recommendations if unavailable" value={draft.recommendationsIfUnavailable == null ? "Not specified" : draft.recommendationsIfUnavailable ? "Yes" : "No"} />}
        </div>
        {editingSection === "additional" ? <label className="notes-label">Notes<textarea value={draft.notes || ""} onChange={(event) => update("notes", event.target.value)} /></label> : <Detail label="Notes" value={draft.notes} />}
      </section>
      </main>
    </div>
  );
}

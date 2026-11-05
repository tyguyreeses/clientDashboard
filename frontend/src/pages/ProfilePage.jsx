import { useEffect, useState } from "react";
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
const TRIAL_PROGRESS_COLORS = ["var(--coral)", "#e6ba62", "#a6aa5a", "#4d9a6d"];

function TrialBoard({ status, onChange }) {
  if (["not_interested", "cancelled"].includes(status)) return null;
  const currentIndex = Math.max(0, TRIAL_STEPS.indexOf(status));
  return (
    <div className="trial-kanban">
      <div className="trial-kanban-label">Bridal trial status</div>
      <div className="trial-kanban-columns">
        {TRIAL_STEPS.map((step) => (
          <button type="button" className={`trial-step ${status === step ? "active" : ""}`} key={step} onClick={() => onChange(step)}>
            {TRIAL_STATUS[step]}
          </button>
        ))}
      </div>
      <div className="trial-progress" aria-label={`Bridal trial progress: ${TRIAL_STATUS[status]}`}>
        <div className="trial-progress-fill" style={{ width: `${((currentIndex + 1) / TRIAL_STEPS.length) * 100}%`, backgroundColor: TRIAL_PROGRESS_COLORS[currentIndex] }} />
      </div>
    </div>
  );
}

function InvoiceSummary({ wedding, invoice, invoiceWarnings, assistantReceipt, pricingVersions, invoiceLoading, copied, onGenerate, onCopy }) {
  if (!invoice) {
    return <section className="profile-section invoice-section"><div className="profile-section-title"><span className="section-number mint-number">03</span><div><p className="eyebrow">Billing</p><h2>Invoice</h2></div></div><p className="muted">No invoice has been generated yet.</p><button className="profile-save" onClick={() => onGenerate()} disabled={invoiceLoading}>Generate invoice</button></section>;
  }
  return <section className="profile-section invoice-section">
    <div className="profile-section-title"><span className="section-number mint-number">03</span><div><p className="eyebrow">Billing</p><h2>Invoice summary</h2></div><button className="profile-save" onClick={() => onGenerate(invoice.pricing_version_id)} disabled={invoiceLoading}>{invoiceLoading ? "Generating…" : "Regenerate invoice"}</button></div>
    <div className="invoice-controls"><label>Pricing version<select value={invoice.pricing_version_id} disabled={invoiceLoading} onChange={(event) => onGenerate(Number(event.target.value))}>{pricingVersions.map((version) => <option key={version.id} value={version.id}>{version.name}</option>)}</select></label><button className="profile-save" onClick={onCopy}>{copied ? "Copied" : "Copy invoice message"}</button></div>
    {(invoiceWarnings?.length > 0 || invoice.warnings?.length > 0) && <div className="invoice-warnings"><strong>Invoice warnings</strong>{[...(invoiceWarnings || []), ...(invoice.warnings || [])].map((warning, index) => <div key={`${warning}-${index}`}>{warning}</div>)}</div>}
    <div className="invoice-details">
      <strong>{wedding.name}</strong>
      <span>Wedding date: {formatDate(wedding.weddingDate)}</span>
      <span>Address: {wedding.address || "—"}</span>
      {wedding.city && <span>City: {wedding.city}</span>}
      {wedding.venue && <span>Venue: {wedding.venue}</span>}
    </div>
    <div className="invoice-meta"><span>Ready by {invoice.timing_details?.ready_by || "—"}</span><span>Start at {invoice.timing_details?.start_time || "—"}</span><span>{invoice.timing_details?.service_minutes || 0} minutes</span></div>
    <div className="invoice-durations">Service durations: bride {invoice.timing_details?.service_durations?.bride || 0} min · updo {invoice.timing_details?.service_durations?.bridal_party_updo || 0} min · down {invoice.timing_details?.service_durations?.bridal_party_down || 0} min · flower girl {invoice.timing_details?.service_durations?.flowergirl || 0} min</div>
    <div className="invoice-lines">{invoice.line_items.map((item, index) => <div className="invoice-line" key={`${item.description}-${index}`}><span>{item.description} × {item.quantity}</span><strong>${item.total}</strong></div>)}</div>
    <div className="invoice-total-row"><span>Total</span><strong>${invoice.grand_total}</strong></div>
    <div className="invoice-balance"><span>Non-refundable deposit: ${invoice.deposit_amount}</span><span>Remaining balance: ${invoice.balance_due}</span><span>Balance due date: {formatDate(invoice.timing_details?.balance_due_date || wedding.weddingDate)}</span></div>
    {assistantReceipt && <div className="assistant-receipt"><h3>Assistant receipt</h3><div>Total paid to assistant: ${assistantReceipt.total_paid_to_assistant}</div><div>Assisted bridal-party members: {assistantReceipt.assisted_bridesmaid_count}</div></div>}
  </section>;
}

export function ProfilePage({ wedding, onClose, onSaved }) {
  const [draft, setDraft] = useState(wedding);
  const [editingSection, setEditingSection] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [invoice, setInvoice] = useState(null);
  const [assistantReceipt, setAssistantReceipt] = useState(null);
  const [pricingVersions, setPricingVersions] = useState([]);
  const [invoiceLoading, setInvoiceLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [invoiceWarnings, setInvoiceWarnings] = useState([]);
  const update = (field, value) =>
    setDraft((item) => ({ ...item, [field]: value }));
  const loadInvoiceData = async () => {
    setInvoiceLoading(true);
    try {
      const [currentInvoice, versions] = await Promise.all([
        json(`/weddings/${wedding.id}/invoice`).catch((err) => {
          if (err.status === 404) return null;
          throw err;
        }),
        json("/pricing-versions"),
      ]);
      setInvoice(currentInvoice);
      setAssistantReceipt(currentInvoice ? await json(`/invoices/${currentInvoice.id}/assistant-receipt`).catch(() => null) : null);
      setPricingVersions(versions);
    } catch (err) {
      setError(err.message);
    } finally {
      setInvoiceLoading(false);
    }
  };

  useEffect(() => { loadInvoiceData(); }, [wedding.id]);

  const generateInvoice = async (pricingVersionId = invoice?.pricing_version_id) => {
    setInvoiceLoading(true);
    setError("");
    try {
      const result = await json(`/weddings/${wedding.id}/invoice`, {
        method: "POST",
        body: JSON.stringify({ pricing_version_id: pricingVersionId || null }),
      });
      setInvoice(result.invoice);
      setAssistantReceipt(await json(`/invoices/${result.invoice.id}/assistant-receipt`).catch(() => null));
    } catch (err) {
      setError(err.message);
    } finally {
      setInvoiceLoading(false);
    }
  };

  const copyInvoiceMessage = async () => {
    if (!invoice?.message_text) return;
    try {
      await navigator.clipboard.writeText(invoice.message_text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setError("Unable to copy the invoice message. Check browser clipboard permissions.");
    }
  };

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
            is_referral: Boolean(draft.isReferral),
            notes: draft.notes || null,
          }),
        }),
        json(`/weddings/${draft.id}`, {
          method: "PATCH",
          body: JSON.stringify({
            wedding_date: draft.weddingDate,
            address: draft.address || "",
            city: draft.city || null,
            venue: draft.venue || null,
            miles_one_way: draft.miles ?? null,
            ready_by: draft.readyBy === "Time TBD" ? null : (draft.readyBy || null),
            status: Number(draft.status),
            bridal_trial_status: draft.bridalTrialStatus,
          }),
        }),
      ]);
      const members = draft.partyMembers || [];
      const updatedMembers = await Promise.all(
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
      setInvoiceWarnings([
        ...(client.invoice_warnings || []),
        ...(updatedWedding.invoice_warnings || []),
        ...updatedMembers.flatMap((member) => member.invoice_warnings || []),
      ]);
      await loadInvoiceData();
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
          <button className="profile-save invoice-action" onClick={() => generateInvoice()} disabled={invoiceLoading}>
            {invoiceLoading ? "Generating…" : invoice ? "Regenerate invoice" : "Generate invoice"}
          </button>
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
            <Editable label="Address" value={draft.address} onChange={(value) => update("address", value)} required />
          ) : <Detail label="Address" value={draft.address} />}
          {editingSection === "wedding" ? (
            <Editable label="City" value={draft.city} onChange={(value) => update("city", value)} />
          ) : <Detail label="City" value={draft.city} />}
          {editingSection === "wedding" ? (
            <Editable label="Venue" value={draft.venue} onChange={(value) => update("venue", value)} />
          ) : <Detail label="Venue" value={draft.venue} />}
          {editingSection === "wedding" ? (
            <Editable label="Ready-by time" type="time" step={15 * 60} min="01:00" max="12:00" value={draft.readyBy} onChange={(value) => update("readyBy", value)} />
          ) : <Detail label="Ready by" value={draft.readyBy} />}
          {editingSection === "wedding" ? (
            <div className="editable-select"><label>Workflow status</label><select value={draft.status} onChange={(event) => update("status", event.target.value)}>{Object.entries(STATUS).map(([value, option]) => <option key={value} value={value}>{option.label}</option>)}</select></div>
          ) : <Detail label="Workflow status" value={STATUS[draft.status]?.label} />}
          {editingSection === "wedding" && (
            <div className="editable-select"><label>Bridal trial status</label><select value={draft.bridalTrialStatus} onChange={(event) => update("bridalTrialStatus", event.target.value)}>{Object.entries(TRIAL_STATUS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
          )}
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

      <InvoiceSummary
        wedding={draft}
        invoice={invoice}
        invoiceWarnings={invoiceWarnings}
        assistantReceipt={assistantReceipt}
        pricingVersions={pricingVersions}
        invoiceLoading={invoiceLoading}
        copied={copied}
        onGenerate={generateInvoice}
        onCopy={copyInvoiceMessage}
      />

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
          {editingSection === "additional" ? <BooleanField label="Referral discount" value={draft.isReferral} onChange={(value) => update("isReferral", value)} /> : <Detail label="Referral discount" value={draft.isReferral ? "Yes" : "No"} />}
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

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const STATUS = {
  0: { label: "Cancelled", tone: "cancelled" },
  1: { label: "Inquired", tone: "inquired" },
  2: { label: "Invoice sent", tone: "responded" },
  3: { label: "Awaiting deposit", tone: "awaiting" },
  4: { label: "Deposit received", tone: "booked" },
  5: { label: "Paid in full", tone: "paid" },
  6: { label: "Completed", tone: "completed" },
};

export const PARTY_ROLE = {
  B: "Bride",
  P: "Bridal Party",
  F: "Flower Girl",
  M: "MOB",
  O: "Other",
  J: "Other",
};

export const HAIRSTYLE = {
  U: "Updo",
  D: "Half up",
};

export const TRIAL_STATUS = {
  not_interested: "Not interested",
  interested: "Interested",
  link_sent: "Link sent",
  booked: "Booked",
  complete: "Complete",
  cancelled: "Cancelled",
};

export const json = async (path, options = {}) => {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.status === 204 ? null : response.json();
};

export const formatDate = (value) =>
  value
    ? new Intl.DateTimeFormat("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      }).format(new Date(`${value}T12:00:00`))
    : "No date";

export const formatDateTime = (value) =>
  value
    ? new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value))
    : "";

export const formatMoney = (value) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));

export const initials = (name = "") =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

export const timeLabel = (value) => (value ? value.slice(0, 5) : "Time TBD");

export function weddingView(wedding) {
  const client = wedding.client || {};
  return {
    ...wedding,
    clientId: wedding.client_id,
    name: client.name || "Unnamed client",
    email: client.email || "",
    phone: client.phone || "",
    source: client.source || "Unknown source",
    socialMedia: client.social_media || "",
    inquiryDate: client.inquiry_date,
    planningStage: client.planning_stage || "",
    makeupInterest: client.makeup_interest,
    recommendationsIfUnavailable: client.recommendations_if_unavailable,
    referralName: client.referral_name || "",
    notes: client.notes || "",
    initials: initials(client.name),
    weddingDate: wedding.wedding_date,
    invoiceSentAt: wedding.invoice_sent_at,
    readyBy: timeLabel(wedding.ready_by),
    location: wedding.location || "Location TBD",
    miles: wedding.miles_one_way,
    partyMembers: wedding.party_members || [],
    people: (wedding.party_members || []).length,
    bridalTrialStatus: wedding.bridal_trial_status,
    balance: 0,
    paid: "No payment recorded",
    party: `${(wedding.party_members || []).length} party members`,
  };
}

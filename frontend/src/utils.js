const API_URL = "/api/admin";
let csrfToken = "";

export const setCsrfToken = (token) => { csrfToken = token || ""; };

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
    headers: {
      "Content-Type": "application/json",
      ...(options.method && options.method !== "GET" ? { "X-CSRF-Token": csrfToken } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = Array.isArray(body.detail)
      ? body.detail.map((item) => `${item.loc?.at(-1) || "field"}: ${item.msg}`).join("; ")
      : body.detail;
    const error = new Error(detail || `Request failed (${response.status})`);
    error.status = response.status;
    throw error;
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

export const formatDistance = (value) =>
  value == null || value === "" ? "Not specified" : Number(value).toString();

export const initials = (name = "") =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

export const formatPhone = (value = "") => {
  let digits = String(value).replace(/\D/g, "");
  if (digits.length === 11 && digits.startsWith("1")) digits = digits.slice(1);
  digits = digits.slice(0, 10);
  if (!digits) return "";
  if (digits.length <= 3) return `(${digits}`;
  if (digits.length <= 6) return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
  return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
};

export const formatTime = (value) => {
  if (!value) return "Time TBD";
  const [hours, minutes] = value.slice(0, 5).split(":").map(Number);
  const suffix = hours >= 12 ? "PM" : "AM";
  const displayHour = hours % 12 || 12;
  return `${displayHour}:${String(minutes).padStart(2, "0")} ${suffix}`;
};

export const timeLabel = (value) => formatTime(value);

export const timeSince = (value) => {
  if (!value) return "Inquiry date unknown";
  const rawValue = String(value);
  const inquiry = new Date(rawValue.includes("T") ? rawValue : `${rawValue}T00:00:00`);
  const today = new Date();
  inquiry.setHours(0, 0, 0, 0);
  today.setHours(0, 0, 0, 0);
  const days = Math.max(0, Math.floor((today - inquiry) / 86400000));
  if (days === 0) return "Today";
  if (days === 1) return "1 day ago";
  if (days < 7) return `${days} days ago`;
  const weeks = Math.floor(days / 7);
  if (weeks === 1) return "1 week ago";
  if (weeks < 5) return `${weeks} weeks ago`;
  const months = Math.floor(days / 30);
  if (months === 1) return "1 month ago";
  return `${months} months ago`;
};

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
    isReferral: Boolean(client.is_referral),
    archived: Boolean(client.archived),
    notes: client.notes || "",
    initials: initials(client.name),
    weddingDate: wedding.wedding_date,
    invoiceSentAt: wedding.invoice_sent_at,
    statusProgress: wedding.status_progress || [],
    statusEnteredAt: (wedding.status_progress || []).find((entry) => entry.status === wedding.status)?.forward_entered_at || wedding.updated_at,
    readyBy: wedding.ready_by ? wedding.ready_by.slice(0, 5) : "",
    readyByLabel: formatTime(wedding.ready_by),
    address: wedding.address || "",
    city: wedding.city || "",
    venue: wedding.venue || "",
    miles: wedding.miles_one_way == null ? null : Number(wedding.miles_one_way),
    partyMembers: wedding.party_members || [],
    people: (wedding.party_members || []).length,
    bridalTrialStatus: wedding.bridal_trial_status,
    balance: 0,
    paid: "No payment recorded",
    party: `${(wedding.party_members || []).length} party members`,
  };
}

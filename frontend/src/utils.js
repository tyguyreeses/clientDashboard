const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const STATUS = {
  0: { label: "Cancelled", tone: "cancelled" },
  1: { label: "Inquired", tone: "inquired" },
  2: { label: "Responded", tone: "responded" },
  3: { label: "Awaiting deposit", tone: "awaiting" },
  4: { label: "Deposit received", tone: "booked" },
};

export const TRIAL_STATUS = {
  not_interested: "Not interested",
  interested: "Interested",
  link_sent: "Link sent",
  booked: "Booked",
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
    notes: client.notes || "",
    initials: initials(client.name),
    weddingDate: wedding.wedding_date,
    readyBy: timeLabel(wedding.ready_by),
    location: wedding.location || "Location TBD",
    miles: wedding.miles_one_way,
    people: (wedding.party_members || []).reduce(
      (sum, member) =>
        sum + member.by_me_quantity + member.by_assistant_quantity,
      0,
    ),
    bridalTrialStatus: wedding.bridal_trial_status,
    balance: 0,
    paid: "No payment recorded",
    party: `${(wedding.party_members || []).length} party members`,
  };
}

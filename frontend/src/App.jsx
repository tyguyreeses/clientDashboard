import { useEffect, useMemo, useState } from "react";
import { AddClientModal } from "./components/AddClientModal";
import { Footer, Header } from "./components/Layout";
import { HistoryPage } from "./pages/HistoryPage";
import { ProfilePage } from "./pages/ProfilePage";
import { PricingPage } from "./pages/PricingPage";
import { BookingRate, KanbanBoard, Stat } from "./components/WeddingBoard";
import { initials, json, weddingView } from "./utils";

export function App({ user }) {
  const [weddings, setWeddings] = useState([]);
  const [clients, setClients] = useState([]);
  const [selected, setSelected] = useState(null);
  const [page, setPage] = useState("dashboard");
  const [showAddClient, setShowAddClient] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revenueToDate, setRevenueToDate] = useState(0);

  const loadData = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    setError("");
    try {
      const [clientData, weddingData] = await Promise.all([
        json("/clients"),
        json("/weddings"),
      ]);
      setClients(clientData);
      const weddingViews = weddingData.map(weddingView);
      setWeddings(weddingViews);
      const today = new Date().toISOString().slice(0, 10);
      const currentYear = today.slice(0, 4);
      const revenueItems = weddingViews.filter(
        (wedding) => wedding.status >= 4 || wedding.bridalTrialStatus === "complete",
      );
      const invoices = await Promise.all(
        revenueItems.map(async (wedding) => {
          try {
            return await json(`/weddings/${wedding.id}/invoice`);
          } catch {
            return null;
          }
        }),
      );
      const revenue = invoices.reduce((total, invoice, index) => {
        if (!invoice) return total;
        const wedding = revenueItems[index];
        const invoiceAmount = wedding.status >= 5
          ? Number(invoice.grand_total || 0)
          : Number(invoice.deposit_amount || 0);
        const trialAmount = wedding.bridalTrialStatus === "complete"
          ? Number(invoice.pricing_version?.trial_price || 0)
          : 0;
        return total + invoiceAmount + trialAmount;
      }, 0);
      setRevenueToDate(revenue);
    } catch (err) {
      setError(`${err.message}. Is the FastAPI server running on port 8000?`);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    loadData();
  }, []);
  const openWedding = async (wedding) => {
    try {
      const detail = await json(`/weddings/${wedding.id}`);
      setSelected(weddingView(detail));
    } catch (err) {
      setError(err.message);
    }
  };

  const updateStatus = async (weddingOrId, status) => {
    const wedding = typeof weddingOrId === "object" ? weddingOrId : weddings.find((item) => item.id === Number(weddingOrId));
    if (!wedding) return;
    setWeddings((items) => items.map((item) => (
      item.id === wedding.id ? { ...item, status: Number(status) } : item
    )));
    try {
      const updated = await json(`/weddings/${wedding.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: Number(status) }),
      });
      setWeddings((items) =>
        items.map((item) =>
          item.id === wedding.id
            ? weddingView({
                ...updated,
                client: updated.client || {
                  name: item.name,
                  email: item.email,
                  phone: item.phone,
                  source: item.source,
                  notes: item.notes,
                },
              })
            : item,
        ),
      );
      await loadData(false);
    } catch (err) {
      setError(err.message);
      await loadData(false);
    }
  };
  const groups = useMemo(() => {
    const columns = [[1, "Inquired", "coral"], [2, "Invoice sent", "peach"], [3, "Awaiting deposit", "butter"], [4, "Deposit received", "mint"], [5, "Paid in full", "lilac"]];
    return columns.map(([status, label, color]) => ({
      key: label,
      status,
      label,
      color,
      items: weddings.filter((item) => item.status === status).sort((a, b) => String(a.statusEnteredAt || "").localeCompare(String(b.statusEnteredAt || ""))),
    }));
  }, [weddings]);
  const today = new Date().toISOString().slice(0, 10);
  const currentYear = today.slice(0, 4);
  const inquiriesToDate = clients.filter((client) => {
    const inquiryDate = String(client.inquiryDate || client.inquiry_date || "").slice(0, 10);
    return inquiryDate.startsWith(currentYear) && inquiryDate <= today;
  }).length;
  const bookedToDate = weddings.filter((wedding) => wedding.status >= 4 && wedding.status <= 6).length;
  const bookingPercentage = inquiriesToDate ? Math.round((bookedToDate / inquiriesToDate) * 100) : 0;
  return (
    <div className="app-shell">
      <Header
        user={user}
        page={page}
        onNavigate={(next) => {
          setSelected(null);
          setPage(next);
        }}
        onAddClient={() => setShowAddClient(true)}
      />
      <div className="brand-banner" aria-label="Hair By Maddie banner">
        <img src="/logo_banner.PNG" alt="Hair By Maddie · Bridal Hairstylist" />
      </div>
      <>
        {selected && (
        <ProfilePage
          wedding={selected}
          onClose={() => setSelected(null)}
          onSaved={(item) => {
            setWeddings((items) =>
              items.map((old) => (old.id === item.id ? item : old)),
            );
            setClients((items) =>
              items.map((old) =>
                old.id === item.clientId
                  ? {
                      ...old,
                      name: item.name,
                      email: item.email,
                      phone: item.phone,
                      inquiry_date: item.inquiryDate,
                      source: item.source,
                      social_media: item.socialMedia,
                      planning_stage: item.planningStage,
                      makeup_interest: item.makeupInterest,
                      recommendations_if_unavailable:
                        item.recommendationsIfUnavailable,
                      referral_name: item.referralName,
                      is_referral: item.isReferral,
                      notes: item.notes,
                    }
                  : old,
              ),
            );
            setSelected(item);
            loadData(false);
          }}
        />
        )}
        {page === "history" ? (
        <HistoryPage onSelect={openWedding} />
      ) : page === "pricing" ? (
        <PricingPage />
      ) : (
        <main className="dashboard">
          <div className="welcome-row">
            <div>
              <h1>Dashboard</h1>
            </div>
            <div className="dashboard-date">
              <span className="sun-dot" />{" "}
              {new Date().toLocaleDateString("en-US", {
                month: "long",
                day: "numeric",
                year: "numeric",
              })}
            </div>
          </div>
          {error && (
            <div className="api-message error">
              {error} <button onClick={loadData}>Retry</button>
            </div>
          )}
          <div className="stats-row">
            <Stat
              label="Inquiries to date"
              value={inquiriesToDate}
              accent="coral"
            />
            <Stat
              label="Booked to date"
              value={bookedToDate}
              accent="peach"
            />
            <BookingRate percentage={bookingPercentage} />
            <Stat
              label="Revenue to date"
              value={`$${revenueToDate.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
              accent="lavender"
            />
          </div>
          <div className="board-toolbar">
            <div>
              <strong>Wedding board</strong>
            </div>
            <button
              className="add-button"
              onClick={() => setShowAddClient(true)}
            >
              ＋ Add client
            </button>
          </div>
          {loading ? (
            <div className="loading-state">Loading…</div>
          ) : (
            <div className="board">
              <KanbanBoard groups={groups} onSelect={openWedding} onStatus={updateStatus} />
            </div>
          )}
          <div className="client-strip">
            <div>
              <h2>Clients</h2>
            </div>
            <div className="client-chips">
              {clients.slice(0, 8).map((client) => (
                <button
                  className="client-chip"
                  key={client.id}
                  onClick={() => {
                    const wedding = weddings.find((item) => item.clientId === client.id);
                    if (wedding) openWedding(wedding);
                  }}
                >
                  <b>{initials(client.name)}</b>
                  {client.name}
                </button>
              ))}
              {!clients.length && (
                <span className="muted">No clients yet.</span>
              )}
            </div>
          </div>
        </main>
        )}
      </>
      <Footer />
      {showAddClient && (
        <AddClientModal
          onClose={() => setShowAddClient(false)}
          onCreated={(client, wedding) => {
            setClients((items) =>
              [...items, client].sort((a, b) => a.name.localeCompare(b.name)),
            );
            setWeddings((items) => [...items, weddingView(wedding)]);
            setShowAddClient(false);
            setNotice(`${client.name} and their inquiry were added`);
          }}
        />
      )}
    </div>
  );
}

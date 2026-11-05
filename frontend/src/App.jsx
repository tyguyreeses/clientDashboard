import { useEffect, useMemo, useState } from "react";
import { AddClientModal } from "./components/AddClientModal";
import { Footer, Header } from "./components/Layout";
import { HistoryPage } from "./pages/HistoryPage";
import { ProfilePage } from "./pages/ProfilePage";
import { KanbanBoard, Stat } from "./components/WeddingBoard";
import { initials, json, weddingView } from "./utils";

export function App() {
  const [weddings, setWeddings] = useState([]);
  const [clients, setClients] = useState([]);
  const [selected, setSelected] = useState(null);
  const [page, setPage] = useState("dashboard");
  const [showAddClient, setShowAddClient] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadData = async () => {
    setLoading(true);
    setError("");
    try {
      const [clientData, weddingData] = await Promise.all([
        json("/clients"),
        json("/weddings"),
      ]);
      setClients(clientData);
      setWeddings(weddingData.map(weddingView));
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
      setNotice("Status saved");
    } catch (err) {
      setError(err.message);
    }
  };
  const groups = useMemo(() => {
    const columns = [[1, "Inquired", "coral"], [2, "Invoice sent", "peach"], [3, "Awaiting deposit", "butter"], [4, "Deposit received", "mint"], [5, "Paid in full", "lilac"]];
    return columns.map(([status, label, color]) => ({
      key: label,
      status,
      label,
      color,
      items: weddings.filter((item) => item.status === status).sort((a, b) => a.weddingDate.localeCompare(b.weddingDate)),
    }));
  }, [weddings]);
  return (
    <div className="app-shell">
      <Header
        page={page}
        onNavigate={(next) => {
          setSelected(null);
          setPage(next);
        }}
        onAddClient={() => setShowAddClient(true)}
      />
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
          }}
        />
        )}
        {page === "history" ? (
        <HistoryPage onSelect={openWedding} />
      ) : (
        <main className="dashboard">
          <div className="welcome-row">
            <div>
              <h1>
                Dashboard <span className="wave">✦</span>
              </h1>
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
          {notice && <div className="api-message success">{notice}</div>}
          <div className="stats-row">
            <Stat
              label="Upcoming celebrations"
              value={weddings.filter((item) => item.status === 4).length}
              accent="peach"
            />
            <Stat
              label="Awaiting a deposit"
              value={weddings.filter((item) => item.status === 3).length}
              accent="butter"
            />
            <Stat
              label="Clients in your care"
              value={clients.length}
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

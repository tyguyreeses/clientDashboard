import { useState } from "react";
import { ClientDetails } from "./ClientDetails";
import { initials } from "../utils";

export function ClientsPage({
  clients,
  weddings,
  onAddClient,
  onSaved,
  onArchived,
}) {
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const filtered = clients.filter((client) =>
    `${client.name} ${client.email || ""} ${client.phone || ""}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  const selected = clients.find((client) => client.id === selectedId);
  return (
    <main className="clients-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Clients</p>
          <h1>Client directory</h1>
        </div>
        <button className="add-button" onClick={onAddClient}>
          ＋ Add client
        </button>
      </div>
      <div className="client-layout">
        <section className="client-list-card">
          <input
            className="client-search"
            placeholder="Search clients"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          {filtered.length ? (
            filtered.map((client) => (
              <button
                className={`client-list-row ${selectedId === client.id ? "selected" : ""}`}
                key={client.id}
                onClick={() => setSelectedId(client.id)}
              >
                <span className="initials">{initials(client.name)}</span>
                <span>
                  <strong>{client.name}</strong>
                  <small>
                    {client.email || client.phone || "No contact details"}
                  </small>
                </span>
                <span className="client-row-arrow">›</span>
              </button>
            ))
          ) : (
            <div className="empty-row">No clients.</div>
          )}
        </section>
        {selected ? (
          <ClientDetails
            client={selected}
            weddings={weddings.filter(
              (wedding) => wedding.clientId === selected.id,
            )}
            onSaved={onSaved}
            onArchived={onArchived}
          />
        ) : (
          <div className="client-empty">
            <span className="large-initials">✦</span>
            <h2>Select a client</h2>
            <p>View and edit client details.</p>
          </div>
        )}
      </div>
    </main>
  );
}

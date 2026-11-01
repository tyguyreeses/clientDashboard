import { useState } from "react";
import { WeddingRow } from "./WeddingRow";

export function Stat({ label, value, accent }) {
  return (
    <div className={`stat-card ${accent}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <b>↗</b>
    </div>
  );
}
export function WeddingSection({ group, onSelect, onStatus }) {
  const [open, setOpen] = useState(true);
  return (
    <section className="wedding-section">
      <button
        className={`section-heading ${group.color}`}
        onClick={() => setOpen(!open)}
      >
        <span className="chevron">{open ? "⌄" : "›"}</span>
        <span className="section-dot" />
        <span className="section-title">{group.label}</span>
        <span className="count">{group.items.length}</span>
        <span className="section-sparkle">✦</span>
      </button>
      {open && (
        <div className="rows">
          {group.items.length ? (
            group.items.map((wedding) => (
              <WeddingRow
                key={wedding.id}
                wedding={wedding}
                onSelect={onSelect}
                onStatus={onStatus}
              />
            ))
          ) : (
            <div className="empty-row">No weddings.</div>
          )}
        </div>
      )}
    </section>
  );
}

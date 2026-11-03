import { useState } from "react";
import { formatDate, STATUS, timeLabel, timeSince } from "../utils";

export function Stat({ label, value, accent }) {
  return <div className={`stat-card ${accent}`}><span>{label}</span><strong>{value}</strong><b>↗</b></div>;
}

function WeddingCard({ wedding, onSelect, onDragStart, onDragEnd }) {
  return (
    <article
      className="kanban-card"
      draggable
      onDragStart={(event) => { event.dataTransfer.effectAllowed = "move"; event.dataTransfer.setData("wedding-id", String(wedding.id)); onDragStart(wedding); }}
      onDragEnd={onDragEnd}
      onClick={() => onSelect(wedding)}
    >
      <div className="kanban-card-top"><strong>{wedding.name}</strong><small>{timeSince(wedding.inquiryDate)}</small></div>
      <span>{formatDate(wedding.weddingDate)}</span>
      <span>{wedding.people || 0} people · {wedding.location}</span>
    </article>
  );
}

export function WeddingSection({ group, onSelect, onStatus, onDragStart, onDragEnd }) {
  const [over, setOver] = useState(false);
  return (
    <section className={`kanban-column ${group.color} ${over ? "drag-over" : ""}`} onDragOver={(event) => { event.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={(event) => { event.preventDefault(); setOver(false); onStatus(event.dataTransfer.getData("wedding-id"), group.status); }}>
      <header className="kanban-column-heading"><span className="section-dot" /><strong>{group.label}</strong><span className="count">{group.items.length}</span></header>
      <div className="kanban-cards">
        {group.items.map((wedding) => <WeddingCard key={wedding.id} wedding={wedding} onSelect={onSelect} onDragStart={onDragStart} onDragEnd={onDragEnd} />)}
        {!group.items.length && <div className="kanban-empty">Drop weddings here</div>}
      </div>
    </section>
  );
}

export function KanbanBoard({ groups, onSelect, onStatus }) {
  const [dragging, setDragging] = useState(null);
  const [dropTarget, setDropTarget] = useState(null);
  const finish = (status) => { if (dragging) onStatus(dragging.id, status); setDragging(null); setDropTarget(null); };
  const start = (wedding) => { setDragging(wedding); };
  return (
    <>
      <div className="kanban-board">
        {groups.map((group) => <WeddingSection key={group.key} group={group} onSelect={onSelect} onStatus={(id, status) => onStatus(id, status)} onDragStart={start} onDragEnd={() => { setDragging(null); setDropTarget(null); }} />)}
      </div>
      {dragging && <div className="drag-actions"><button className={`drag-cancel ${dropTarget === "cancel" ? "drag-target" : ""}`} onDragEnter={() => setDropTarget("cancel")} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); finish(0); }}>Cancel</button><button className={`drag-complete ${dropTarget === "complete" ? "drag-target" : ""}`} onDragEnter={() => setDropTarget("complete")} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); finish(6); }}>Completed</button></div>}
    </>
  );
}

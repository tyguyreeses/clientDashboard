import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { formatDate, STATUS, timeLabel, timeSince } from "../utils";

export function Stat({ label, value, accent }) {
  return <div className={`stat-card ${accent}`}><span>{label}</span><strong>{value}</strong><b>↗</b></div>;
}

const BOOKING_PROGRESS_STOPS = [
  [0, [165, 91, 91]],
  [0.20, [230, 186, 98]],
  [0.40, [166, 170, 90]],
  [0.60, [57, 118, 92]],
];

function bookingProgressColor(percentage) {
  const position = percentage / 100;
  const upperIndex = BOOKING_PROGRESS_STOPS.findIndex(([stop]) => position <= stop);
  const resolvedUpperIndex = upperIndex === -1 ? BOOKING_PROGRESS_STOPS.length - 1 : upperIndex;
  const lowerIndex = Math.max(0, resolvedUpperIndex - 1);
  const [lowerStop, lowerColor] = BOOKING_PROGRESS_STOPS[lowerIndex];
  const [upperStop, upperColor] = BOOKING_PROGRESS_STOPS[resolvedUpperIndex];
  const range = upperStop - lowerStop || 1;
  const ratio = Math.max(0, Math.min(1, (position - lowerStop) / range));
  const color = lowerColor.map((channel, index) => Math.round(channel + (upperColor[index] - channel) * ratio));
  return `rgb(${color.join(", ")})`;
}

export function BookingRate({ percentage }) {
  const displayPercentage = Math.min(100, percentage);
  return <div className="stat-card booking-rate-card"><span>Booking percentage to date</span><div className="booking-rate-circle" style={{ "--booking-percentage": `${displayPercentage}%`, "--booking-progress-color": bookingProgressColor(displayPercentage) }}><strong>{displayPercentage}%</strong></div></div>;
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
      <div className="kanban-card-top"><strong>{wedding.name}</strong><small>{timeSince(wedding.statusEnteredAt || wedding.inquiryDate)}</small></div>
      <span>{formatDate(wedding.weddingDate)}</span>
      <span>{wedding.people || 0} people · {wedding.address}</span>
    </article>
  );
}

export function WeddingSection({ group, onSelect, onStatus, onHover, onDragStart, onDragEnd }) {
  const [over, setOver] = useState(false);
  return (
    <section className={`kanban-column ${group.color} ${over ? "drag-over" : ""}`} onDragOver={(event) => { event.preventDefault(); setOver(true); onHover(group.status); }} onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) { setOver(false); onHover(null); } }} onDrop={(event) => { event.preventDefault(); setOver(false); onHover(null); onStatus(event.dataTransfer.getData("wedding-id"), group.status); }}>
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
  const [hoverStatus, setHoverStatus] = useState(null);
  const [rowHeight, setRowHeight] = useState(null);
  const boardRef = useRef(null);
  useEffect(() => {
    if (!dragging) return undefined;
    const clearDrag = () => {
      setDragging(null);
      setHoverStatus(null);
      setDropTarget(null);
    };
    window.addEventListener("dragend", clearDrag);
    window.addEventListener("drop", clearDrag);
    return () => {
      window.removeEventListener("dragend", clearDrag);
      window.removeEventListener("drop", clearDrag);
    };
  }, [dragging]);
  useLayoutEffect(() => {
    const board = boardRef.current;
    if (!board) return undefined;
    const measure = () => {
      const tallest = Math.max(
        ...Array.from(board.children).map((column) => {
          const heading = column.querySelector(".kanban-column-heading");
          const cards = column.querySelector(".kanban-cards");
          return (heading?.scrollHeight || 0) + (cards?.scrollHeight || 0);
        }),
        360,
      );
      setRowHeight((current) => current === tallest ? current : tallest);
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(board);
    Array.from(board.children).forEach((column) => observer.observe(column));
    return () => observer.disconnect();
  }, [groups, dragging, hoverStatus]);
  const [dropTarget, setDropTarget] = useState(null);
  const finish = (status) => { if (dragging) onStatus(dragging.id, status); setDragging(null); setHoverStatus(null); setDropTarget(null); };
  const start = (wedding) => { setDragging(wedding); };
  const renderedGroups = useMemo(() => {
    if (!dragging || hoverStatus == null) return groups;
    return groups.map((group) => {
      const source = group.items.some((item) => item.id === dragging.id);
      const target = group.status === hoverStatus;
      if (source && target) return group;
      if (source) return { ...group, items: group.items.filter((item) => item.id !== dragging.id) };
      if (target && !group.items.some((item) => item.id === dragging.id)) {
        return {
          ...group,
          items: [...group.items, dragging].sort((a, b) =>
            String(a.statusEnteredAt || "").localeCompare(String(b.statusEnteredAt || "")),
          ),
        };
      }
      return group;
    });
  }, [dragging, groups, hoverStatus]);
  return (
    <>
      <div ref={boardRef} className="kanban-board" style={{ gridTemplateRows: rowHeight ? `${rowHeight}px` : "auto" }}>
        {renderedGroups.map((group) => <WeddingSection key={group.key} group={group} onSelect={onSelect} onStatus={(id, status) => onStatus(id, status)} onHover={setHoverStatus} onDragStart={start} onDragEnd={() => { setDragging(null); setHoverStatus(null); setDropTarget(null); }} />)}
      </div>
      <div className={`drag-actions ${dragging ? "is-visible" : ""}`}><button className={`drag-cancel ${dropTarget === "cancel" ? "drag-target" : ""}`} onDragEnter={() => setDropTarget("cancel")} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); finish(0); }}>Cancel</button><button className={`drag-complete ${dropTarget === "complete" ? "drag-target" : ""}`} onDragEnter={() => setDropTarget("complete")} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); finish(6); }}>Completed</button></div>
    </>
  );
}

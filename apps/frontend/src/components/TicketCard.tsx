import { Link } from "react-router-dom";

import type { TicketListItem } from "../types/ticket";
import { formatRelativeTime, getUrgencyMeta } from "../utils/format";

interface TicketCardProps {
  ticket: TicketListItem;
  selected: boolean;
}

export default function TicketCard({ ticket, selected }: TicketCardProps) {
  const urgency = getUrgencyMeta(ticket.urgency_score);
  const priorityLabel = ticket.priority_label === "uncertain"
    ? "Uncertain"
    : urgency.label;

  return (
    <Link
      className={`ticket-card ${selected ? "is-selected" : ""}`}
      to={`/ticket/${ticket.id}`}
    >
      <div className="ticket-card__topline">
        <span className={`urgency-pill urgency-pill--${ticket.priority_label}`}>
          {priorityLabel}
        </span>
        <span className="ticket-card__time">{formatRelativeTime(ticket.created_at)}</span>
      </div>
      <h3>{ticket.subject || "Untitled support issue"}</h3>
      <p>{ticket.customer_email}</p>
      <div className="ticket-card__meta">
        <span className={`status-badge status-badge--${ticket.status}`}>
          {ticket.status}
        </span>
      </div>
    </Link>
  );
}

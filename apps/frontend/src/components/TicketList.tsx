import { useDeferredValue, useState } from "react";
import { useNavigate } from "react-router-dom";

import type { TicketListItem } from "../types/ticket";
import TicketCard from "./TicketCard";

interface TicketListProps {
  tickets: TicketListItem[];
  selectedId?: string;
  loading: boolean;
  error: string | null;
}

export default function TicketList({
  tickets,
  selectedId,
  loading,
  error,
}: TicketListProps) {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search);
  const normalizedQuery = deferredSearch.trim().toLowerCase();

  const filteredTickets = tickets.filter((ticket) => {
    if (!normalizedQuery) {
      return true;
    }

    return [ticket.subject ?? "", ticket.customer_email, ticket.status]
      .join(" ")
      .toLowerCase()
      .includes(normalizedQuery);
  }).sort((left, right) => {
    if (left.priority_rank !== right.priority_rank) {
      return left.priority_rank - right.priority_rank;
    }

    if (right.urgency_score !== left.urgency_score) {
      return right.urgency_score - left.urgency_score;
    }

    if (left.status === "resolved" && right.status !== "resolved") {
      return 1;
    }

    if (right.status === "resolved" && left.status !== "resolved") {
      return -1;
    }

    return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
  });

  return (
    <section className="panel panel--sidebar">
      <div className="panel__header panel__header--stacked">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
          <div>
            <p className="eyebrow">Queue • En/Ar Support</p>
            <h2>Ticket list</h2>
          </div>
          <button
            className="button button--primary"
            onClick={() => navigate("/")}
            style={{ padding: '6px 12px', fontSize: '0.8rem' }}
            type="button"
          >
            Dashboard
          </button>
        </div>
        <label className="search-field">
          <span>Search / Filters</span>
          <input
            aria-label="Search tickets"
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by subject, email, or status"
            type="search"
            value={search}
          />
        </label>
      </div>

      {loading ? <p className="panel__message">Loading tickets…</p> : null}
      {error ? <p className="panel__message panel__message--error">{error}</p> : null}

      <div className="ticket-list">
        {filteredTickets.map((ticket) => (
          <TicketCard
            key={ticket.id}
            selected={selectedId === ticket.id}
            ticket={ticket}
          />
        ))}
      </div>

      {!loading && filteredTickets.length === 0 ? (
        <p className="panel__message">No tickets match the current search.</p>
      ) : null}
    </section>
  );
}

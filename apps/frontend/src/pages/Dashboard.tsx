import { Link } from "react-router-dom";

import TicketList from "../components/TicketList";
import { useTickets } from "../hooks/useTickets";

export default function Dashboard() {
  const { tickets, loading, error } = useTickets();

  return (
    <div className="app-shell">
      <aside className="app-shell__sidebar">
        <TicketList error={error} loading={loading} tickets={tickets} />
      </aside>

      <main className="app-shell__content">
        <section className="hero-panel">
          <p className="eyebrow">Agent dashboard</p>
          <h1>Decision mode for support operations.</h1>
          <p>
            Review the prioritized queue, open a ticket, inspect the system
            interpretation, and act with the least amount of guesswork.
          </p>

          {tickets.length > 0 ? (
            <Link className="button button--primary hero-panel__cta" to={`/ticket/${tickets[0].id}`}>
              Open highest-visibility ticket
            </Link>
          ) : (
            <span className="hero-panel__empty">
              Tickets will appear here once the backend queue is populated.
            </span>
          )}
        </section>

        <section className="panel panel--placeholder">
          <div className="panel__header">
            <div>
              <p className="eyebrow">Workflow</p>
              <h2>How this dashboard is meant to feel</h2>
            </div>
          </div>

          <div className="placeholder-grid">
            <article>
              <strong>Interpret first</strong>
              <p>
                The system understanding is the source of truth, so the interface
                keeps intent, category, sentiment, and confidence highly visible.
              </p>
            </article>
            <article>
              <strong>Surface gaps clearly</strong>
              <p>
                Missing information is separated from extracted data so agents can
                tell what is known versus what still blocks action.
              </p>
            </article>
            <article>
              <strong>Operate in instruction mode</strong>
              <p>
                The action plan is designed to read like concise operational
                guidance, not a chat transcript.
              </p>
            </article>
          </div>
        </section>
      </main>
    </div>
  );
}

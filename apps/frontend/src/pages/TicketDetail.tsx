import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";

import ActionControls from "../components/ActionControls";
import AgentPanel from "../components/AgentPanel";
import AttachmentViewer from "../components/AttachmentViewer";
import EntityViewer from "../components/EntityViewer";
import TicketList from "../components/TicketList";
import { useTicketDetail } from "../hooks/useTicketDetail";
import { useTickets } from "../hooks/useTickets";
import {
  formatLabel,
  formatPercent,
  formatTimestamp,
  getUrgencyMeta,
  getRtlStyle,
} from "../utils/format";

export default function TicketDetail() {
  const { id } = useParams<{ id: string }>();
  const { tickets, loading: loadingTickets, error: ticketListError, refresh: refreshTickets } =
    useTickets();
  const { detail, loading, error, refresh } = useTicketDetail(id);

  const interpretationWarning = useMemo(() => {
    if (!detail?.interpretation?.confidence) {
      return false;
    }
    return detail.interpretation.confidence < 0.6;
  }, [detail?.interpretation?.confidence]);

  const urgency = detail ? getUrgencyMeta(detail.urgency_score) : null;

  async function refreshAll() {
    await Promise.all([refresh(), refreshTickets()]);
  }

  return (
    <div className="app-shell">
      <aside className="app-shell__sidebar">
        <TicketList
          error={ticketListError}
          loading={loadingTickets}
          selectedId={id}
          tickets={tickets}
        />
      </aside>

      <main className="app-shell__content">
        {loading ? <p className="page-message">Loading ticket detail…</p> : null}
        {error ? <p className="page-message page-message--error">{error}</p> : null}

        {!loading && !detail ? (
          <section className="panel panel--placeholder">
            <p className="eyebrow">Ticket detail</p>
            <h2>No ticket selected</h2>
            <p>
              Return to the <Link to="/">dashboard</Link> and choose a ticket from the
              queue.
            </p>
          </section>
        ) : null}

        {detail ? (
          <>
            <section className="panel email-panel">
              <div className="panel__header panel__header--spread">
                <div>
                  <p className="eyebrow">Conversation context</p>
                  <h1>{detail.subject || "Untitled issue"}</h1>
                </div>
                {urgency ? (
                  <span className={`urgency-pill urgency-pill--${urgency.tone}`}>
                    {urgency.label} urgency
                  </span>
                ) : null}
              </div>

              <div className="email-panel__meta">
                <span>From {detail.customer_email}</span>
                <span>{formatTimestamp(detail.created_at)}</span>
                <span className={`status-badge status-badge--${detail.status}`}>
                  {detail.status}
                </span>
              </div>

              <article className="email-body" style={getRtlStyle(detail.body)}>
                <p>{detail.body || "No original body available."}</p>
              </article>

              <div className="thread-block">
                <h3>Previous messages</h3>
                {detail.messages.length === 0 ? (
                  <p className="panel__message">No message history stored yet.</p>
                ) : (
                  detail.messages.map((message) => (
                    <div className="thread-message" key={message.id}>
                      <div className="thread-message__topline">
                        <strong>{formatLabel(message.sender)}</strong>
                        <span>{formatTimestamp(message.timestamp)}</span>
                      </div>
                      <p style={getRtlStyle(message.content)}>{message.content}</p>
                    </div>
                  ))
                )}
              </div>
            </section>

            <section
              className={`panel ${interpretationWarning ? "panel--warning" : ""}`}
            >
              <div className="panel__header panel__header--spread">
                <div>
                  <p className="eyebrow">System interpretation</p>
                  <h2>Current understanding</h2>
                </div>
                <span className="status-badge" style={{ fontSize: "0.7rem", opacity: 0.8 }}>
                  Arabic Native
                </span>
              </div>

              <div className="interpretation-grid">
                <div>
                  <span>Intent</span>
                  <strong>{formatLabel(detail.interpretation?.intent)}</strong>
                </div>
                <div>
                  <span>Category</span>
                  <strong>{formatLabel(detail.interpretation?.category)}</strong>
                </div>
                <div>
                  <span>Sentiment</span>
                  <strong>{formatLabel(detail.interpretation?.sentiment)}</strong>
                </div>
                <div>
                  <span>Confidence</span>
                  <strong>{formatPercent(detail.interpretation?.confidence)}</strong>
                </div>
              </div>

              {detail.interpretation?.reasoning ? (
                <p className="interpretation-reasoning">{detail.interpretation.reasoning}</p>
              ) : null}

              {interpretationWarning ? (
                <p className="panel__message panel__message--warning">
                  Confidence is below 60%, so this interpretation should be treated cautiously.
                </p>
              ) : null}
            </section>

            <EntityViewer
              entities={detail.entities}
              onEntitySaved={refreshAll}
              requiredFields={detail.required_fields}
              ticketId={detail.id}
            />

            <AttachmentViewer attachments={detail.attachments} />

            <div className="detail-grid detail-grid--double">
              <AgentPanel agentAction={detail.agent_action} />
              <ActionControls
                missingFields={detail.required_fields}
                onActionComplete={refreshAll}
                ticketStatus={detail.status}
                ticketId={detail.id}
              />
            </div>
          </>
        ) : null}
      </main>
    </div>
  );
}

import { useState } from "react";
import { Link } from "react-router-dom";

import TicketList from "../components/TicketList";
import { useTickets } from "../hooks/useTickets";
import { submitSimulatedEmail } from "../services/api";
import { formatLabel } from "../utils/format";

export default function Dashboard() {
  const { tickets, loading, error, refresh } = useTickets();
  const [simulationOpen, setSimulationOpen] = useState(false);
  const [customerEmail, setCustomerEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [threadId, setThreadId] = useState("");
  const [attachments, setAttachments] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  const [lastTicketId, setLastTicketId] = useState<string | null>(null);
  const [lastThreadId, setLastThreadId] = useState<string | null>(null);
  const [escalationInfo, setEscalationInfo] = useState<{ escalated: boolean; target?: string } | null>(null);

  function resetSimulationForm() {
    setCustomerEmail("");
    setSubject("");
    setBody("");
    setThreadId("");
    setAttachments([]);
    setSubmitError(null);
    setAiResponse(null);
    setLastTicketId(null);
    setLastThreadId(null);
    setEscalationInfo(null);
  }

  function closeSimulation() {
    setSimulationOpen(false);
    resetSimulationForm();
  }

  async function handleSubmitSimulation() {
    if (!customerEmail.trim() || !subject.trim() || !body.trim()) {
      setSubmitError("Customer email, title, and body are required.");
      return;
    }

    setSubmitting(true);
    setSubmitError(null);
    try {
      const currentThreadId = threadId.trim();
      const response = await submitSimulatedEmail({
        customer_email: customerEmail.trim(),
        subject: subject.trim(),
        body: body.trim(),
        attachments,
        thread_id: currentThreadId || undefined,
      });
      await refresh();
      setAiResponse(response.email_body || "Success! (No response body returned)");
      setLastTicketId(response.ticket_id);
      setLastThreadId(currentThreadId);
      setEscalationInfo({ escalated: !!response.escalated, target: response.escalation_target });
      
      // Clear body/attachments but keep thread/email for continuation
      setBody("");
      setAttachments([]);
    } catch (simulationError) {
      setSubmitError(
        simulationError instanceof Error
          ? simulationError.message
          : "Failed to send simulated email.",
      );
    } finally {
      setSubmitting(false);
    }
  }

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

          <div className="hero-panel__actions">
            <button
              className="button button--ghost hero-panel__cta"
              onClick={() => setSimulationOpen(true)}
              type="button"
            >
              Simulate customer mail
            </button>

            {tickets.length > 0 ? (
              <Link className="button button--primary hero-panel__cta" to={`/ticket/${tickets[0].id}`}>
                Open highest-visibility ticket
              </Link>
            ) : (
              <span className="hero-panel__empty">
                Tickets will appear here once the backend queue is populated.
              </span>
            )}
          </div>
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

      {simulationOpen ? (
        <div className="modal-backdrop" onClick={closeSimulation} role="presentation">
          <section
            aria-modal="true"
            className="panel modal-card"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
          >
            <div className="modal-card__scroll-area">
              <div className="panel__header panel__header--spread">
                <div>
                  <p className="eyebrow">Simulation</p>
                  <h2>Send a customer email</h2>
                </div>
                <button className="icon-button" onClick={closeSimulation} type="button">
                  Close
                </button>
              </div>

              <div className="simulation-form">
                <label className="simulation-field">
                  <span>Customer email</span>
                  <input
                    onChange={(event) => setCustomerEmail(event.target.value)}
                    placeholder="customer@example.com"
                    type="email"
                    value={customerEmail}
                  />
                </label>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                  <label className="simulation-field">
                    <span>Title</span>
                    <input
                      onChange={(event) => setSubject(event.target.value)}
                      placeholder="Order refund request"
                      type="text"
                      value={subject}
                    />
                  </label>

                  <label className="simulation-field">
                    <span>Thread ID (Optional)</span>
                    <input
                      onChange={(event) => setThreadId(event.target.value)}
                      placeholder="uuid-or-thread-id"
                      type="text"
                      value={threadId}
                    />
                  </label>
                </div>

                <label className="simulation-field simulation-field--body">
                  <span>Body</span>
                  <textarea
                    onChange={(event) => setBody(event.target.value)}
                    placeholder="Write the customer's message here..."
                    rows={8}
                    value={body}
                  />
                </label>

                <label className="simulation-field">
                  <span>Attachments</span>
                  <input
                    multiple
                    onChange={(event) => setAttachments(Array.from(event.target.files ?? []))}
                    type="file"
                  />
                </label>

                {attachments.length > 0 ? (
                  <div className="simulation-chips" aria-label="Selected attachments">
                    {attachments.map((file) => (
                      <span className="simulation-chip" key={`${file.name}-${file.size}`}>
                        {file.name}
                      </span>
                    ))}
                  </div>
                ) : null}

                {submitError ? <p className="panel__message panel__message--error">{submitError}</p> : null}

                {aiResponse ? (
                  <div className="simulation-response">
                    <p className="eyebrow">System Response</p>
                    <div className="email-body" style={{ marginTop: "8px", fontSize: "0.9rem" }}>
                      {aiResponse}
                    </div>

                    {escalationInfo?.escalated && (
                      <div className="panel--warning" style={{ marginTop: "16px", padding: "12px 16px", borderRadius: "12px" }}>
                        <p className="eyebrow" style={{ color: "var(--warning)" }}>Automated Escalation</p>
                        <p style={{ margin: "4px 0 0", fontSize: "0.9rem" }}>
                          This interaction has been automatically escalated to the <strong>{formatLabel(escalationInfo.target)}</strong> department.
                        </p>
                      </div>
                    )}

                    <div style={{ marginTop: "16px", display: "flex", alignItems: "center", gap: "12px" }}>
                      {lastTicketId && (
                        <Link 
                          className="button button--secondary" 
                          to={`/ticket/${lastTicketId}`}
                          onClick={closeSimulation}
                        >
                          View generated ticket
                        </Link>
                      )}
                      {lastThreadId && (
                        <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                          Thread ID: <strong>{lastThreadId}</strong>
                        </span>
                      )}
                    </div>
                  </div>
                ) : null}

                <div className="action-grid modal-actions">
                  <button className="button button--secondary" onClick={closeSimulation} type="button">
                    Cancel
                  </button>
                  <button
                    className="button button--primary"
                    disabled={submitting}
                    onClick={() => void handleSubmitSimulation()}
                    type="button"
                  >
                    {submitting ? "Sending…" : "Send"}
                  </button>
                </div>
              </div>
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}

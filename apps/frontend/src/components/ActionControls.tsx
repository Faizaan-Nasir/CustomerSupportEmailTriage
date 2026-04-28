import { useState } from "react";

import { sendAgentAction } from "../services/api";
import type { AgentActionType, TicketStatus } from "../types/ticket";

interface ActionControlsProps {
  ticketId: string;
  ticketStatus: TicketStatus;
  missingFields: string[];
  onActionComplete: () => Promise<void> | void;
}

export default function ActionControls({
  ticketId,
  ticketStatus,
  missingFields,
  onActionComplete,
}: ActionControlsProps) {
  const [draft, setDraft] = useState("");
  const [activeAction, setActiveAction] = useState<AgentActionType | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runAction(action: AgentActionType) {
    setActiveAction(action);
    setError(null);
    try {
      const payload =
        action === "reply"
          ? {
            ticket_id: ticketId,
            action,
            data: { content: draft },
          }
          : {
            ticket_id: ticketId,
            action,
            data: { note: draft },
          };

      await sendAgentAction(payload);
      setDraft("");
      await onActionComplete();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "Action failed.");
    } finally {
      setActiveAction(null);
    }
  }

  const isResolved = ticketStatus === "resolved";
  const isEscalated = ticketStatus === "escalated";
  const isLocked = isResolved;
  const escalateDisabled = missingFields.length > 0 || isLocked || isEscalated;
  const replyDisabled = !draft.trim();
  const showMissingInfoWarning = missingFields.length > 0 && !isEscalated && !isResolved;
  const escalationMessage = isEscalated
    ? "This ticket has already been escalated to the appropriate internal team."
    : showMissingInfoWarning
      ? "Escalation is disabled until the required missing information is filled in."
      : null;

  return (
    <section className="panel panel--actions">
      <div className="panel__header">
        <div>
          <p className="eyebrow">Execution</p>
          <h2>Action controls</h2>
        </div>
      </div>

      <label className="reply-box">
        <span>Reply / note</span>
        <textarea
          disabled={isLocked}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Write the customer reply or an internal note for escalation / resolution."
          rows={5}
          value={draft}
        />
      </label>

      <div className="action-grid">
        <button
          className="button button--primary"
          disabled={replyDisabled || activeAction !== null || isLocked}
          onClick={() => void runAction("reply")}
          type="button"
        >
          {activeAction === "reply" ? "Sending…" : "Send reply"}
        </button>
        <button
          className="button button--warning"
          disabled={escalateDisabled || activeAction !== null}
          onClick={() => void runAction("escalate")}
          type="button"
        >
          {isEscalated ? "Escalated" : activeAction === "escalate" ? "Escalating…" : "Escalate"}
        </button>
        <button
          className="button button--success"
          disabled={activeAction !== null || isLocked}
          onClick={() => void runAction("resolve")}
          type="button"
        >
          {isResolved ? "Resolved" : activeAction === "resolve" ? "Resolving…" : "Mark resolved"}
        </button>
      </div>

      {escalationMessage ? (
        <p className="panel__message panel__message--warning">{escalationMessage}</p>
      ) : null}

      {error ? <p className="panel__message panel__message--error">{error}</p> : null}
    </section>
  );
}

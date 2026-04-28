import type { AgentActionDetail } from "../types/ticket";
import { formatLabel, formatTimestamp } from "../utils/format";

interface AgentPanelProps {
  agentAction: AgentActionDetail | null;
}

export default function AgentPanel({ agentAction }: AgentPanelProps) {
  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="eyebrow">Guidance</p>
          <h2>Suggested action plan</h2>
        </div>
      </div>

      {!agentAction ? (
        <p className="panel__message">
          No agent action plan has been generated for this ticket yet.
        </p>
      ) : (
        <div className="agent-plan">
          <div className="agent-plan__block">
            <span className="agent-plan__label">Summary</span>
            <p>{agentAction.summary || "No summary available."}</p>
          </div>

          <div className="agent-plan__block">
            <span className="agent-plan__label">Steps</span>
            <ol>
              {agentAction.action_plan.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </div>

          <div className="agent-plan__meta">
            <span>
              Escalation:{" "}
              <strong>
                {agentAction.escalation_target
                  ? formatLabel(agentAction.escalation_target)
                  : "Not required"}
              </strong>
            </span>
            <span>Generated {formatTimestamp(agentAction.generated_at)}</span>
          </div>
        </div>
      )}
    </section>
  );
}

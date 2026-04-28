import { useEffect, useState } from "react";

import { updateEntity } from "../services/api";
import type { EntityDetail } from "../types/ticket";
import { formatLabel } from "../utils/format";

interface EntityViewerProps {
  ticketId: string;
  entities: EntityDetail[];
  requiredFields: string[];
  onEntitySaved: () => Promise<void> | void;
}

export default function EntityViewer({
  ticketId,
  entities,
  requiredFields,
  onEntitySaved,
}: EntityViewerProps) {
  const [draftValues, setDraftValues] = useState<Record<string, string>>({});
  const [savingId, setSavingId] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    const nextValues: Record<string, string> = {};
    for (const entity of entities) {
      nextValues[entity.id] = entity.value;
    }
    setDraftValues(nextValues);
  }, [entities]);

  async function handleSave(entity: EntityDetail) {
    const nextValue = (draftValues[entity.id] || "").trim();
    if (!nextValue || nextValue === entity.value) {
      return;
    }

    setSavingId(entity.id);
    setSaveError(null);
    try {
      await updateEntity(ticketId, entity.id, {
        key: entity.key,
        value: nextValue,
        source: entity.source,
        confidence: entity.confidence,
      });
      await onEntitySaved();
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Failed to save entity.");
    } finally {
      setSavingId(null);
    }
  }

  return (
    <div className="detail-grid detail-grid--double">
      <section className="panel">
        <div className="panel__header">
          <div>
            <p className="eyebrow">Structured data</p>
            <h2>Extracted entities</h2>
          </div>
        </div>

        <div className="entity-list">
          {entities.length === 0 ? (
            <p className="panel__message">No entities were extracted for this ticket.</p>
          ) : null}

          {entities.map((entity) => {
            const changed = draftValues[entity.id] !== entity.value;
            return (
              <div className="entity-row" key={entity.id}>
                <div className="entity-row__meta">
                  <span>{formatLabel(entity.key)}</span>
                  <small>
                    {entity.source ? formatLabel(entity.source) : "Unknown source"}
                  </small>
                </div>
                <div className="entity-row__editor">
                  <input
                    onChange={(event) =>
                      setDraftValues((current) => ({
                        ...current,
                        [entity.id]: event.target.value,
                      }))
                    }
                    value={draftValues[entity.id] ?? entity.value}
                  />
                  <button
                    className="button button--secondary"
                    disabled={!changed || savingId === entity.id}
                    onClick={() => void handleSave(entity)}
                    type="button"
                  >
                    {savingId === entity.id ? "Saving…" : "Save"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {saveError ? <p className="panel__message panel__message--error">{saveError}</p> : null}
      </section>

      <section className="panel panel--warning">
        <div className="panel__header">
          <div>
            <p className="eyebrow">Action readiness</p>
            <h2>Missing information</h2>
          </div>
        </div>

        {requiredFields.length === 0 ? (
          <p className="panel__message panel__message--success">
            This ticket appears action-ready. No missing fields are currently required.
          </p>
        ) : (
          <ul className="missing-list">
            {requiredFields.map((field) => (
              <li key={field}>{formatLabel(field)}</li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

import { useState } from "react";

import { resolveAttachmentPreviewUrl } from "../services/api";
import type { AttachmentDetail } from "../types/ticket";
import { formatTimestamp } from "../utils/format";

interface AttachmentViewerProps {
  attachments: AttachmentDetail[];
}

export default function AttachmentViewer({ attachments }: AttachmentViewerProps) {
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({});

  function toggleAttachment(attachmentId: string) {
    setExpandedIds((current) => ({
      ...current,
      [attachmentId]: !current[attachmentId],
    }));
  }

  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="eyebrow">Context files</p>
          <h2>Attachments</h2>
        </div>
      </div>

      {attachments.length === 0 ? (
        <p className="panel__message">No attachments were stored for this ticket.</p>
      ) : (
        <div className="attachment-list">
          {attachments.map((attachment) => {
            const previewHref = resolveAttachmentPreviewUrl(attachment.preview_url);
            const expanded = !!expandedIds[attachment.id];
            return (
              <article className="attachment-card" key={attachment.id}>
                <div className="attachment-card__topline">
                  <div>
                    <h3>{attachment.file_url?.split("/").pop() || "Attachment"}</h3>
                    <p>{formatTimestamp(attachment.created_at)}</p>
                  </div>
                  <div className="attachment-card__actions">
                    {previewHref ? (
                      <a
                        className="button button--secondary"
                        href={previewHref}
                        rel="noreferrer"
                        target="_blank"
                      >
                        Preview
                      </a>
                    ) : null}
                    <button
                      className="button button--ghost"
                      onClick={() => toggleAttachment(attachment.id)}
                      type="button"
                    >
                      {expanded ? "Hide extracted text" : "Show extracted text"}
                    </button>
                  </div>
                </div>

                {expanded && attachment.parsed_text ? (
                  <pre className="attachment-card__text">{attachment.parsed_text}</pre>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

"""Service for normalizing and storing incoming emails."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from app.repositories.message_repo import create_message
from app.repositories.ticket_repo import create_ticket


class IngestionInput(TypedDict, total=False):
    """Normalized inbound email payload."""

    customer_email: str
    subject: str
    body: str
    sender: str


class IngestionResult(TypedDict):
    """Identifiers produced by the ingestion step."""

    ticket_id: str
    message_id: str
    created_at: str
    status: str


@dataclass
class IngestionService:
    """Create a ticket record and persist the initial inbound message."""

    def ingest_email(self, payload: IngestionInput) -> IngestionResult:
        """Persist the inbound email as a ticket plus its opening message."""
        customer_email = (payload.get("customer_email") or "").strip()
        subject = (payload.get("subject") or "").strip()
        body = (payload.get("body") or "").strip()
        sender = (payload.get("sender") or "customer").strip() or "customer"

        if not customer_email:
            raise ValueError("customer_email is required.")
        if not body:
            raise ValueError("body is required.")

        ticket = create_ticket(
            {
                "customer_email": customer_email,
                "subject": subject,
                "body": body,
            }
        )
        message = create_message(
            {
                "ticket_id": ticket["id"],
                "sender": sender,
                "content": body,
            }
        )

        return {
            "ticket_id": ticket["id"],
            "message_id": message["id"],
            "created_at": ticket["created_at"],
            "status": "ingested",
        }


_service: IngestionService | None = None


def get_ingestion_service() -> IngestionService:
    """Return a singleton ingestion service instance."""
    global _service
    if _service is None:
        _service = IngestionService()
    return _service


def ingest_email(payload: IngestionInput) -> IngestionResult:
    """Compatibility helper matching the technical document wording."""
    return get_ingestion_service().ingest_email(payload)

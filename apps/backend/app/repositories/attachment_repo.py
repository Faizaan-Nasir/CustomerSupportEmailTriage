"""Repository helpers for storing attachment metadata and embeddings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict

from app.repositories.supabase_client import get_client


class AttachmentCreateInput(TypedDict, total=False):
    """Payload for inserting an attachment record."""

    ticket_id: str
    file_url: str
    parsed_text: str
    embedding: list[float]


class AttachmentRecord(TypedDict, total=False):
    """Normalized attachment record returned from Supabase."""

    id: str
    ticket_id: str
    file_url: str | None
    parsed_text: str | None
    embedding: list[float] | None
    created_at: str


def _serialize_embedding(embedding: list[float] | None) -> str | None:
    if embedding is None:
        return None
    return "[" + ",".join(str(float(value)) for value in embedding) + "]"


def _deserialize_embedding(value: Any) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return [float(item) for item in value]
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.startswith("[") and cleaned.endswith("]"):
            cleaned = cleaned[1:-1].strip()
        if not cleaned:
            return []
        return [float(item.strip()) for item in cleaned.split(",")]
    return None


@dataclass
class AttachmentRepository:
    """CRUD-style operations for the `attachments` table."""

    table_name: str = "attachments"

    def __post_init__(self) -> None:
        self._client = get_client()

    @staticmethod
    def _first_row(response: Any) -> dict[str, Any]:
        rows = getattr(response, "data", None) or []
        if not rows:
            raise LookupError("Supabase returned no rows.")
        return dict(rows[0])

    @staticmethod
    def _normalize_row(row: dict[str, Any]) -> AttachmentRecord:
        normalized = dict(row)
        normalized["embedding"] = _deserialize_embedding(normalized.get("embedding"))
        return AttachmentRecord(normalized)

    def create_attachment(self, payload: AttachmentCreateInput) -> dict[str, str]:
        """Insert an attachment and return its identifier plus timestamp."""
        insert_payload = dict(payload)
        if "embedding" in insert_payload:
            insert_payload["embedding"] = _serialize_embedding(insert_payload["embedding"])

        response = self._client.table(self.table_name).insert(insert_payload).execute()
        row = self._first_row(response)
        return {
            "id": row["id"],
            "created_at": row["created_at"],
        }

    def list_attachments_for_ticket(self, ticket_id: str) -> list[AttachmentRecord]:
        """Return all attachments associated with a ticket."""
        response = (
            self._client.table(self.table_name)
            .select("*")
            .eq("ticket_id", ticket_id)
            .order("created_at")
            .execute()
        )
        rows = getattr(response, "data", None) or []
        return [self._normalize_row(dict(row)) for row in rows]

    def get_attachment(self, attachment_id: str) -> AttachmentRecord:
        """Fetch a single attachment record by id."""
        response = (
            self._client.table(self.table_name)
            .select("*")
            .eq("id", attachment_id)
            .limit(1)
            .execute()
        )
        return self._normalize_row(self._first_row(response))


_repo: AttachmentRepository | None = None


def get_attachment_repository() -> AttachmentRepository:
    """Return a singleton attachment repository instance."""
    global _repo
    if _repo is None:
        _repo = AttachmentRepository()
    return _repo


def create_attachment(payload: AttachmentCreateInput) -> dict[str, str]:
    """Compatibility helper matching the technical document wording."""
    return get_attachment_repository().create_attachment(payload)


def list_attachments_for_ticket(ticket_id: str) -> list[AttachmentRecord]:
    """Compatibility helper for ticket-scoped attachment reads."""
    return get_attachment_repository().list_attachments_for_ticket(ticket_id)


def get_attachment(attachment_id: str) -> AttachmentRecord:
    """Compatibility helper for direct record lookup."""
    return get_attachment_repository().get_attachment(attachment_id)


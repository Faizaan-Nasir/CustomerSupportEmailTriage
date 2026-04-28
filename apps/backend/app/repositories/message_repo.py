"""Repository helpers for storing and reading ticket messages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict

from app.repositories.supabase_client import get_client


class MessageCreateInput(TypedDict):
    """Payload for inserting a ticket message."""

    ticket_id: str
    sender: str
    content: str


class MessageRecord(TypedDict, total=False):
    """Normalized message record returned from Supabase."""

    id: str
    ticket_id: str
    sender: str
    content: str
    timestamp: str


@dataclass
class MessageRepository:
    """CRUD-style operations for the `messages` table."""

    table_name: str = "messages"

    def __post_init__(self) -> None:
        self._client = get_client()

    @staticmethod
    def _first_row(response: Any) -> dict[str, Any]:
        rows = getattr(response, "data", None) or []
        if not rows:
            raise LookupError("Supabase returned no rows.")
        return dict(rows[0])

    def create_message(self, payload: MessageCreateInput) -> dict[str, str]:
        """Insert a message and return its identifier plus timestamp."""
        response = self._client.table(self.table_name).insert(dict(payload)).execute()
        row = self._first_row(response)
        return {
            "id": row["id"],
            "timestamp": row["timestamp"],
        }

    def list_messages_for_ticket(self, ticket_id: str) -> list[MessageRecord]:
        """Return all messages associated with a ticket."""
        response = (
            self._client.table(self.table_name)
            .select("*")
            .eq("ticket_id", ticket_id)
            .order("timestamp")
            .execute()
        )
        rows = getattr(response, "data", None) or []
        return [MessageRecord(dict(row)) for row in rows]

    def get_message(self, message_id: str) -> MessageRecord:
        """Fetch a single message record by id."""
        response = (
            self._client.table(self.table_name)
            .select("*")
            .eq("id", message_id)
            .limit(1)
            .execute()
        )
        return MessageRecord(self._first_row(response))


_repo: MessageRepository | None = None


def get_message_repository() -> MessageRepository:
    """Return a singleton message repository instance."""
    global _repo
    if _repo is None:
        _repo = MessageRepository()
    return _repo


def create_message(payload: MessageCreateInput) -> dict[str, str]:
    """Compatibility helper matching the table's insert use case."""
    return get_message_repository().create_message(payload)


def list_messages_for_ticket(ticket_id: str) -> list[MessageRecord]:
    """Compatibility helper for ticket-scoped message reads."""
    return get_message_repository().list_messages_for_ticket(ticket_id)


def get_message(message_id: str) -> MessageRecord:
    """Compatibility helper for direct record lookup."""
    return get_message_repository().get_message(message_id)


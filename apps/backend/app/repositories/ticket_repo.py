"""Repository helpers for working with support tickets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict

from app.repositories.supabase_client import get_client


class TicketCreateInput(TypedDict, total=False):
    """Required payload for creating a ticket."""

    customer_email: str
    subject: str
    body: str
    thread_id: str | None


class TicketRecord(TypedDict, total=False):
    """Normalized ticket record returned from Supabase."""

    id: str
    thread_id: str | None
    customer_email: str
    subject: str | None
    body: str | None
    status: str
    urgency_score: float
    interaction_count: int
    created_at: str
    updated_at: str


@dataclass
class TicketRepository:
    """CRUD operations for the `tickets` table."""

    table_name: str = "tickets"

    def __post_init__(self) -> None:
        self._client = get_client()

    @staticmethod
    def _first_row(response: Any) -> dict[str, Any]:
        rows = getattr(response, "data", None) or []
        if not rows:
            raise LookupError("Supabase returned no rows.")
        return dict(rows[0])

    def create_ticket(self, payload: TicketCreateInput) -> dict[str, str]:
        """Insert a ticket and return its identifier plus creation timestamp."""
        insert_data = {
            "customer_email": payload["customer_email"],
            "subject": payload["subject"],
            "body": payload["body"],
        }
        if payload.get("thread_id"):
            insert_data["thread_id"] = payload["thread_id"]

        response = (
            self._client.table(self.table_name)
            .insert(insert_data)
            .execute()
        )
        row = self._first_row(response)
        return {
            "id": row["id"],
            "created_at": row["created_at"],
        }

    def find_by_thread_id(self, thread_id: str) -> TicketRecord | None:
        """Find an existing ticket by its thread identifier."""
        response = (
            self._client.table(self.table_name)
            .select("*")
            .eq("thread_id", thread_id)
            .limit(1)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        if not rows:
            return None
        return TicketRecord(dict(rows[0]))

    def get_ticket(self, ticket_id: str) -> TicketRecord:
        """Fetch a single ticket by id."""
        response = (
            self._client.table(self.table_name)
            .select("*")
            .eq("id", ticket_id)
            .limit(1)
            .execute()
        )
        return TicketRecord(self._first_row(response))

    def update_ticket(self, ticket_id: str, updates: dict[str, Any]) -> TicketRecord:
        """Update a ticket and return the updated record."""
        response = (
            self._client.table(self.table_name)
            .update(updates)
            .eq("id", ticket_id)
            .execute()
        )
        return TicketRecord(self._first_row(response))

    def list_tickets(self, limit: int = 50) -> list[TicketRecord]:
        """Fetch recent tickets, moving resolved ones to the end of the queue."""
        response = (
            self._client.table(self.table_name)
            .select("*")
            .order("status", desc=True)  # 'resolved' starts with 'r', 'open' with 'o', 'escalated' with 'e'. Desc puts 'resolved' last.
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        return [TicketRecord(dict(row)) for row in rows]


_repo: TicketRepository | None = None


def get_ticket_repository() -> TicketRepository:
    """Return a singleton ticket repository instance."""
    global _repo
    if _repo is None:
        _repo = TicketRepository()
    return _repo


def create_ticket(payload: TicketCreateInput) -> dict[str, str]:
    """Compatibility helper matching the technical document wording."""
    return get_ticket_repository().create_ticket(payload)


def get_ticket(ticket_id: str) -> TicketRecord:
    """Compatibility helper matching the technical document wording."""
    return get_ticket_repository().get_ticket(ticket_id)


def update_ticket(ticket_id: str, updates: dict[str, Any]) -> TicketRecord:
    """Compatibility helper for ticket updates."""
    return get_ticket_repository().update_ticket(ticket_id, updates)


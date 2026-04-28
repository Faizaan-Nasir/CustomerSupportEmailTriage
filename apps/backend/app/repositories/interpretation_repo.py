"""Repository helpers for storing and reading ticket interpretations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict

from app.repositories.supabase_client import get_client


class InterpretationCreateInput(TypedDict, total=False):
    """Payload for inserting an interpretation record."""

    ticket_id: str
    intent: str
    category: str
    sentiment: str
    urgency: float
    confidence: float
    reasoning: str
    raw_output: dict[str, Any]


class InterpretationRecord(TypedDict, total=False):
    """Normalized interpretation record returned from Supabase."""

    id: str
    ticket_id: str
    intent: str | None
    category: str | None
    sentiment: str | None
    urgency: float | None
    confidence: float | None
    reasoning: str | None
    raw_output: dict[str, Any] | None
    created_at: str


@dataclass
class InterpretationRepository:
    """CRUD-style operations for the `interpretations` table."""

    table_name: str = "interpretations"

    def __post_init__(self) -> None:
        self._client = get_client()

    @staticmethod
    def _first_row(response: Any) -> dict[str, Any]:
        rows = getattr(response, "data", None) or []
        if not rows:
            raise LookupError("Supabase returned no rows.")
        return dict(rows[0])

    def create_interpretation(self, payload: InterpretationCreateInput) -> dict[str, str]:
        """Insert an interpretation and return its identifier plus timestamp."""
        response = self._client.table(self.table_name).insert(dict(payload)).execute()
        row = self._first_row(response)
        return {
            "id": row["id"],
            "created_at": row["created_at"],
        }

    def list_interpretations_for_ticket(self, ticket_id: str) -> list[InterpretationRecord]:
        """Return all interpretations associated with a ticket."""
        response = (
            self._client.table(self.table_name)
            .select("*")
            .eq("ticket_id", ticket_id)
            .order("created_at")
            .execute()
        )
        rows = getattr(response, "data", None) or []
        return [InterpretationRecord(dict(row)) for row in rows]

    def get_latest_interpretation_for_ticket(self, ticket_id: str) -> InterpretationRecord:
        """Return the most recent interpretation associated with a ticket."""
        response = (
            self._client.table(self.table_name)
            .select("*")
            .eq("ticket_id", ticket_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return InterpretationRecord(self._first_row(response))

    def get_interpretation(self, interpretation_id: str) -> InterpretationRecord:
        """Fetch a single interpretation record by id."""
        response = (
            self._client.table(self.table_name)
            .select("*")
            .eq("id", interpretation_id)
            .limit(1)
            .execute()
        )
        return InterpretationRecord(self._first_row(response))


_repo: InterpretationRepository | None = None


def get_interpretation_repository() -> InterpretationRepository:
    """Return a singleton interpretation repository instance."""
    global _repo
    if _repo is None:
        _repo = InterpretationRepository()
    return _repo


def create_interpretation(payload: InterpretationCreateInput) -> dict[str, str]:
    """Compatibility helper matching the technical document wording."""
    return get_interpretation_repository().create_interpretation(payload)


def list_interpretations_for_ticket(ticket_id: str) -> list[InterpretationRecord]:
    """Compatibility helper for ticket-scoped interpretation reads."""
    return get_interpretation_repository().list_interpretations_for_ticket(ticket_id)


def get_latest_interpretation_for_ticket(ticket_id: str) -> InterpretationRecord:
    """Compatibility helper for latest interpretation lookup."""
    return get_interpretation_repository().get_latest_interpretation_for_ticket(ticket_id)


def get_interpretation(interpretation_id: str) -> InterpretationRecord:
    """Compatibility helper for direct record lookup."""
    return get_interpretation_repository().get_interpretation(interpretation_id)


"""Repository helpers for storing and reading extracted entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict

from app.repositories.supabase_client import get_client


class EntityCreateInput(TypedDict, total=False):
    """Payload for inserting an extracted entity."""

    ticket_id: str
    key: str
    value: str
    source: str
    confidence: float


class EntityRecord(TypedDict, total=False):
    """Normalized entity record returned from Supabase."""

    id: str
    ticket_id: str
    key: str
    value: str
    source: str | None
    confidence: float | None
    created_at: str


class EntityUpdateInput(TypedDict, total=False):
    """Payload for updating an extracted entity."""

    key: str
    value: str
    source: str
    confidence: float


@dataclass
class EntityRepository:
    """CRUD-style operations for the `entities` table."""

    table_name: str = "entities"

    def __post_init__(self) -> None:
        self._client = get_client()

    @staticmethod
    def _first_row(response: Any) -> dict[str, Any]:
        rows = getattr(response, "data", None) or []
        if not rows:
            raise LookupError("Supabase returned no rows.")
        return dict(rows[0])

    def create_entity(self, payload: EntityCreateInput) -> dict[str, str]:
        """Insert an entity and return its identifier plus creation timestamp."""
        response = self._client.table(self.table_name).insert(dict(payload)).execute()
        row = self._first_row(response)
        return {
            "id": row["id"],
            "created_at": row["created_at"],
        }

    def list_entities_for_ticket(self, ticket_id: str) -> list[EntityRecord]:
        """Return all entities associated with a ticket."""
        response = (
            self._client.table(self.table_name)
            .select("*")
            .eq("ticket_id", ticket_id)
            .order("created_at")
            .execute()
        )
        rows = getattr(response, "data", None) or []
        return [EntityRecord(dict(row)) for row in rows]

    def get_entity(self, entity_id: str) -> EntityRecord:
        """Fetch a single entity record by id."""
        response = (
            self._client.table(self.table_name)
            .select("*")
            .eq("id", entity_id)
            .limit(1)
            .execute()
        )
        return EntityRecord(self._first_row(response))

    def update_entity(self, entity_id: str, payload: EntityUpdateInput) -> EntityRecord:
        """Update an entity record and return the normalized row."""
        response = (
            self._client.table(self.table_name)
            .update(dict(payload))
            .eq("id", entity_id)
            .execute()
        )
        return EntityRecord(self._first_row(response))


_repo: EntityRepository | None = None


def get_entity_repository() -> EntityRepository:
    """Return a singleton entity repository instance."""
    global _repo
    if _repo is None:
        _repo = EntityRepository()
    return _repo


def create_entity(payload: EntityCreateInput) -> dict[str, str]:
    """Compatibility helper matching the technical document wording."""
    return get_entity_repository().create_entity(payload)


def list_entities_for_ticket(ticket_id: str) -> list[EntityRecord]:
    """Compatibility helper for ticket-scoped reads."""
    return get_entity_repository().list_entities_for_ticket(ticket_id)


def get_entity(entity_id: str) -> EntityRecord:
    """Compatibility helper for direct record lookup."""
    return get_entity_repository().get_entity(entity_id)


def update_entity(entity_id: str, payload: EntityUpdateInput) -> EntityRecord:
    """Compatibility helper for updating entity records."""
    return get_entity_repository().update_entity(entity_id, payload)

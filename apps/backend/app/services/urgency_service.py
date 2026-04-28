"""Service for time-based urgency updates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, TypedDict

from app.repositories.supabase_client import get_client
from app.repositories.ticket_repo import get_ticket, update_ticket


class UrgencyUpdateInput(TypedDict, total=False):
    """Input contract for aging-based urgency recalculation."""

    ticket_id: str
    initial_urgency: float
    created_at: str
    reference_time: str


class UrgencyUpdateResult(TypedDict):
    """Output contract for urgency updates."""

    ticket_id: str
    previous_urgency: float
    updated_urgency: float
    hours_open: float


def _clamp_score(value: Any) -> float:
    numeric = float(value)
    if numeric < 0.0:
        return 0.0
    if numeric > 1.0:
        return 1.0
    return numeric


def _parse_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


@dataclass
class UrgencyService:
    """Update ticket urgency using an aging-based escalation model."""

    table_name: str = "tickets"

    def __post_init__(self) -> None:
        self._client = get_client()

    def _calculate_aged_urgency(self, initial_urgency: float, hours_open: float) -> float:
        if initial_urgency >= 0.8:
            aged = initial_urgency + min(hours_open / 240.0, 0.12)
        elif initial_urgency >= 0.5:
            aged = initial_urgency + min(hours_open / 120.0, 0.25)
        else:
            aged = initial_urgency + min(hours_open / 72.0, 0.4)
        return _clamp_score(aged)

    def update_urgency(self, payload: UrgencyUpdateInput) -> UrgencyUpdateResult:
        """Recalculate and persist urgency based on how long a ticket has been open."""
        ticket_id = str(payload.get("ticket_id") or "").strip()
        if not ticket_id:
            raise ValueError("ticket_id is required.")

        ticket = get_ticket(ticket_id)
        previous_urgency = _clamp_score(payload.get("initial_urgency", ticket.get("urgency_score", 0.0)))
        created_at_raw = str(payload.get("created_at") or ticket["created_at"])
        reference_time_raw = str(payload.get("reference_time") or datetime.now(UTC).isoformat())

        created_at = _parse_timestamp(created_at_raw)
        reference_time = _parse_timestamp(reference_time_raw)
        hours_open = max((reference_time - created_at).total_seconds() / 3600.0, 0.0)
        updated_urgency = self._calculate_aged_urgency(previous_urgency, hours_open)

        update_ticket(ticket_id, {"urgency_score": updated_urgency})

        return {
            "ticket_id": ticket_id,
            "previous_urgency": previous_urgency,
            "updated_urgency": updated_urgency,
            "hours_open": hours_open,
        }


_service: UrgencyService | None = None


def get_urgency_service() -> UrgencyService:
    """Return a singleton urgency service instance."""
    global _service
    if _service is None:
        _service = UrgencyService()
    return _service


def update_urgency(payload: UrgencyUpdateInput) -> UrgencyUpdateResult:
    """Compatibility helper matching the technical document wording."""
    return get_urgency_service().update_urgency(payload)


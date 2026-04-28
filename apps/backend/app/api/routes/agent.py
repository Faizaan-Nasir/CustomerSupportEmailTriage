"""Routes for agent-triggered actions."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.repositories.message_repo import create_message
from app.repositories.supabase_client import get_client
from app.repositories.ticket_repo import get_ticket_repository, update_ticket


router = APIRouter(prefix="/agent", tags=["agent"])


class AgentActionRequest(BaseModel):
    """Payload for human-triggered ticket actions."""

    ticket_id: str
    action: Literal["reply", "escalate", "resolve"]
    data: dict[str, Any] = Field(default_factory=dict)


class AgentActionResponse(BaseModel):
    """Result payload after a human-triggered ticket action is applied."""

    ticket_id: str
    action: str
    status: str
    message_id: str | None = None


def _update_ticket(ticket_id: str, updates: dict[str, Any]) -> None:
    update_ticket(ticket_id, updates)


@router.post("/action", response_model=AgentActionResponse)
async def send_agent_action(payload: AgentActionRequest) -> AgentActionResponse:
    """Apply an agent-selected action and persist the resulting ticket state."""
    ticket_id = payload.ticket_id.strip()
    if not ticket_id:
        raise HTTPException(status_code=400, detail="ticket_id is required.")

    try:
        ticket = get_ticket_repository().get_ticket(ticket_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=f"Ticket not found: {ticket_id}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    current_interaction_count = int(ticket.get("interaction_count") or 0)
    message_id: str | None = None

    try:
        if payload.action == "reply":
            content = str(payload.data.get("content") or "").strip()
            if not content:
                raise HTTPException(status_code=400, detail="Reply action requires data.content.")

            created = create_message(
                {
                    "ticket_id": ticket_id,
                    "sender": "agent",
                    "content": content,
                }
            )
            message_id = created["id"]
            _update_ticket(
                ticket_id,
                {
                    "status": "open",
                    "interaction_count": current_interaction_count + 1,
                },
            )
            status = "open"
        elif payload.action == "escalate":
            note = str(payload.data.get("note") or "").strip()
            if note:
                created = create_message(
                    {
                        "ticket_id": ticket_id,
                        "sender": "agent",
                        "content": note,
                    }
                )
                message_id = created["id"]

            _update_ticket(ticket_id, {"status": "escalated"})
            status = "escalated"
        else:
            resolution_note = str(payload.data.get("note") or "").strip()
            if resolution_note:
                created = create_message(
                    {
                        "ticket_id": ticket_id,
                        "sender": "agent",
                        "content": resolution_note,
                    }
                )
                message_id = created["id"]

            _update_ticket(ticket_id, {"status": "resolved"})
            status = "resolved"
    except HTTPException:
        raise
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AgentActionResponse(
        ticket_id=ticket_id,
        action=payload.action,
        status=status,
        message_id=message_id,
    )

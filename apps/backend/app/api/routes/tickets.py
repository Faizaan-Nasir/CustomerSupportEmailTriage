"""Routes for ticket retrieval."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.repositories.entity_repo import list_entities_for_ticket
from app.repositories.interpretation_repo import get_interpretation_repository
from app.repositories.message_repo import list_messages_for_ticket
from app.repositories.supabase_client import get_client
from app.repositories.ticket_repo import get_ticket_repository


router = APIRouter(prefix="/tickets", tags=["tickets"])


class TicketListItem(BaseModel):
    """Compact ticket payload for dashboard-style list views."""

    id: str
    subject: str | None
    status: str
    urgency_score: float


class InterpretationDetail(BaseModel):
    """Latest interpretation associated with a ticket."""

    id: str
    intent: str | None
    category: str | None
    sentiment: str | None
    urgency: float | None
    confidence: float | None
    reasoning: str | None
    created_at: str


class EntityDetail(BaseModel):
    """Structured entity extracted for a ticket."""

    id: str
    key: str
    value: str
    source: str | None
    confidence: float | None
    created_at: str


class MessageDetail(BaseModel):
    """Message thread item associated with a ticket."""

    id: str
    sender: str
    content: str
    timestamp: str


class AgentActionDetail(BaseModel):
    """Latest stored agent action plan for a ticket."""

    id: str
    summary: str | None
    action_plan: str | None
    escalation_target: str | None
    generated_at: str


class TicketDetailResponse(BaseModel):
    """Full ticket detail payload used by the detail view."""

    id: str
    subject: str | None
    body: str | None
    interpretation: InterpretationDetail | None
    entities: list[EntityDetail]
    messages: list[MessageDetail]
    agent_action: AgentActionDetail | None


def _get_latest_agent_action(ticket_id: str) -> AgentActionDetail | None:
    rows = (
        get_client()
        .table("agent_actions")
        .select("*")
        .eq("ticket_id", ticket_id)
        .order("generated_at", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        return None

    row = dict(rows[0])
    return AgentActionDetail(
        id=row["id"],
        summary=row.get("summary"),
        action_plan=row.get("action_plan"),
        escalation_target=row.get("escalation_target"),
        generated_at=row["generated_at"],
    )


@router.get("", response_model=list[TicketListItem])
async def get_tickets(limit: int = Query(default=50, ge=1, le=100)) -> list[TicketListItem]:
    """Return recent tickets for dashboard and API smoke-test usage."""
    try:
        tickets = get_ticket_repository().list_tickets(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return [
        TicketListItem(
            id=ticket["id"],
            subject=ticket.get("subject"),
            status=str(ticket.get("status") or "open"),
            urgency_score=float(ticket.get("urgency_score") or 0.0),
        )
        for ticket in tickets
    ]


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket_by_id(ticket_id: str) -> TicketDetailResponse:
    """Return a full ticket view including interpretation, entities, messages, and agent plan."""
    try:
        ticket = get_ticket_repository().get_ticket(ticket_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=f"Ticket not found: {ticket_id}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        interpretation_record = get_interpretation_repository().get_latest_interpretation_for_ticket(ticket_id)
    except LookupError:
        interpretation = None
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    else:
        interpretation = InterpretationDetail(
            id=interpretation_record["id"],
            intent=interpretation_record.get("intent"),
            category=interpretation_record.get("category"),
            sentiment=interpretation_record.get("sentiment"),
            urgency=float(interpretation_record["urgency"])
            if interpretation_record.get("urgency") is not None
            else None,
            confidence=float(interpretation_record["confidence"])
            if interpretation_record.get("confidence") is not None
            else None,
            reasoning=interpretation_record.get("reasoning"),
            created_at=interpretation_record["created_at"],
        )

    try:
        entities = [
            EntityDetail(
                id=entity["id"],
                key=entity["key"],
                value=entity["value"],
                source=entity.get("source"),
                confidence=float(entity["confidence"]) if entity.get("confidence") is not None else None,
                created_at=entity["created_at"],
            )
            for entity in list_entities_for_ticket(ticket_id)
        ]
        messages = [
            MessageDetail(
                id=message["id"],
                sender=message["sender"],
                content=message["content"],
                timestamp=message["timestamp"],
            )
            for message in list_messages_for_ticket(ticket_id)
        ]
        agent_action = _get_latest_agent_action(ticket_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return TicketDetailResponse(
        id=ticket["id"],
        subject=ticket.get("subject"),
        body=ticket.get("body"),
        interpretation=interpretation,
        entities=entities,
        messages=messages,
        agent_action=agent_action,
    )

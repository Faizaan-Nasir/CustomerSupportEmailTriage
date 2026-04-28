"""Routes for ticket retrieval."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.repositories.attachment_repo import get_attachment
from app.repositories.attachment_repo import list_attachments_for_ticket
from app.repositories.entity_repo import list_entities_for_ticket
from app.repositories.entity_repo import update_entity as update_entity_record
from app.repositories.interpretation_repo import get_interpretation_repository
from app.repositories.message_repo import list_messages_for_ticket
from app.repositories.supabase_client import get_client
from app.repositories.ticket_repo import get_ticket_repository
from app.services.requirement_inference_service import infer_requirements


router = APIRouter(prefix="/tickets", tags=["tickets"])


class TicketListItem(BaseModel):
    """Compact ticket payload for dashboard-style list views."""

    id: str
    customer_email: str
    subject: str | None
    status: str
    urgency_score: float
    priority_label: str
    priority_rank: int
    created_at: str


class AttachmentDetail(BaseModel):
    """Attachment metadata exposed to the frontend detail view."""

    id: str
    file_url: str | None
    preview_url: str | None
    parsed_text: str | None
    created_at: str


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
    action_plan: list[str]
    escalation_target: str | None
    generated_at: str


class EntityUpdateRequest(BaseModel):
    """Editable entity update payload for the dashboard."""

    key: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1)
    source: str | None = None
    confidence: float | None = None


class TicketDetailResponse(BaseModel):
    """Full ticket detail payload used by the detail view."""

    id: str
    customer_email: str
    subject: str | None
    body: str | None
    status: str
    urgency_score: float
    interaction_count: int
    created_at: str
    updated_at: str
    interpretation: InterpretationDetail | None
    entities: list[EntityDetail]
    required_fields: list[str]
    attachments: list[AttachmentDetail]
    messages: list[MessageDetail]
    agent_action: AgentActionDetail | None


def _priority_metadata(urgency_score: float, confidence: float | None) -> tuple[str, int]:
    if confidence is None or confidence < settings.confidence_threshold:
        return "uncertain", 0

    if urgency_score >= 0.7:
        return "high", 1

    if urgency_score >= 0.4:
        return "medium", 2

    return "low", 3


def _parse_action_plan(value: str | None) -> list[str]:
    if not value:
        return []
    steps: list[str] = []
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        steps.append(line)
    return steps


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
        action_plan=_parse_action_plan(row.get("action_plan")),
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

    list_items: list[TicketListItem] = []
    interpretation_repo = get_interpretation_repository()

    for ticket in tickets:
        confidence: float | None = None
        try:
            latest_interpretation = interpretation_repo.get_latest_interpretation_for_ticket(ticket["id"])
        except LookupError:
            latest_interpretation = None
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        else:
            confidence_raw = latest_interpretation.get("confidence") if latest_interpretation else None
            confidence = float(confidence_raw) if confidence_raw is not None else None

        urgency_score = float(ticket.get("urgency_score") or 0.0)
        priority_label, priority_rank = _priority_metadata(urgency_score, confidence)

        list_items.append(
            TicketListItem(
                id=ticket["id"],
                customer_email=ticket["customer_email"],
                subject=ticket.get("subject"),
                status=str(ticket.get("status") or "open"),
                urgency_score=urgency_score,
                priority_label=priority_label,
                priority_rank=priority_rank,
                created_at=ticket["created_at"],
            )
        )

    return list_items


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
        attachments = [
            AttachmentDetail(
                id=attachment["id"],
                file_url=attachment.get("file_url"),
                preview_url=(
                    f"/tickets/{ticket_id}/attachments/{attachment['id']}/content"
                    if attachment.get("file_url")
                    else None
                ),
                parsed_text=attachment.get("parsed_text"),
                created_at=attachment["created_at"],
            )
            for attachment in list_attachments_for_ticket(ticket_id)
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
        required_fields = infer_requirements(
            {
                "intent": interpretation.intent if interpretation else "",
                "category": interpretation.category if interpretation else "",
                "entities": [entity.model_dump() for entity in entities],
            }
        )["required_fields"]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return TicketDetailResponse(
        id=ticket["id"],
        customer_email=ticket["customer_email"],
        subject=ticket.get("subject"),
        body=ticket.get("body"),
        status=str(ticket.get("status") or "open"),
        urgency_score=float(ticket.get("urgency_score") or 0.0),
        interaction_count=int(ticket.get("interaction_count") or 0),
        created_at=ticket["created_at"],
        updated_at=ticket["updated_at"],
        interpretation=interpretation,
        entities=entities,
        required_fields=required_fields,
        attachments=attachments,
        messages=messages,
        agent_action=agent_action,
    )


@router.get("/{ticket_id}/attachments/{attachment_id}/content")
async def get_ticket_attachment_content(ticket_id: str, attachment_id: str) -> FileResponse:
    """Serve attachment content for frontend preview/download flows."""
    try:
        attachment = get_attachment(attachment_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=f"Attachment not found: {attachment_id}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if attachment["ticket_id"] != ticket_id:
        raise HTTPException(
            status_code=400,
            detail=f"Attachment {attachment_id} does not belong to ticket {ticket_id}.",
        )

    file_url = attachment.get("file_url")
    if not file_url:
        raise HTTPException(status_code=404, detail=f"Attachment file is unavailable: {attachment_id}")
    # Support Supabase-stored files (supabase://bucket/path) as well as local paths
    if isinstance(file_url, str) and file_url.startswith("supabase://"):
        # Format: supabase://{bucket}/{object_path}
        _, rest = file_url.split("supabase://", 1)
        parts = rest.split("/", 1)
        if len(parts) != 2:
            raise HTTPException(status_code=500, detail="Invalid Supabase file_url format.")
        bucket, object_path = parts[0], parts[1]
        try:
            client = get_client()
            signed = client.storage.from_(bucket).create_signed_url(object_path, 60)
            url = signed.get("signedURL") or signed.get("signedUrl") or signed.get("signedURL")
            if not url:
                raise RuntimeError("Failed to create signed URL")
            return RedirectResponse(url)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    path = Path(file_url).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Attachment file not found: {path}")

    return FileResponse(path)


@router.patch("/{ticket_id}/entities/{entity_id}", response_model=EntityDetail)
async def update_ticket_entity(
    ticket_id: str,
    entity_id: str,
    payload: EntityUpdateRequest,
) -> EntityDetail:
    """Persist edits to an extracted entity for dashboard workflows."""
    try:
        existing = get_client().table("entities").select("*").eq("id", entity_id).limit(1).execute().data or []
        if not existing:
            raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")
        row = dict(existing[0])
        if row["ticket_id"] != ticket_id:
            raise HTTPException(
                status_code=400,
                detail=f"Entity {entity_id} does not belong to ticket {ticket_id}.",
            )

        updated = update_entity_record(
            entity_id,
            {
                "key": payload.key.strip(),
                "value": payload.value.strip(),
                "source": payload.source.strip() if payload.source else row.get("source"),
                "confidence": payload.confidence if payload.confidence is not None else row.get("confidence"),
            },
        )
    except HTTPException:
        raise
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return EntityDetail(
        id=updated["id"],
        key=updated["key"],
        value=updated["value"],
        source=updated.get("source"),
        confidence=float(updated["confidence"]) if updated.get("confidence") is not None else None,
        created_at=updated["created_at"],
    )

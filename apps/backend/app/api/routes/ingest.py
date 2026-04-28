"""Routes for incoming email ingestion."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.rag.indexer import index_attachment
from app.rag.parser import parse_file
from app.services.agent_assist_service import generate_agent_plan
from app.services.communication_service import generate_email
from app.services.decision_service import decide_next_action
from app.services.entity_extraction_service import extract_entities
from app.services.ingestion_service import ingest_email
from app.services.interpretation_service import interpret_email
from app.services.requirement_inference_service import infer_requirements


router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestRequest(BaseModel):
    """Request payload for ticket ingestion."""

    email: str = Field(..., description="Raw email body content")
    subject: str = Field(..., description="Email subject line")
    attachments: list[str] = Field(default_factory=list, description="Local attachment file paths")
    customer_email: str = Field(..., description="Customer email address")
    sender: str = Field(default="customer", description="Original sender role label")


class IngestResponse(BaseModel):
    """Minimal response payload for a processed ticket."""

    ticket_id: str
    status: str


def _index_attachments(ticket_id: str, attachments: list[str], query_text: str) -> None:
    for attachment in attachments:
        path = Path(attachment).expanduser().resolve()
        if not path.exists():
            raise HTTPException(status_code=400, detail=f"Attachment file not found: {path}")

        parsed = parse_file(str(path))
        index_attachment(ticket_id, str(path), parsed["text"])


@router.post("", response_model=IngestResponse)
async def ingest_ticket(payload: IngestRequest) -> IngestResponse:
    """Run the full backend pipeline for an incoming support email."""
    try:
        ingested = ingest_email(
            {
                "customer_email": payload.customer_email,
                "subject": payload.subject,
                "body": payload.email,
                "sender": payload.sender,
            }
        )
        ticket_id = ingested["ticket_id"]

        if payload.attachments:
            _index_attachments(ticket_id, payload.attachments, payload.email)

        interpretation = interpret_email({"ticket_id": ticket_id, "body": payload.email})
        extraction = extract_entities({"ticket_id": ticket_id, "body": payload.email})
        requirements = infer_requirements(
            {
                "intent": interpretation["intent"],
                "category": interpretation["category"],
                "entities": extraction["entities"],
            }
        )
        decision = decide_next_action(
            {
                "intent": interpretation["intent"],
                "category": interpretation["category"],
                "confidence": interpretation["confidence"],
                "urgency": interpretation["urgency"],
                "required_fields": requirements["required_fields"],
                "interaction_count": 0,
            }
        )
        generate_email(
            {
                "intent": interpretation["intent"],
                "category": interpretation["category"],
                "sentiment": interpretation["sentiment"],
                "confidence": interpretation["confidence"],
                "required_fields": requirements["required_fields"],
                "ask_for_info": decision["ask_for_info"],
            }
        )
        generate_agent_plan(
            {
                "ticket_id": ticket_id,
                "intent": interpretation["intent"],
                "category": interpretation["category"],
                "sentiment": interpretation["sentiment"],
                "entities": extraction["entities"],
                "required_fields": requirements["required_fields"],
                "escalate": decision["escalate"],
                "escalation_target": decision["escalation_target"],
            }
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return IngestResponse(ticket_id=ticket_id, status="processed")

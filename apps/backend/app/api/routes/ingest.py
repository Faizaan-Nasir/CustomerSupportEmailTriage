"""Routes for incoming email ingestion."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.rag.indexer import index_attachment
from app.rag.parser import parse_file
from app.repositories.supabase_client import get_client as get_supabase_client
from app.repositories.ticket_repo import update_ticket
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
    thread_id: str | None = Field(None, description="External thread identifier")


class IngestResponse(BaseModel):
    """Minimal response payload for a processed ticket."""

    ticket_id: str
    status: str
    email_body: str | None = None
    escalated: bool = False
    escalation_target: str | None = None


def _index_attachments(ticket_id: str, attachments: list[str], query_text: str) -> None:
    for attachment in attachments:
        path = Path(attachment).expanduser().resolve()
        if not path.exists():
            raise HTTPException(status_code=400, detail=f"Attachment file not found: {path}")

        parsed = parse_file(str(path))
        try:
            index_attachment(ticket_id, str(path), parsed["text"])
        except Exception:
            # Non-fatal: continue ingestion even if indexing fails
            continue


def _uploads_root() -> Path:
    return Path(__file__).resolve().parents[3] / "uploads"


async def _save_uploaded_attachments(ticket_id: str, attachments: list[UploadFile], query_text: str) -> None:
    if not attachments:
        return

    ticket_uploads_root = _uploads_root() / ticket_id
    ticket_uploads_root.mkdir(parents=True, exist_ok=True)

    for attachment in attachments:
        if not attachment.filename:
            raise HTTPException(status_code=400, detail="Each attachment must have a filename.")

        target_path = ticket_uploads_root / Path(attachment.filename).name
        content = await attachment.read()
        target_path.write_bytes(content)
        # Parse locally for RAG indexing
        parsed = parse_file(str(target_path))

        # Upload to Supabase storage bucket `attachments` (private). Store storage path in DB.
        try:
            supabase = get_supabase_client()
            bucket = "attachments"
            object_path = f"{ticket_id}/{target_path.name}"
            # Use local file upload API to send file bytes
            supabase.storage.from_(bucket).upload(object_path, str(target_path))
            file_url = f"supabase://{bucket}/{object_path}"
        except Exception:
            # On failure to upload, fall back to local file path so ingestion can continue
            file_url = str(target_path)

        try:
            index_attachment(ticket_id, file_url, parsed["text"])
        except Exception:
            # Non-fatal: continue ingestion even if indexing fails
            continue


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
                "thread_id": payload.thread_id,
            }
        )
        ticket_id = ingested["ticket_id"]
        
        from app.repositories.message_repo import list_messages_for_ticket
        messages = list_messages_for_ticket(ticket_id)
        # Convert message records to a simple list of dicts for context
        context = [{"sender": m["sender"], "content": m["content"]} for m in messages]

        if payload.attachments:
            _index_attachments(ticket_id, payload.attachments, payload.email)

        interpretation = interpret_email({"ticket_id": ticket_id, "body": payload.email, "context": context})
        extraction = extract_entities({"ticket_id": ticket_id, "body": payload.email, "context": context})
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
                "interaction_count": len(messages),
            }
        )

        if decision["escalate"]:
            update_ticket(ticket_id, {"status": "escalated"})

        comms = generate_email(
            {
                "intent": interpretation["intent"],
                "category": interpretation["category"],
                "sentiment": interpretation["sentiment"],
                "confidence": interpretation["confidence"],
                "required_fields": requirements["required_fields"],
                "ask_for_info": decision["ask_for_info"],
                "context": context,
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

    return IngestResponse(
        ticket_id=ticket_id, 
        status="processed", 
        email_body=comms["email_body"],
        escalated=bool(decision["escalate"]),
        escalation_target=decision["escalation_target"]
    )


@router.post("/upload", response_model=IngestResponse)
async def ingest_uploaded_ticket(
    email: str = Form(...),
    subject: str = Form(...),
    customer_email: str = Form(...),
    sender: str = Form(default="customer"),
    thread_id: str | None = Form(default=None),
    attachments: list[UploadFile] = File(default_factory=list),
) -> IngestResponse:
    """Run the full backend pipeline for a browser-submitted support email."""
    try:
        ingested = ingest_email(
            {
                "customer_email": customer_email,
                "subject": subject,
                "body": email,
                "sender": sender,
                "thread_id": thread_id,
            }
        )
        ticket_id = ingested["ticket_id"]

        from app.repositories.message_repo import list_messages_for_ticket
        messages = list_messages_for_ticket(ticket_id)
        # Convert message records to a simple list of dicts for context
        context = [{"sender": m["sender"], "content": m["content"]} for m in messages]

        if attachments:
            await _save_uploaded_attachments(ticket_id, attachments, email)

        interpretation = interpret_email({"ticket_id": ticket_id, "body": email, "context": context})
        extraction = extract_entities({"ticket_id": ticket_id, "body": email, "context": context})
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
                "interaction_count": len(messages),
            }
        )

        if decision["escalate"]:
            update_ticket(ticket_id, {"status": "escalated"})

        comms = generate_email(
            {
                "intent": interpretation["intent"],
                "category": interpretation["category"],
                "sentiment": interpretation["sentiment"],
                "confidence": interpretation["confidence"],
                "required_fields": requirements["required_fields"],
                "ask_for_info": decision["ask_for_info"],
                "context": context,
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

    return IngestResponse(
        ticket_id=ticket_id, 
        status="processed", 
        email_body=comms["email_body"],
        escalated=bool(decision["escalate"]),
        escalation_target=decision["escalation_target"]
    )

"""Service for extracting structured entities from tickets."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, TypedDict

from app.llm.client import get_client
from app.llm.structured_output import validate_structured_output
from app.rag.retriever import retrieve_relevant_chunks
from app.repositories.entity_repo import create_entity, list_entities_for_ticket


class EntityExtractionInput(TypedDict, total=False):
    """Input contract for ticket entity extraction."""

    ticket_id: str
    body: str
    subject: str
    query: str
    top_k: int
    context: list[dict[str, str]] | None


class ExtractedEntity(TypedDict, total=False):
    """Normalized entity payload used across downstream layers."""

    entity_id: str
    key: str
    value: str
    source: str
    confidence: float


class EntityExtractionResult(TypedDict):
    """Result contract for stored entities plus retrieved context."""

    ticket_id: str
    entities: list[ExtractedEntity]
    rag_chunks: list[str]


ENTITY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["entities"],
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["key", "value", "source", "confidence"],
                "properties": {
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                    "source": {"type": "string"},
                    "confidence": {"type": "number"},
                },
            },
        }
    },
}


SUPPORTED_ENTITY_KEYS: set[str] = {
    "order_id",
    "invoice_id",
    "tracking_number",
    "transaction_reference",
    "payment_method",
    "product_name",
    "order_date",
    "delivery_address",
    "account_email",
}


REGEX_PATTERNS: dict[str, re.Pattern[str]] = {
    "order_id": re.compile(
        r"\border\s*(?:id|number)?\s*[:#-]?\s*([A-Z]{2,5}-\d{3,}|\d{5,}|ORD-\d+)\b",
        re.IGNORECASE,
    ),
    "invoice_id": re.compile(
        r"\binvoice\s*(?:id|number)?\s*[:#-]?\s*([A-Z]{2,5}-\d{3,}|\d{5,}|INV-\d+)\b",
        re.IGNORECASE,
    ),
    "tracking_number": re.compile(
        r"\btracking\s*(?:id|number)?\s*[:#-]?\s*([A-Z0-9-]{8,})\b",
        re.IGNORECASE,
    ),
    "transaction_reference": re.compile(
        r"\b(?:transaction|payment)\s*(?:id|reference|ref)?\s*[:#-]?\s*([A-Z0-9-]{6,})\b",
        re.IGNORECASE,
    ),
}


def _normalize_label(value: str) -> str:
    cleaned = "_".join(value.strip().lower().replace("/", " ").replace("-", " ").split())
    return cleaned or "unknown"


def _clamp_score(value: Any) -> float:
    numeric = float(value)
    if numeric < 0.0:
        return 0.0
    if numeric > 1.0:
        return 1.0
    return numeric


def _dedupe_key(entity: ExtractedEntity) -> tuple[str, str]:
    return (_normalize_label(entity["key"]), entity["value"].strip().lower())


def _looks_like_specific_value(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    if len(stripped) > 120:
        return False
    if "\n" in stripped:
        return False
    return True


def _keyword_candidates(body: str) -> list[str]:
    lowered = body.lower()
    keywords = {"order", "invoice", "tracking", "transaction", "payment"}

    if any(term in lowered for term in {"refund", "charged", "billing", "invoice", "payment"}):
        keywords.update({"refund", "charge", "billing", "card"})
    if any(term in lowered for term in {"shipping", "delivery", "tracking"}):
        keywords.update({"shipping", "delivery", "address"})
    if any(term in lowered for term in {"product", "defect", "damaged"}):
        keywords.update({"product", "defect", "damaged"})
    if any(term in lowered for term in {"account", "login", "password"}):
        keywords.update({"account", "login", "email"})

    return sorted(keywords)


def _relevant_attachment_context(body: str, rag_chunks: list[str], *, line_limit: int = 12) -> list[str]:
    keywords = _keyword_candidates(body)
    narrowed_chunks: list[str] = []

    for chunk in rag_chunks:
        matched_lines: list[str] = []
        for line in chunk.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            lowered = stripped.lower()
            if any(keyword in lowered for keyword in keywords):
                matched_lines.append(stripped)
            if len(matched_lines) >= line_limit:
                break

        if matched_lines:
            narrowed_chunks.append("\n".join(matched_lines))

    return narrowed_chunks


@dataclass
class EntityExtractionService:
    """Extract structured entities from email body content and retrieved attachments."""

    def _extract_with_regex(self, body: str, subject: str, rag_chunks: list[str]) -> list[ExtractedEntity]:
        combined_text = "\n".join([subject, body, *rag_chunks])
        entities: list[ExtractedEntity] = []

        for key, pattern in REGEX_PATTERNS.items():
            for match in pattern.finditer(combined_text):
                value = match.group(1).strip()
                if not _looks_like_specific_value(value):
                    continue
                # Determine source based on where the match was found
                if match.start() < len(subject):
                    source = "email_subject"
                elif match.start() < len(subject) + len(body) + 1:
                    source = "email_body"
                else:
                    source = "rag_attachment"

                entities.append(
                    {
                        "key": key,
                        "value": value,
                        "source": source,
                        "confidence": 0.95,
                    }
                )

        return entities

    def _build_prompt(self, body: str, subject: str, rag_chunks: list[str], context: list[dict[str, str]] | None = None) -> str:
        context_str = ""
        if context:
            context_str = "Conversation history:\n"
            for msg in context:
                context_str += f"- {msg.get('sender', 'unknown')}: {msg.get('content', '')}\n"
            context_str += "\n"

        rag_block = "\n\n".join(
            f"Attachment chunk {index + 1}:\n{chunk}" for index, chunk in enumerate(rag_chunks)
        )
        return f"""
You are extracting structured customer-support entities from an email interaction and its related attachment excerpts.

Return only information that is explicitly supported by the text. Focus on identifiers and actionable details
that help reduce unnecessary follow-up requests.

{context_str}

Important examples of useful entities:
- order_id
- invoice_id
- tracking_number
- transaction_reference
- payment_method
- product_name
- order_date
- delivery_address
- account_email

Restrictions:
- Return only the supported keys listed above.
- Extract only customer-resolution details tied to this specific ticket.
- Ignore generic examples, documentation text, headings, repeated template content, and unrelated identifiers.
- If attachment text is broad or reference-like, be conservative and return fewer entities rather than guessing.
- Do not return more than 8 entities.

For each entity return:
- key: normalized snake_case label
- value: exact extracted value when possible
- source: one of email_subject, email_body, or rag_attachment
- confidence: a score from 0.0 to 1.0

Return JSON only in this format:
{{"entities": [{{"key": "...", "value": "...", "source": "...", "confidence": 0.9}}]}}

Current Email Subject:
\"\"\"
{subject}
\"\"\"

Current Email body:
\"\"\"
{body}
\"\"\"

Attachment context (derived from indexed files):
\"\"\"
{rag_block or "No attachment context available."}
\"\"\"
""".strip()

    def extract_entities(self, payload: EntityExtractionInput) -> EntityExtractionResult:
        """Extract entities, persist them, and return the normalized result."""
        ticket_id = (payload.get("ticket_id") or "").strip()
        body = (payload.get("body") or "").strip()
        subject = (payload.get("subject") or "").strip()
        context = payload.get("context")
        
        # Build an aggressive RAG query combining history and current body to surface all relevant attachment details
        query_parts = []
        if context:
            for msg in context[-3:]:  # Last few messages for focus
                query_parts.append(msg.get("content", ""))
        query_parts.append(subject)
        query_parts.append(body)
        query = "\n".join(query_parts).strip()
        
        top_k = int(payload.get("top_k") or 5)  # Increased k for better recall in threads

        if not ticket_id:
            raise ValueError("ticket_id is required.")
        if not body:
            raise ValueError("body is required.")

        rag_chunks = retrieve_relevant_chunks(query=query, ticket_id=ticket_id, top_k=top_k)["chunks"]
        filtered_rag_chunks = _relevant_attachment_context(body, rag_chunks)
        regex_entities = self._extract_with_regex(body, subject, filtered_rag_chunks)

        llm_response = get_client().generate_text(
            self._build_prompt(body, subject, filtered_rag_chunks, context),
            temperature=0.1,
            expect_json=True,
        )
        validated = validate_structured_output(llm_response["text"], ENTITY_SCHEMA)["validated_json"]

        # Seed merged map with EXISTING entities to prevent "losing" data across interaction turns
        existing_entities = list_entities_for_ticket(ticket_id)
        merged: dict[tuple[str, str], ExtractedEntity] = {}
        
        for entity in existing_entities:
            normalized = {
                "key": _normalize_label(entity["key"]),
                "value": entity["value"].strip(),
                "source": entity.get("source") or "unknown",
                "confidence": _clamp_score(entity.get("confidence") or 1.0),
            }
            merged[_dedupe_key(normalized)] = normalized

        for entity in regex_entities:
            normalized = {
                "key": _normalize_label(entity["key"]),
                "value": entity["value"].strip(),
                "source": entity["source"],
                "confidence": _clamp_score(entity["confidence"]),
            }
            if normalized["key"] not in SUPPORTED_ENTITY_KEYS:
                continue
            dedupe = _dedupe_key(normalized)
            current = merged.get(dedupe)
            if current is None or normalized["confidence"] > current["confidence"]:
                merged[dedupe] = normalized

        for entity in validated["entities"]:
            normalized = {
                "key": _normalize_label(entity["key"]),
                "value": entity["value"].strip(),
                "source": _normalize_label(entity["source"]),
                "confidence": _clamp_score(entity["confidence"]),
            }
            if normalized["key"] not in SUPPORTED_ENTITY_KEYS:
                continue
            if not _looks_like_specific_value(normalized["value"]):
                continue
            dedupe = _dedupe_key(normalized)
            current = merged.get(dedupe)
            if current is None or normalized["confidence"] > current["confidence"]:
                merged[dedupe] = normalized

        persisted_entities: list[ExtractedEntity] = []
        for entity in merged.values():
            # Only create NEW entities (that don't have an ID yet) to avoid duplicates in DB
            # Note: In a real production system we might update existing ones if confidence is higher,
            # but for this prototype, appending unique key-value pairs is sufficient.
            
            # Check if this exact key-value pair already exists in DB to avoid re-insertion
            # (merged already deduped them locally)
            exists = any(
                e["key"] == entity["key"] and e["value"] == entity["value"]
                for e in existing_entities
            )
            
            if not exists:
                created = create_entity(
                    {
                        "ticket_id": ticket_id,
                        "key": entity["key"],
                        "value": entity["value"],
                        "source": entity["source"],
                        "confidence": entity["confidence"],
                    }
                )
                persisted_entities.append(
                    {
                        "entity_id": created["id"],
                        "key": entity["key"],
                        "value": entity["value"],
                        "source": entity["source"],
                        "confidence": entity["confidence"],
                    }
                )
            else:
                # Find the existing record to include in result
                for e in existing_entities:
                    if e["key"] == entity["key"] and e["value"] == entity["value"]:
                        persisted_entities.append(
                            {
                                "entity_id": e["id"],
                                "key": e["key"],
                                "value": e["value"],
                                "source": e.get("source") or "email_body",
                                "confidence": e.get("confidence") or 1.0,
                            }
                        )
                        break

        return {
            "ticket_id": ticket_id,
            "entities": persisted_entities,
            "rag_chunks": filtered_rag_chunks,
        }


_service: EntityExtractionService | None = None


def get_entity_extraction_service() -> EntityExtractionService:
    """Return a singleton entity extraction service instance."""
    global _service
    if _service is None:
        _service = EntityExtractionService()
    return _service


def extract_entities(payload: EntityExtractionInput) -> EntityExtractionResult:
    """Compatibility helper matching the technical document wording."""
    return get_entity_extraction_service().extract_entities(payload)

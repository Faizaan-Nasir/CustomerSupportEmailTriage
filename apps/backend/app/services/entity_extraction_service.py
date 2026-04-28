"""Service for extracting structured entities from tickets."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, TypedDict

from app.llm.client import get_client
from app.llm.structured_output import validate_structured_output
from app.rag.retriever import retrieve_relevant_chunks
from app.repositories.entity_repo import create_entity


class EntityExtractionInput(TypedDict, total=False):
    """Input contract for ticket entity extraction."""

    ticket_id: str
    body: str
    query: str
    top_k: int


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


REGEX_PATTERNS: dict[str, re.Pattern[str]] = {
    "order_id": re.compile(r"\b(?:order\s*(?:id|number)?\s*[:#-]?\s*)?([A-Z]{2,5}-\d{3,}|\bORD-\d+\b)", re.IGNORECASE),
    "invoice_id": re.compile(r"\b(?:invoice\s*(?:id|number)?\s*[:#-]?\s*)?([A-Z]{2,5}-\d{3,}|\bINV-\d+\b)", re.IGNORECASE),
    "tracking_number": re.compile(r"\b(?:tracking\s*(?:id|number)?\s*[:#-]?\s*)?([A-Z0-9]{8,})\b", re.IGNORECASE),
    "transaction_reference": re.compile(r"\b(?:transaction|payment)\s*(?:id|reference|ref)?\s*[:#-]?\s*([A-Z0-9-]{6,})\b", re.IGNORECASE),
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


@dataclass
class EntityExtractionService:
    """Extract structured entities from email body content and retrieved attachments."""

    def _extract_with_regex(self, body: str, rag_chunks: list[str]) -> list[ExtractedEntity]:
        combined_text = "\n".join([body, *rag_chunks])
        entities: list[ExtractedEntity] = []

        for key, pattern in REGEX_PATTERNS.items():
            for match in pattern.finditer(combined_text):
                value = match.group(1).strip()
                if not value:
                    continue
                source = "email_body" if match.start() < len(body) else "rag_attachment"
                entities.append(
                    {
                        "key": key,
                        "value": value,
                        "source": source,
                        "confidence": 0.95,
                    }
                )

        return entities

    def _build_prompt(self, body: str, rag_chunks: list[str]) -> str:
        rag_block = "\n\n".join(
            f"Attachment chunk {index + 1}:\n{chunk}" for index, chunk in enumerate(rag_chunks)
        )
        return f"""
You are extracting structured customer-support entities from an email and its related attachment excerpts.

Return only information that is explicitly supported by the text. Focus on identifiers and actionable details
that help reduce unnecessary follow-up requests.

Important examples of useful entities:
- order_id
- invoice_id
- tracking_number
- transaction_reference
- payment_method
- product_name
- order_date
- delivery_address

For each entity return:
- key: normalized snake_case label
- value: exact extracted value when possible
- source: one of email_body or rag_attachment
- confidence: a score from 0.0 to 1.0

Return JSON only in this format:
{{"entities": [{{"key": "...", "value": "...", "source": "...", "confidence": 0.9}}]}}

Email body:
\"\"\"
{body}
\"\"\"

Attachment context:
\"\"\"
{rag_block or "No attachment context available."}
\"\"\"
""".strip()

    def extract_entities(self, payload: EntityExtractionInput) -> EntityExtractionResult:
        """Extract entities, persist them, and return the normalized result."""
        ticket_id = (payload.get("ticket_id") or "").strip()
        body = (payload.get("body") or "").strip()
        query = (payload.get("query") or body).strip()
        top_k = int(payload.get("top_k") or 3)

        if not ticket_id:
            raise ValueError("ticket_id is required.")
        if not body:
            raise ValueError("body is required.")

        rag_chunks = retrieve_relevant_chunks(query=query, ticket_id=ticket_id, top_k=top_k)["chunks"]
        regex_entities = self._extract_with_regex(body, rag_chunks)

        llm_response = get_client().generate_text(
            self._build_prompt(body, rag_chunks),
            temperature=0.1,
            expect_json=True,
        )
        validated = validate_structured_output(llm_response["text"], ENTITY_SCHEMA)["validated_json"]

        merged: dict[tuple[str, str], ExtractedEntity] = {}
        for entity in regex_entities:
            normalized = {
                "key": _normalize_label(entity["key"]),
                "value": entity["value"].strip(),
                "source": entity["source"],
                "confidence": _clamp_score(entity["confidence"]),
            }
            merged[_dedupe_key(normalized)] = normalized

        for entity in validated["entities"]:
            normalized = {
                "key": _normalize_label(entity["key"]),
                "value": entity["value"].strip(),
                "source": _normalize_label(entity["source"]),
                "confidence": _clamp_score(entity["confidence"]),
            }
            dedupe = _dedupe_key(normalized)
            current = merged.get(dedupe)
            if current is None or normalized["confidence"] > current["confidence"]:
                merged[dedupe] = normalized

        persisted_entities: list[ExtractedEntity] = []
        for entity in merged.values():
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

        return {
            "ticket_id": ticket_id,
            "entities": persisted_entities,
            "rag_chunks": rag_chunks,
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


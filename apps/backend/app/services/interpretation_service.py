"""Service for multi-dimensional email interpretation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict

from app.llm.client import get_client
from app.llm.structured_output import validate_structured_output
from app.repositories.interpretation_repo import create_interpretation


class InterpretationInput(TypedDict):
    """Input contract for email interpretation."""

    ticket_id: str
    body: str


class InterpretationResult(TypedDict, total=False):
    """Normalized interpretation payload used across downstream layers."""

    interpretation_id: str
    ticket_id: str
    intent: str
    category: str
    sentiment: str
    urgency: float
    confidence: float
    reasoning: str
    raw_output: dict[str, Any]


INTERPRETATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["intent", "category", "sentiment", "urgency", "confidence", "reasoning"],
    "properties": {
        "intent": {"type": "string"},
        "category": {"type": "string"},
        "sentiment": {"type": "string"},
        "urgency": {"type": "number"},
        "confidence": {"type": "number"},
        "reasoning": {"type": "string"},
    },
}


CATEGORY_ALIASES: dict[str, str] = {
    "billing": "billing_issue",
    "billing_issue": "billing_issue",
    "billing_and_payments": "billing_issue",
    "billing_and_payment": "billing_issue",
    "payment_issue": "billing_issue",
    "payment_problem": "billing_issue",
    "payments": "billing_issue",
    "refund": "billing_issue",
    "shipping": "shipping_issue",
    "shipping_issue": "shipping_issue",
    "delivery_issue": "shipping_issue",
    "delivery_problem": "shipping_issue",
    "shipment_issue": "shipping_issue",
    "shipment_delay": "shipping_issue",
    "product": "product_issue",
    "product_issue": "product_issue",
    "product_defect": "product_issue",
    "defective_product": "product_issue",
    "damaged_product": "product_issue",
    "account": "account_issue",
    "account_issue": "account_issue",
    "account_access": "account_issue",
    "login_issue": "account_issue",
}

INTENT_ALIASES: dict[str, str] = {
    "refund": "request_refund",
    "refund_request": "request_refund",
    "request_refund": "request_refund",
    "complaint": "complaint",
    "clarification": "clarification_request",
    "clarification_request": "clarification_request",
    "general_question": "general_inquiry",
    "general_inquiry": "general_inquiry",
    "inquiry": "general_inquiry",
}

SENTIMENT_ALIASES: dict[str, str] = {
    "neutral": "neutral",
    "frustrated": "frustrated",
    "frustration": "frustrated",
    "upset": "frustrated",
    "angry": "frustrated",
    "urgent": "urgent",
    "anxious": "urgent",
}


def _normalize_label(value: str) -> str:
    cleaned = "_".join(value.strip().lower().replace("/", " ").replace("-", " ").split())
    return cleaned or "unknown"


def _normalize_category(value: str) -> str:
    normalized = _normalize_label(value)
    return CATEGORY_ALIASES.get(normalized, normalized)


def _normalize_intent(value: str) -> str:
    normalized = _normalize_label(value)
    return INTENT_ALIASES.get(normalized, normalized)


def _normalize_sentiment(value: str) -> str:
    normalized = _normalize_label(value)
    return SENTIMENT_ALIASES.get(normalized, normalized)


def _clamp_score(value: Any) -> float:
    numeric = float(value)
    if numeric < 0.0:
        return 0.0
    if numeric > 1.0:
        return 1.0
    return numeric


@dataclass
class InterpretationService:
    """Analyze an email and persist the result as the shared interpretation layer."""

    def _build_prompt(self, body: str) -> str:
        return f"""
You are analyzing a customer support email for a unified decision system.

Your output becomes the single source of truth for downstream actions, so it must
be consistent, cautious, and grounded only in the email content.

Interpret the email across the following dimensions:
- intent: what the customer is trying to achieve
- category: the issue domain
- sentiment: the emotional tone
- urgency: a score from 0.0 to 1.0
- confidence: a score from 0.0 to 1.0 representing interpretation certainty
- reasoning: one or two concise sentences explaining the interpretation

Guidelines:
- Prefer normalized snake_case labels for intent, category, and sentiment.
- Use only one of these category labels:
  billing_issue, shipping_issue, product_issue, account_issue, complaint, general_inquiry
- When the message is about refunds, double charges, invoices, payments, or transaction problems,
  use category billing_issue instead of alternate names like billing or billing_and_payments.
- Use only one of these intent labels when applicable:
  request_refund, complaint, clarification_request, general_inquiry
- Use only one of these sentiment labels when applicable:
  neutral, frustrated, urgent
- Do not invent facts not supported by the email.
- If the email is ambiguous, lower confidence rather than overcommitting.
- Urgency should reflect language, sentiment, and issue severity in the email.
- Return JSON only.

Email body:
\"\"\"
{body}
\"\"\"
""".strip()

    def interpret_email(self, payload: InterpretationInput) -> InterpretationResult:
        """Interpret an email body, store the result, and return the normalized output."""
        ticket_id = payload["ticket_id"].strip()
        body = payload["body"].strip()

        if not ticket_id:
            raise ValueError("ticket_id is required.")
        if not body:
            raise ValueError("body is required.")

        response = get_client().generate_text(
            self._build_prompt(body),
            temperature=0.1,
            expect_json=True,
        )
        validated = validate_structured_output(response["text"], INTERPRETATION_SCHEMA)[
            "validated_json"
        ]

        normalized_output = {
            "intent": _normalize_intent(validated["intent"]),
            "category": _normalize_category(validated["category"]),
            "sentiment": _normalize_sentiment(validated["sentiment"]),
            "urgency": _clamp_score(validated["urgency"]),
            "confidence": _clamp_score(validated["confidence"]),
            "reasoning": validated["reasoning"].strip(),
        }

        persisted = create_interpretation(
            {
                "ticket_id": ticket_id,
                "intent": normalized_output["intent"],
                "category": normalized_output["category"],
                "sentiment": normalized_output["sentiment"],
                "urgency": normalized_output["urgency"],
                "confidence": normalized_output["confidence"],
                "reasoning": normalized_output["reasoning"],
                "raw_output": validated,
            }
        )

        return {
            "interpretation_id": persisted["id"],
            "ticket_id": ticket_id,
            "intent": normalized_output["intent"],
            "category": normalized_output["category"],
            "sentiment": normalized_output["sentiment"],
            "urgency": normalized_output["urgency"],
            "confidence": normalized_output["confidence"],
            "reasoning": normalized_output["reasoning"],
            "raw_output": validated,
        }


_service: InterpretationService | None = None


def get_interpretation_service() -> InterpretationService:
    """Return a singleton interpretation service instance."""
    global _service
    if _service is None:
        _service = InterpretationService()
    return _service


def interpret_email(payload: InterpretationInput) -> InterpretationResult:
    """Compatibility helper matching the technical document wording."""
    return get_interpretation_service().interpret_email(payload)

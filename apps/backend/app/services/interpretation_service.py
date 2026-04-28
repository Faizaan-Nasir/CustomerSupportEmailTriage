"""Service for multi-dimensional email interpretation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict

from app.llm.client import get_client
from app.llm.structured_output import validate_structured_output
from app.repositories.interpretation_repo import create_interpretation
from app.repositories.ticket_repo import update_ticket
from app.repositories.supabase_client import get_client as get_supabase_client


class InterpretationInput(TypedDict, total=False):
    """Input contract for email interpretation."""

    ticket_id: str
    body: str
    context: list[dict[str, str]] | None


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
    """Analyze an interaction and persist the result as the shared interpretation layer."""

    def _build_prompt(self, body: str, context: list[dict[str, str]] | None = None) -> str:
        context_str = ""
        if context:
            context_str = "Conversation history (thread):\n"
            for msg in context:
                context_str += f"- {msg.get('sender', 'unknown')}: {msg.get('content', '')}\n"
            context_str += "\n"

        return f"""
Assume the role of a customer support analyst interpreting the customer's current message in the context of the entire email thread.

Your output becomes the single source of truth for downstream actions, so it must
be consistent, cautious, and grounded in the entire interaction history.

{context_str}Current message from customer:
\"\"\"
{body}
\"\"\"

Interpret the interaction across the following dimensions:
- intent: what the customer is trying to achieve now
- category: the issue domain
- sentiment: the current emotional tone
- urgency: a score from 0.0 to 1.0, reflecting the severity of the entire thread
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
- Do not invent facts not supported by the email or context.
- If the email is ambiguous, lower confidence rather than overcommitting.
- Urgency must be evaluated for the entire context of the thread. A second or third response
    about a critical issue might increase urgency if it is still unresolved.
- Return JSON only.

A sample email and ideal interpretation:
Email 1:
\"\"\"
Respected sir,
The baby milk I had bought from your online store happened to be expired. I only identified
this issue when my 2-month-old baby drank the milk, got sick and was hospitalized. This coming from
a reputed store that claims to provide best quality products is really disappointing.
I request you to process a refund and also urge you to look into your inventory to ensure such things don't repeat.
\"\"\"

Ideal interpretation:
{
    "intent": "request_refund",
    "category": "product_issue",
    "sentiment": "frustrated",
    "urgency": 0.9,
    "confidence": 0.95,
    "reasoning": "The customer is requesting a refund due to a defective product that caused harm to their baby, which is a highly urgent and frustrating situation."
}

Email 2: 
\"\"\"
Respected sir, 
I recently ordered a stroller from your online store, however I have received the order 5 days
after it was supposed to be delivered. This was only after a lot of back and forth with the delivery company.
I would request you to formally look into this matter and ensure that such delays don't happen in the future.
\"\"\"

Ideal interpretation:
{
    "intent": "complaint",
    "category": "shipping_issue",
    "sentiment": "frustrated",
    "urgency": 0.5,
    "confidence": 0.9,
    "reasoning": "The customer is expressing frustration about a delayed delivery and is requesting the company to address the issue to prevent future occurrences."
}
""".strip()

    def interpret_email(self, payload: InterpretationInput) -> InterpretationResult:
        """Interpret an interaction, store the result, and return the normalized output."""
        ticket_id = payload["ticket_id"].strip()
        body = payload["body"].strip()
        context = payload.get("context")

        if not ticket_id:
            raise ValueError("ticket_id is required.")
        if not body:
            raise ValueError("body is required.")

        response = get_client().generate_text(
            self._build_prompt(body, context),
            temperature=0.1,
            expect_json=True,
        )
        print(f"Raw interpretation response for ticket {ticket_id}:", response)
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
        print(f"Interpretation for ticket {ticket_id}: {normalized_output}")

        raw_output_blob = {
            "validated": validated,
            "thread_context": context
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
                "raw_output": raw_output_blob,
            }
        )

        update_ticket(ticket_id, {"urgency_score": normalized_output["urgency"]})

        return {
            "interpretation_id": persisted["id"],
            "ticket_id": ticket_id,
            "intent": normalized_output["intent"],
            "category": normalized_output["category"],
            "sentiment": normalized_output["sentiment"],
            "urgency": normalized_output["urgency"],
            "confidence": normalized_output["confidence"],
            "reasoning": normalized_output["reasoning"],
            "raw_output": raw_output_blob,
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

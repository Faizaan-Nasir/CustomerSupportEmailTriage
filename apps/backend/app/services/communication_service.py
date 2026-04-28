"""Service for customer-facing communication generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict


class CommunicationInput(TypedDict, total=False):
    """Input contract for customer-facing acknowledgment generation."""

    intent: str
    category: str
    sentiment: str
    confidence: float
    required_fields: list[str]
    ask_for_info: bool


class CommunicationResult(TypedDict):
    """Output contract for generated customer communication."""

    email_body: str


LABEL_TEXT: dict[str, str] = {
    "billing_issue": "a billing issue",
    "shipping_issue": "a shipping issue",
    "product_issue": "a product issue",
    "account_issue": "an account issue",
    "request_refund": "a refund request",
    "complaint": "a complaint",
    "neutral": "neutral",
    "frustrated": "frustrating",
    "urgent": "urgent",
}

FIELD_TEXT: dict[str, str] = {
    "order_id": "Order ID",
    "invoice_id": "Invoice ID",
    "payment_method": "Payment method",
    "transaction_reference": "Transaction reference",
    "tracking_number": "Tracking number",
    "delivery_address": "Delivery address",
    "product_name": "Product name",
    "order_date": "Order date",
    "account_email": "Account email",
}


def _normalize_label(value: str) -> str:
    cleaned = "_".join(value.strip().lower().replace("/", " ").replace("-", " ").split())
    return cleaned or "unknown"


def _label_text(value: str) -> str:
    normalized = _normalize_label(value)
    return LABEL_TEXT.get(normalized, normalized.replace("_", " "))


def _format_required_fields(fields: list[str]) -> str:
    lines = []
    for field in fields:
        normalized = _normalize_label(field)
        lines.append(f"- {FIELD_TEXT.get(normalized, normalized.replace('_', ' ').title())}")
    return "\n".join(lines)


@dataclass
class CommunicationService:
    """Generate minimal, context-aware customer acknowledgments."""

    def generate_email(self, payload: CommunicationInput) -> CommunicationResult:
        """Return a short customer-facing acknowledgment email body."""
        category = _normalize_label(str(payload.get("category") or ""))
        sentiment = _normalize_label(str(payload.get("sentiment") or "neutral"))
        confidence = float(payload.get("confidence") or 0.0)
        required_fields = [_normalize_label(field) for field in (payload.get("required_fields") or [])]
        ask_for_info = bool(payload.get("ask_for_info"))

        if confidence >= 0.75:
            opening = (
                f"It looks like you're facing {_label_text(category)}. "
                "We’re reviewing it and will help you through the next steps."
            )
        else:
            opening = (
                "Thanks for reaching out. We’re reviewing the details of your request "
                "and will help you with the next steps."
            )

        if sentiment == "frustrated":
            opening = "I’m sorry this has been frustrating. " + opening
        elif sentiment == "urgent":
            opening = "We understand this feels urgent. " + opening

        if ask_for_info and required_fields:
            email_body = (
                f"{opening}\n\n"
                "To move this forward without unnecessary back-and-forth, please share:\n"
                f"{_format_required_fields(required_fields)}"
            )
        else:
            email_body = opening

        return {"email_body": email_body.strip()}


_service: CommunicationService | None = None


def get_communication_service() -> CommunicationService:
    """Return a singleton communication service instance."""
    global _service
    if _service is None:
        _service = CommunicationService()
    return _service


def generate_email(payload: CommunicationInput) -> CommunicationResult:
    """Compatibility helper matching the technical document wording."""
    return get_communication_service().generate_email(payload)


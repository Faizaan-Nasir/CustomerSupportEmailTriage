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
    context: list[dict[str, str]] | None


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
    "unrelated": "unrelated matter",
    "uncertain": "review",
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
        context = payload.get("context")

        if context and len(context) > 0:
            # Use LLM for context-aware response when history exists
            return self._generate_context_aware_email(payload)

        # Handle Uncertainty or Low Confidence
        if category == "uncertain" or confidence < 0.5:
            opening = (
                "Thanks for reaching out. We've received your message and our customer service team "
                "will review your request and get back to you with a personalized response shortly."
            )
            email_body = f"{opening}\n\n---\nThis response is AI generated"
            return {"email_body": email_body}

        if category == "unrelated":
            opening = (
                "Thanks for reaching out. It appears this message may have been sent to us by mistake, "
                "as it is unrelated to our support services. Please check the email address carefully "
                "before sending your mail again."
            )
            email_body = f"{opening}\n\n---\nThis response is AI generated"
            return {"email_body": email_body}

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
            if len(required_fields) >= 3:
                missing_info_text = (
                    "To move this forward quickly, please share a copy of your bill or invoice "
                    "containing your order details, or provide the following information:\n"
                    f"{_format_required_fields(required_fields)}"
                )
            else:
                missing_info_text = (
                    "To move this forward without unnecessary back-and-forth, please share:\n"
                    f"{_format_required_fields(required_fields)}"
                )
            email_body = f"{opening}\n\n{missing_info_text}"
        else:
            email_body = opening

        email_body = f"{email_body.strip()}\n\n---\nThis response is AI generated"

        return {"email_body": email_body.strip()}

    def _generate_context_aware_email(self, payload: CommunicationInput) -> CommunicationResult:
        """Use Gemini to generate a response that respects the conversation history."""
        context = payload.get("context") or []
        context_str = "Conversation history:\n"
        for msg in context:
            context_str += f"- {msg.get('sender', 'unknown')}: {msg.get('content', '')}\n"

        category = _normalize_label(str(payload.get("category") or ""))
        confidence = float(payload.get("confidence") or 0.0)
        required_fields = payload.get('required_fields', [])

        prompt = f"""
You are a helpful customer support agent. Generate a concise, context-aware response to the customer.

{context_str}
Current Situation:
- Intent: {payload.get('intent')}
- Category: {payload.get('category')}
- Sentiment: {payload.get('sentiment')}
- Confidence: {payload.get('confidence')}
- Missing Info: {', '.join(required_fields) if payload.get('ask_for_info') else 'None'}

Guidelines:
- IMPORTANT: If the conversation history is primarily in Arabic or the customer just wrote in Arabic, you MUST respond in Arabic.
- If the 'Category' is 'uncertain' or 'Confidence' is low (below 0.5), politely explain that a customer service representative will review their specific case and respond soon.
- Acknowledge previous points if the customer just provided them.
- Be empathetic if the sentiment is frustrated.
- If 'Category' is 'unrelated', politely explain that this seems to be a mistake and suggest they check the email address.
- If 'Missing Info' is not 'None' AND confidence is high, politely ask for the missing details.
- SPECIAL RULE: If there are 3 or more items listed in 'Missing Info', suggest that providing a bill or invoice would be the easiest way to share all the required details.
- Keep it under 3-4 sentences.
- Do not use placeholders like [Name].
- End with a professional closing.
- Do not include the "AI generated" warning here; it will be added by the service.

Example (English - Clear - Many missing fields): 
\"\"\"
Sample Input:
Current Situation:
- Intent: request_refund
- Category: billing_issue
- Sentiment: frustrated
- Missing Info: Order ID, Invoice ID, Payment method

Sample Output:
Dear Customer,
We're sorry to hear about the billing issue you're experiencing. 
To help us resolve this quickly, please provide a copy of your invoice or bill containing your order details. 
Alternatively, you can share your Order ID, Invoice ID, and Payment method used.
Thank you for your cooperation.
Sincerely,
Customer Support Team
\"\"\"

Example (Arabic - Clear):
\"\"\"
Sample Input:
Current Situation:
- Intent: complaint
- Category: product_issue
- Sentiment: frustrated
- Missing Info: رقم الطلب (Order ID)

Sample Output:
عزيزي العميل،
نحن نأسف حقاً لسماع تجربتك السلبية مع المنتج. لقد قمنا بتوجيه شكواك إلى الفريق المختص لمراجعتها فوراً.
لمساعدتنا في تسريع عملية الحل، يرجى تزويدنا برقم الطلب الخاص بك.
شكراً لصبرك وتعاونك معنا.
مع خالص التحية،
فريق دعم العملاء
\"\"\"

Response:
""".strip()

        from app.llm.client import get_client
        response = get_client().generate_text(prompt, temperature=0.7)
        email_body = response["text"].strip()
        email_body = f"{email_body}\n\n---\nThis response is AI generated"

        return {"email_body": email_body}


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



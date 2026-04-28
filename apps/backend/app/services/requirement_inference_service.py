"""Service for inferring required information dynamically."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict


class RequirementInferenceInput(TypedDict, total=False):
    """Input contract for determining what information is still missing."""

    intent: str
    category: str
    entities: dict[str, str] | list[dict[str, str]]


class RequirementInferenceResult(TypedDict):
    """Result contract for required field inference."""

    required_fields: list[str]


REQUIREMENT_RULES: dict[str, list[str]] = {
    "billing_issue": ["invoice_id", "payment_method", "transaction_reference"],
    "shipping_issue": ["order_id", "tracking_number", "delivery_address"],
    "product_issue": ["product_name", "order_date"],
    "account_issue": ["account_email"],
    "refund_request": ["order_id", "invoice_id", "transaction_reference"],
    "complaint": ["order_id"],
}


def _normalize_label(value: str) -> str:
    cleaned = "_".join(value.strip().lower().replace("/", " ").replace("-", " ").split())
    return cleaned or "unknown"


def _normalize_entities(entities: dict[str, str] | list[dict[str, str]]) -> set[str]:
    if isinstance(entities, dict):
        return {_normalize_label(key) for key, value in entities.items() if str(value).strip()}

    normalized: set[str] = set()
    for entity in entities:
        key = entity.get("key", "")
        value = entity.get("value", "")
        if str(key).strip() and str(value).strip():
            normalized.add(_normalize_label(str(key)))
    return normalized


@dataclass
class RequirementInferenceService:
    """Infer the minimum missing information required to continue a ticket flow."""

    def infer_requirements(self, payload: RequirementInferenceInput) -> RequirementInferenceResult:
        """Return only the fields still missing for the given interpretation context."""
        intent = _normalize_label(str(payload.get("intent") or ""))
        category = _normalize_label(str(payload.get("category") or ""))
        present_entities = _normalize_entities(payload.get("entities") or {})

        required_candidates: list[str] = []
        for label in (category, intent):
            required_candidates.extend(REQUIREMENT_RULES.get(label, []))

        seen: set[str] = set()
        ordered_required: list[str] = []
        for field in required_candidates:
            normalized_field = _normalize_label(field)
            if normalized_field in seen:
                continue
            seen.add(normalized_field)
            if normalized_field not in present_entities:
                ordered_required.append(normalized_field)

        return {"required_fields": ordered_required}


_service: RequirementInferenceService | None = None


def get_requirement_inference_service() -> RequirementInferenceService:
    """Return a singleton requirement inference service instance."""
    global _service
    if _service is None:
        _service = RequirementInferenceService()
    return _service


def infer_requirements(payload: RequirementInferenceInput) -> RequirementInferenceResult:
    """Compatibility helper matching the technical document wording."""
    return get_requirement_inference_service().infer_requirements(payload)


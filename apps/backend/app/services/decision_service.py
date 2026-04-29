"""Service for ticket decision-making logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict

from app.config import settings


class DecisionInput(TypedDict, total=False):
    """Input contract for deciding the next step in the ticket flow."""

    intent: str
    category: str
    confidence: float
    urgency: float
    required_fields: list[str]
    interaction_count: int


class DecisionResult(TypedDict, total=False):
    """Decision outcome shared with downstream communication and agent-assist layers."""

    ask_for_info: bool
    escalate: bool
    continue_automation: bool
    escalation_target: str | None
    reason: str


ESCALATION_TARGETS: dict[str, str] = {
    "billing_issue": "finance",
    "shipping_issue": "logistics",
    "product_issue": "product_support",
    "account_issue": "account_support",
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


@dataclass
class DecisionService:
    """Decide whether the system should request more info, continue, or escalate."""

    interaction_limit: int = settings.interaction_limit
    confidence_threshold: float = settings.confidence_threshold

    def decide(self, payload: DecisionInput) -> DecisionResult:
        """Return the next-step decision for the current ticket state."""
        category = _normalize_label(str(payload.get("category") or ""))
        intent = _normalize_label(str(payload.get("intent") or ""))
        confidence = _clamp_score(payload.get("confidence") or 0.0)
        urgency = _clamp_score(payload.get("urgency") or 0.0)
        required_fields = [_normalize_label(field) for field in (payload.get("required_fields") or [])]
        interaction_count = int(payload.get("interaction_count") or 0)

        has_missing_info = bool(required_fields)
        within_interaction_limit = interaction_count < self.interaction_limit
        
        # Priority Escalation: If urgency is very high, escalate immediately regardless of missing info
        if urgency >= 0.8 and category in ESCALATION_TARGETS:
            return {
                "ask_for_info": False,
                "escalate": True,
                "continue_automation": False,
                "escalation_target": ESCALATION_TARGETS[category],
                "reason": f"Urgency score ({urgency}) exceeds critical threshold. Escalating immediately to {ESCALATION_TARGETS[category]}.",
            }

        ask_for_info = has_missing_info and within_interaction_limit

        if ask_for_info:
            return {
                "ask_for_info": True,
                "escalate": False,
                "continue_automation": True,
                "escalation_target": None,
                "reason": "Critical information is still missing and the interaction limit has not been reached.",
            }

        if has_missing_info and not within_interaction_limit:
            return {
                "ask_for_info": False,
                "escalate": False,
                "continue_automation": False,
                "escalation_target": None,
                "reason": "Missing information remains, but the interaction limit has been reached so control should move to a human agent.",
            }

        escalation_target = ESCALATION_TARGETS.get(category)
        should_escalate = (
            escalation_target is not None
            and confidence >= self.confidence_threshold
            and urgency >= 0.4
            and intent not in {"clarification_request", "general_inquiry"}
        )

        return {
            "ask_for_info": False,
            "escalate": should_escalate,
            "continue_automation": not should_escalate,
            "escalation_target": escalation_target if should_escalate else None,
            "reason": (
                "Sufficient information is available and the issue meets the threshold for targeted internal escalation."
                if should_escalate
                else "Sufficient information is available, but the ticket can remain with the current support flow without escalation."
            ),
        }


_service: DecisionService | None = None


def get_decision_service() -> DecisionService:
    """Return a singleton decision service instance."""
    global _service
    if _service is None:
        _service = DecisionService()
    return _service


def decide_next_action(payload: DecisionInput) -> DecisionResult:
    """Compatibility helper matching the technical document wording."""
    return get_decision_service().decide(payload)


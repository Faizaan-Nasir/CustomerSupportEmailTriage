"""Service for internal agent guidance generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict

from app.repositories.supabase_client import get_client


class AgentAssistInput(TypedDict, total=False):
    """Input contract for internal agent guidance generation."""

    ticket_id: str
    intent: str
    category: str
    sentiment: str
    entities: list[dict[str, Any]]
    required_fields: list[str]
    escalate: bool
    escalation_target: str | None


class AgentAssistResult(TypedDict, total=False):
    """Output contract for the generated agent action plan."""

    action_plan_id: str
    summary: str
    steps: list[str]
    escalation_target: str | None


CATEGORY_STEPS: dict[str, list[str]] = {
    "billing_issue": [
        "Verify the order and invoice references against the billing system.",
        "Check whether the charge pattern supports a refund or billing correction.",
        "Prepare the customer update once the financial review is complete.",
    ],
    "shipping_issue": [
        "Confirm the order and tracking details in the logistics system.",
        "Check the latest shipment status and expected delivery timeline.",
        "Prepare the customer update with the most accurate ETA available.",
    ],
    "product_issue": [
        "Review the product details, order date, and issue description.",
        "Check return, replacement, or warranty eligibility.",
        "Prepare the next customer step based on policy and available evidence.",
    ],
    "account_issue": [
        "Verify the affected account details and recent account history.",
        "Check whether the issue can be resolved without escalation.",
        "Prepare the customer update with the safest next step.",
    ],
}


def _normalize_label(value: str) -> str:
    cleaned = "_".join(value.strip().lower().replace("/", " ").replace("-", " ").split())
    return cleaned or "unknown"


def _humanize_label(value: str) -> str:
    return _normalize_label(value).replace("_", " ")


@dataclass
class AgentAssistService:
    """Generate a concise internal action plan and persist it for later review."""

    table_name: str = "agent_actions"

    def __post_init__(self) -> None:
        self._client = get_client()

    @staticmethod
    def _first_row(response: Any) -> dict[str, Any]:
        rows = getattr(response, "data", None) or []
        if not rows:
            raise LookupError("Supabase returned no rows.")
        return dict(rows[0])

    def _build_summary(self, payload: AgentAssistInput) -> str:
        category = _humanize_label(str(payload.get("category") or "issue"))
        intent = _humanize_label(str(payload.get("intent") or "request"))
        sentiment = _humanize_label(str(payload.get("sentiment") or "neutral"))
        return (
            f"Customer raised a {category} related to {intent}. "
            f"Current tone appears {sentiment}."
        )

    def _build_steps(self, payload: AgentAssistInput) -> list[str]:
        category = _normalize_label(str(payload.get("category") or ""))
        entities = payload.get("entities") or []
        required_fields = [_humanize_label(field) for field in (payload.get("required_fields") or [])]
        base_steps = list(CATEGORY_STEPS.get(category, [
            "Review the ticket details and confirm the core issue.",
            "Verify the available evidence and policy constraints.",
            "Prepare the next customer-facing action.",
        ]))

        if entities:
            key_details = ", ".join(
                f"{_humanize_label(str(entity.get('key', 'detail')))}: {entity.get('value', '')}"
                for entity in entities[:4]
                if str(entity.get("value", "")).strip()
            )
            if key_details:
                base_steps.insert(0, f"Use the extracted details for validation: {key_details}.")

        if required_fields:
            base_steps.append(
                "Missing information still needed from the customer: "
                + ", ".join(required_fields)
                + "."
            )

        if payload.get("escalate") and payload.get("escalation_target"):
            base_steps.append(
                f"Escalate to {_humanize_label(str(payload['escalation_target']))} once the ticket notes are complete."
            )

        return base_steps

    def _store_action_plan(
        self,
        ticket_id: str,
        summary: str,
        steps: list[str],
        escalation_target: str | None,
    ) -> dict[str, Any]:
        response = (
            self._client.table(self.table_name)
            .insert(
                {
                    "ticket_id": ticket_id,
                    "summary": summary,
                    "action_plan": "\n".join(f"- {step}" for step in steps),
                    "escalation_target": escalation_target,
                }
            )
            .execute()
        )
        return self._first_row(response)

    def generate_agent_plan(self, payload: AgentAssistInput) -> AgentAssistResult:
        """Generate and persist an internal action plan for the support agent."""
        ticket_id = str(payload.get("ticket_id") or "").strip()
        if not ticket_id:
            raise ValueError("ticket_id is required.")

        summary = self._build_summary(payload)
        steps = self._build_steps(payload)
        escalation_target = (
            _normalize_label(str(payload.get("escalation_target")))
            if payload.get("escalation_target")
            else None
        )
        created = self._store_action_plan(ticket_id, summary, steps, escalation_target)

        return {
            "action_plan_id": created["id"],
            "summary": summary,
            "steps": steps,
            "escalation_target": escalation_target,
        }


_service: AgentAssistService | None = None


def get_agent_assist_service() -> AgentAssistService:
    """Return a singleton agent assist service instance."""
    global _service
    if _service is None:
        _service = AgentAssistService()
    return _service


def generate_agent_plan(payload: AgentAssistInput) -> AgentAssistResult:
    """Compatibility helper matching the technical document wording."""
    return get_agent_assist_service().generate_agent_plan(payload)


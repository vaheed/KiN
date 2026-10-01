from __future__

from ..config import Settings
from ..schemas import ActionRisk, ActionType, Decision, PolicyResult


class AutonomyPolicy:
    """Deterministic safety floor applied after the LLM proposes a decision."""

    DESTRUCTIVE = {
        ActionType.delete,
        ActionType.modify_security,
    }
    EXTERNAL_IMPACT = {
        ActionType.deploy,
        ActionType.restart,
        ActionType.change,
        ActionType.external_request,
    }

    def __init__(self, settings: Settings):
        self.mode = settings.autonomy_mode

    def evaluate(self, decision: Decision) -> PolicyResult:
        if self.mode == "strict":
            return PolicyResult(
                mode=self.mode,
                decision_allowed=True,
                execution_class="approval",
                requires_user_approval=True,
                reason="Strict mode requires explicit approval before action execution.",
            )

        if decision.action_risk in {ActionRisk.high, ActionRisk.critical}:
            return PolicyResult(
                mode=self.mode,
                decision_allowed=True,
                execution_class="approval",
                requires_user_approval=True,
                reason="High or critical risk requires user approval.",
            )

        if decision.action_type in self.DESTRUCTIVE:
            return PolicyResult(
                mode=self.mode,
                decision_allowed=True,
                execution_class="approval",
                requires_user_approval=True,
                reason="Destructive or security-sensitive actions require user approval.",
            )

        if decision.impact == "high" or not decision.reversible or decision.confidence < 0.65:
            return PolicyResult(
                mode=self.mode,
                decision_allowed=True,
                execution_class="approval",
                requires_user_approval=True,
                reason="High impact, irreversible, or low-confidence actions require approval.",
            )

        if self.mode == "permissive" and decision.action_risk == ActionRisk.low and decision.confidence >= 0.85:
            return PolicyResult(
                mode=self.mode,
                decision_allowed=True,
                execution_class="automatic",
                requires_user_approval=False,
                reason="Low risk and high confidence in permissive mode.",
            )

        if decision.action_type in self.EXTERNAL_IMPACT or decision.action_risk == ActionRisk.medium:
            return PolicyResult(
                mode=self.mode,
                decision_allowed=True,
                execution_class="conditional",
                requires_user_approval=False,
                reason="Medium-risk or externally visible work is conditional on execution-time checks.",
            )

        return PolicyResult(
            mode=self.mode,
            decision_allowed=True,
            execution_class="automatic",
            requires_user_approval=False,
            reason="Low-impact, reversible, sufficiently confident action.",
        )

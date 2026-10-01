from __future__ import annotations

from ..config import Settings
from ..schemas import ActionRisk, ActionType, Decision, DecisionMode, Environment, PolicyResult, Scope


class AutonomyPolicy:
    """Derive execution mode from the decision, then apply a policy profile."""

    DESTRUCTIVE = {ActionType.delete, ActionType.modify_security}
    ACTIVE = {ActionType.change, ActionType.restart, ActionType.deploy}
    INVESTIGATIVE = {ActionType.observe, ActionType.investigate, ActionType.research}

    def __init__(self, settings: Settings):
        self.profile = settings.autonomy_profile

    @staticmethod
    def mode_for(decision: Decision) -> DecisionMode:
        if decision.action_type == ActionType.no_action:
            return DecisionMode.idle
        if decision.action_type in AutonomyPolicy.DESTRUCTIVE:
            return DecisionMode.destructive
        if decision.action_type == ActionType.delegate:
            return DecisionMode.delegate
        if decision.action_type in AutonomyPolicy.INVESTIGATIVE:
            return DecisionMode.observe if decision.action_type == ActionType.observe else DecisionMode.investigate
        if decision.action_type in {ActionType.communicate, ActionType.external_request}:
            return DecisionMode.communicate
        if decision.action_type in AutonomyPolicy.ACTIVE:
            return DecisionMode.execute
        return DecisionMode.observe

    def evaluate(self, decision: Decision) -> PolicyResult:
        mode = self.mode_for(decision)
        auto_threshold = {"cautious": 0.90, "balanced": 0.75, "autonomous": 0.65}[self.profile]
        conditional_threshold = {"cautious": 0.80, "balanced": 0.65, "autonomous": 0.55}[self.profile]

        if mode == DecisionMode.idle:
            return PolicyResult(mode=mode, profile=self.profile, decision_allowed=True, execution_class="automatic", requires_user_approval=False, reason="No action was requested.")
        if mode == DecisionMode.destructive:
            return PolicyResult(mode=mode, profile=self.profile, decision_allowed=True, execution_class="approval", requires_user_approval=True, reason="Destructive or security-sensitive work always requires approval.")
        if decision.action_risk in {ActionRisk.high, ActionRisk.critical}:
            return PolicyResult(mode=mode, profile=self.profile, decision_allowed=True, execution_class="approval", requires_user_approval=True, reason="High or critical risk requires approval.")
        if decision.environment == Environment.production and mode == DecisionMode.execute:
            return PolicyResult(mode=mode, profile=self.profile, decision_allowed=True, execution_class="approval", requires_user_approval=True, reason="Production-changing work requires approval by default.")
        if decision.impact == "high" or not decision.reversible:
            return PolicyResult(mode=mode, profile=self.profile, decision_allowed=True, execution_class="approval", requires_user_approval=True, reason="High-impact or irreversible work requires approval.")
        if decision.confidence < conditional_threshold:
            return PolicyResult(mode=mode, profile=self.profile, decision_allowed=True, execution_class="approval", requires_user_approval=True, reason="Confidence is too low for autonomous execution.")
        if mode in {DecisionMode.observe, DecisionMode.investigate} and decision.scope != Scope.external:
            return PolicyResult(mode=mode, profile=self.profile, decision_allowed=True, execution_class="automatic", requires_user_approval=False, reason="Observation and investigation are read-only by policy.")
        if mode == DecisionMode.communicate:
            if decision.scope == Scope.external and decision.environment == Environment.production:
                return PolicyResult(mode=mode, profile=self.profile, decision_allowed=True, execution_class="approval", requires_user_approval=True, reason="External production communication requires approval.")
            return PolicyResult(mode=mode, profile=self.profile, decision_allowed=True, execution_class="conditional", requires_user_approval=False, reason="Communication is externally visible and receives an execution-time check.")
        if decision.action_risk == ActionRisk.medium or decision.confidence < auto_threshold:
            return PolicyResult(mode=mode, profile=self.profile, decision_allowed=True, execution_class="conditional", requires_user_approval=False, reason="Moderate risk or confidence requires execution-time checks.")
        if mode == DecisionMode.delegate:
            return PolicyResult(mode=mode, profile=self.profile, decision_allowed=True, execution_class="conditional", requires_user_approval=False, reason="Delegated work remains constrained by the worker's tool and approval policy.")
        return PolicyResult(mode=mode, profile=self.profile, decision_allowed=True, execution_class="automatic", requires_user_approval=False, reason="Low-risk, reversible, sufficiently confident work is eligible for automatic execution.")

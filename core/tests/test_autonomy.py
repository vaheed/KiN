from app.config import Settings
from app.schemas import ActionRisk, ActionType, Decision, Environment, Scope
from app.services.autonomy import AutonomyPolicy


def decision(**overrides):
    payload = dict(
        goal="test",
        intent="test",
        action_type=ActionType.investigate,
        action_risk=ActionRisk.low,
        impact="low",
        environment=Environment.development,
        scope=Scope.internal,
        reversible=True,
        confidence=0.95,
        proposed_action="read-only check",
        plan=["check"],
        next_step="check",
    )
    payload.update(overrides)
    return Decision(**payload)


def test_low_risk_investigation_is_automatic_and_has_mode():
    result = AutonomyPolicy(Settings(env="test", KiN_AUTONOMY_PROFILE="balanced")).evaluate(decision())
    assert result.mode.value == "investigate"
    assert result.execution_class == "automatic"
    assert result.requires_user_approval is False


def test_destructive_requires_approval():
    result = AutonomyPolicy(Settings(env="test", KiN_AUTONOMY_PROFILE="balanced")).evaluate(
        decision(action_type=ActionType.delete, action_risk=ActionRisk.low)
    )
    assert result.mode.value == "destructive"
    assert result.execution_class == "approval"
    assert result.requires_user_approval is True


def test_high_risk_requires_approval():
    result = AutonomyPolicy(Settings(env="test", KiN_AUTONOMY_PROFILE="autonomous")).evaluate(
        decision(action_risk=ActionRisk.high)
    )
    assert result.requires_user_approval is True


def test_cautious_profile_requires_approval_for_low_confidence():
    result = AutonomyPolicy(Settings(env="test", KiN_AUTONOMY_PROFILE="cautious")).evaluate(
        decision(action_type=ActionType.restart, action_risk=ActionRisk.low, confidence=0.72)
    )
    assert result.execution_class == "approval"


def test_production_execute_requires_approval():
    result = AutonomyPolicy(Settings(env="test", KiN_AUTONOMY_PROFILE="autonomous")).evaluate(
        decision(action_type=ActionType.restart, action_risk=ActionRisk.medium, environment=Environment.production, confidence=0.99)
    )
    assert result.mode.value == "execute"
    assert result.execution_class == "approval"


def test_external_communication_is_conditional():
    result = AutonomyPolicy(Settings(env="test", KiN_AUTONOMY_PROFILE="balanced")).evaluate(
        decision(action_type=ActionType.communicate, action_risk=ActionRisk.medium, scope=Scope.external)
    )
    assert result.mode.value == "communicate"
    assert result.execution_class == "conditional"

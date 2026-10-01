from app.config import Settings
from app.schemas import ActionRisk, ActionType, Decision
from app.services.autonomy import AutonomyPolicy


def decision(**overrides):
    payload = dict(
        goal="test",
        intent="test",
        action_type=ActionType.investigate,
        action_risk=ActionRisk.low,
        impact="low",
        reversible=True,
        confidence=0.95,
        proposed_action="read-only check",
        plan=["check"],
        next_step="check",
    )
    payload.update(overrides)
    return Decision(**payload)


def test_low_risk_reversible_is_automatic():
    result = AutonomyPolicy(Settings(env="test", KIN_AUTONOMY_MODE="balanced")).evaluate(decision())
    assert result.execution_class == "automatic"
    assert result.requires_user_approval is False


def test_destructive_requires_approval():
    result = AutonomyPolicy(Settings(env="test", KIN_AUTONOMY_MODE="balanced")).evaluate(
        decision(action_type=ActionType.delete, action_risk=ActionRisk.low)
    )
    assert result.execution_class == "approval"
    assert result.requires_user_approval is True


def test_high_risk_requires_approval():
    result = AutonomyPolicy(Settings(env="test", KIN_AUTONOMY_MODE="permissive")).evaluate(
        decision(action_risk=ActionRisk.high)
    )
    assert result.requires_user_approval is True


def test_strict_mode_requires_approval():
    result = AutonomyPolicy(Settings(env="test", KIN_AUTONOMY_MODE="strict")).evaluate(decision())
    assert result.execution_class == "approval"


def test_medium_risk_external_work_is_conditional():
    result = AutonomyPolicy(Settings(env="test", KIN_AUTONOMY_MODE="balanced")).evaluate(
        decision(action_type=ActionType.restart, action_risk=ActionRisk.medium)
    )
    assert result.execution_class == "conditional"
    assert result.requires_user_approval is False

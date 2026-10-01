from app.schemas import ActionRisk, ActionType, Decision


def test_decision_schema_accepts_valid_payload() -> None:
    decision = Decision(
        goal="diagnose service outage",
        intent="observe before changing anything",
        action_type=ActionType.investigate,
        action_risk=ActionRisk.low,
        impact="low",
        reversible=True,
        confidence=0.9,
        should_investigate=True,
        proposed_action="Collect service status and recent logs.",
        plan=["Check status", "Inspect recent logs"],
        next_step="Run read-only diagnostics.",
    )
    assert decision.confidence == 0.9


def test_decision_schema_rejects_empty_plan() -> None:
    try:
        Decision(
            goal="x",
            intent="x",
            action_type="observe",
            action_risk="low",
            impact="low",
            reversible=True,
            confidence=0.9,
            proposed_action="x",
            plan=["", "  "],
            next_step="x",
        )
    except ValueError:
        return
    raise AssertionError("empty plans must be rejected")

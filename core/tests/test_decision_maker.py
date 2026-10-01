from __future__ import annotations

from app.services.decision import DecisionMaker


VALID_DECISION = """```json
{"goal":"diagnose","intent":"observe","action_type":"investigate","action_risk":"low","impact":"low","environment":"development","scope":"internal","reversible":true,"confidence":0.92,"should_investigate":true,"proposed_action":"collect facts","plan":["inspect"],"next_step":"inspect"}
```"""


class FakeBifrost:
    def __init__(self):
        self.models = []

    def chat_json(self, _system_prompt: str, _user_prompt: str, model: str | None = None) -> str:
        self.models.append(model)
        return VALID_DECISION


def test_standard_decision_uses_default_model(settings):
    bifrost = FakeBifrost()
    result = DecisionMaker(settings, bifrost).decide(user_input="why is this service slow?", memory=[], working={}, context={})
    assert result.goal == "diagnose"
    assert bifrost.models == [settings.decision_model]


def test_fast_context_selects_fast_model(settings):
    bifrost = FakeBifrost()
    DecisionMaker(settings, bifrost).decide(user_input="check status", memory=[], working={}, context={"complexity": "fast"})
    assert bifrost.models == [settings.decision_model_fast]


def test_deep_context_selects_deep_model(settings):
    bifrost = FakeBifrost()
    DecisionMaker(settings, bifrost).decide(user_input="analyze a complex multi-system failure", memory=[], working={}, context={"complexity": "deep"})
    assert bifrost.models == [settings.decision_model_deep]

from __future__ import annotations

from app.services.decision import DecisionMaker


class FakeBifrost:
    def chat_json(self, _system_prompt: str, _user_prompt: str) -> str:
        return '''```json
{"goal":"diagnose","intent":"observe","action_type":"investigate","action_risk":"low","impact":"low","reversible":true,"confidence":0.92,"should_investigate":true,"proposed_action":"collect facts","plan":["inspect"],"next_step":"inspect"}
```'''


def test_decision_maker_parses_fenced_json(settings) -> None:
    result = DecisionMaker(settings, FakeBifrost()).decide(
        user_input="why is this service slow?",
        memory=[],
        working={},
        context={},
    )
    assert result.goal == "diagnose"
    assert result.action_type.value == "investigate"
    assert result.confidence == 0.92

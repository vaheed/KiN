from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app, container
from app.schemas import ActionRisk, ActionType, Decision


class FakeMemories:
    def __init__(self) -> None:
        self.updated: list[tuple[str, dict]] = []

    def get_working(self, session_id: str) -> dict:
        return {"session_id": session_id, "state": {}}

    def search(self, _request):
        return []

    def update_working(self, session_id: str, state: dict) -> None:
        self.updated.append((session_id, state))


class FakeEvents:
    def create(self, _item) -> dict:
        return {"id": uuid4()}


class FakeDecisionMaker:
    def decide(self, **_kwargs) -> Decision:
        return Decision(
            goal="test goal",
            intent="observe",
            action_type=ActionType.investigate,
            action_risk=ActionRisk.low,
            impact="low",
            reversible=True,
            confidence=0.95,
            proposed_action="collect read-only facts",
            plan=["inspect"],
            next_step="inspect",
        )


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "KiN"


def test_decide_api_applies_policy_and_records_event(monkeypatch) -> None:
    memories = FakeMemories()
    monkeypatch.setattr(container, "memories", memories)
    monkeypatch.setattr(container, "events", FakeEvents())
    monkeypatch.setattr(container, "decision_maker", FakeDecisionMaker())

    with TestClient(app) as client:
        response = client.post("/v1/decide", json={"input": "investigate this issue", "session_id": "api-test"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"]["action_risk"] == "low"
    assert payload["policy"]["execution_class"] == "automatic"
    assert payload["policy"]["requires_user_approval"] is False
    assert memories.updated[0][0] == "api-test"

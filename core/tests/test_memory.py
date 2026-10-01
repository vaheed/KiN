from __future__ import annotations

import sys
from datetime import datetime, timezone
from types import SimpleNamespace

from app.config import Settings
from app.schemas import MemoryCreate, MemorySearchRequest
from app.services.memory import MemoryService


class FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def setex(self, key, ttl, value):
        self.data[key] = value


class FakeMem0:
    instances = []

    def __init__(self, config):
        self.config = config
        self.calls = []
        self.search_calls = []
        self.memories = {}
        self.__class__.instances.append(self)

    @classmethod
    def from_config(cls, config):
        return cls(config)

    def add(self, content, **kwargs):
        self.calls.append(("add", content, kwargs))
        memory_id = "00000000-0000-0000-0000-000000000001"
        self.memories[memory_id] = {
            "id": memory_id,
            "memory": content,
            "metadata": kwargs.get("metadata") or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        return {"results": [{"id": memory_id, "memory": content, "event": "ADD"}]}

    def get(self, memory_id):
        return self.memories.get(memory_id)

    def search(self, query, **kwargs):
        self.search_calls.append((query, kwargs))
        return {
            "results": [
                {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "memory": "I prefer concise technical answers.",
                    "score": 0.91,
                    "metadata": {
                        "kin_memory_type": "semantic",
                        "kin_importance": 0.8,
                        "kin_tags": ["preference"],
                    },
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }

    def close(self):
        pass


def test_mem0_uses_bifrost_for_llm_and_embeddings(monkeypatch, settings):
    FakeMem0.instances.clear()
    monkeypatch.setitem(sys.modules, "mem0", SimpleNamespace(Memory=FakeMem0))

    service = MemoryService(settings, FakeRedis())
    memory = service._mem0()
    config = memory.config

    assert config["llm"]["provider"] == "openai"
    assert config["llm"]["config"]["openai_base_url"] == "http://bifrost:8080/v1"
    assert config["llm"]["config"]["model"] == settings.memory_llm_model
    assert config["embedder"]["config"]["openai_base_url"] == "http://bifrost:8080/v1"
    assert config["vector_store"]["provider"] == "pgvector"
    assert config["vector_store"]["config"]["collection_name"] == settings.memory_collection


def test_create_explicit_memory_uses_mem0_without_second_inference(settings):
    fake = FakeMem0({"test": True})
    service = MemoryService(settings, FakeRedis())
    service._memory = fake

    record = service.create(
        MemoryCreate(
            content="I prefer concise technical answers.",
            importance=0.8,
            tags=["preference"],
        )
    )

    assert record.content == "I prefer concise technical answers."
    assert record.importance == 0.8
    add_call = fake.calls[-1]
    assert add_call[2]["infer"] is False
    assert add_call[2]["metadata"]["kin_memory_type"] == "semantic"


def test_search_scopes_to_the_owner_and_kin(settings):
    fake = FakeMem0({"test": True})
    service = MemoryService(settings, FakeRedis())
    service._memory = fake

    results = service.search(MemorySearchRequest(query="preferred answer style"))

    assert len(results) == 1
    assert results[0].similarity == 0.91
    query, kwargs = fake.search_calls[-1]
    assert query == "preferred answer style"
    assert kwargs["filters"] == {"user_id": settings.memory_user_id, "agent_id": settings.memory_agent_id}
    assert kwargs["top_k"] == 8
    assert kwargs["threshold"] == 0.15


def test_working_memory_remains_in_redis(settings):
    redis = FakeRedis()
    service = MemoryService(settings, redis)

    service.update_working("session-1", {"recent_inputs": ["hello"]})
    assert service.get_working("session-1")["state"]["recent_inputs"] == ["hello"]


def test_decision_directive_uses_mem0_consolidation(settings):
    fake = FakeMem0({"test": True})
    service = MemoryService(settings, FakeRedis())
    service._memory = fake

    results = service.remember_directive(
        "The user prefers infrastructure work to use Jira as the source of truth.",
        session_id="session-42",
        memory_type="semantic",
        importance=0.9,
        reason="durable workflow preference",
        goal_id=None,
        decision_event_id="00000000-0000-0000-0000-000000000002",
    )

    assert results[0]["event"] == "ADD"
    _, content, kwargs = fake.calls[-1]
    assert kwargs["infer"] is True
    assert kwargs["user_id"] == settings.memory_user_id
    assert kwargs["agent_id"] == settings.memory_agent_id
    assert kwargs["run_id"] == "session-42"

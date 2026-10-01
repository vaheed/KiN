from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class MemoryType(str, Enum):
    semantic = "semantic"
    episodic = "episodic"


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=100_000)
    memory_type: MemoryType = MemoryType.semantic
    importance: float = Field(default=0.5, ge=0, le=1)
    tags: list[str] = Field(default_factory=list, max_length=30)
    metadata: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None


class MemoryRecord(BaseModel):
    id: UUID
    memory_type: MemoryType
    content: str
    importance: float
    tags: list[str]
    metadata: dict[str, Any]
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MemorySearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=10_000)
    limit: int = Field(default=8, ge=1, le=50)
    min_similarity: float = Field(default=0.15, ge=0, le=1)


class MemorySearchResult(MemoryRecord):
    similarity: float


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=20_000)
    priority: int = Field(default=50, ge=0, le=100)
    context: dict[str, Any] = Field(default_factory=dict)


class GoalRecord(BaseModel):
    id: UUID
    title: str
    description: str
    status: Literal["active", "paused", "completed", "cancelled"]
    priority: int
    context: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EventCreate(BaseModel):
    event_type: str = Field(min_length=1, max_length=100)
    session_id: str | None = Field(default=None, max_length=500)
    goal_id: UUID | None = None
    summary: str = Field(min_length=1, max_length=10_000)
    payload: dict[str, Any] = Field(default_factory=dict)


class EventRecord(EventCreate):
    id: UUID
    created_at: datetime


class DecisionRequest(BaseModel):
    input: str = Field(min_length=1, max_length=50_000)
    session_id: str = Field(default="default", min_length=1, max_length=500)
    goal_id: UUID | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class ActionRisk(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ActionType(str, Enum):
    observe = "observe"
    investigate = "investigate"
    research = "research"
    communicate = "communicate"
    change = "change"
    restart = "restart"
    deploy = "deploy"
    delete = "delete"
    modify_security = "modify_security"
    external_request = "external_request"
    delegate = "delegate"
    no_action = "no_action"


class MemoryDirective(BaseModel):
    remember: bool = False
    memory_type: MemoryType = MemoryType.semantic
    content: str = ""
    importance: float = Field(default=0.5, ge=0, le=1)
    reason: str = ""


class Decision(BaseModel):
    goal: str = Field(min_length=1)
    intent: str = Field(min_length=1)
    action_type: ActionType
    action_risk: ActionRisk
    impact: Literal["low", "medium", "high"]
    reversible: bool
    confidence: float = Field(ge=0, le=1)
    should_investigate: bool = False
    proposed_action: str = Field(min_length=1)
    plan: list[str] = Field(min_length=1, max_length=20)
    requires_user_approval: bool = False
    approval_reason: str = ""
    next_step: str = Field(min_length=1)
    memory_directives: list[MemoryDirective] = Field(default_factory=list, max_length=10)

    @field_validator("plan")
    @classmethod
    def strip_plan(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("plan must contain at least one non-empty step")
        return cleaned


class PolicyResult(BaseModel):
    mode: Literal["balanced", "strict", "permissive"]
    decision_allowed: bool
    execution_class: Literal["automatic", "conditional", "approval"]
    requires_user_approval: bool
    reason: str


class DecisionResponse(BaseModel):
    decision: Decision
    policy: PolicyResult
    event_id: UUID


class WorkingMemoryResponse(BaseModel):
    session_id: str
    state: dict[str, Any]


class TrueForgeRunRequest(BaseModel):
    input: str = Field(min_length=1, max_length=50_000)
    session_id: str | None = None
    agent_name: str | None = None
    model: str | None = None


class TrueForgeRunResponse(BaseModel):
    session_id: str
    turn_id: str
    status: str
    output: str | None
    required_actions: list[dict[str, Any]] = Field(default_factory=list)

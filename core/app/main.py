from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from .config import Settings, get_settings
from .dependencies import Container
from .logging_config import configure_logging
from .schemas import (
    DecisionRequest,
    DecisionResponse,
    EventCreate,
    EventRecord,
    GoalCreate,
    GoalRecord,
    MemoryCreate,
    MemoryRecord,
    MemorySearchRequest,
    MemorySearchResult,
    TrueForgeRunRequest,
    TrueForgeRunResponse,
    WorkingMemoryResponse,
)
from .services.bifrost import BifrostError
from .services.trueforge import TrueForgeUnavailable

logger = logging.getLogger(__name__)
settings = get_settings()
configure_logging(settings.log_level)
container = Container(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not settings.disable_dependency_startup:
        container.startup()
    yield
    if not settings.disable_dependency_startup:
        container.shutdown()


app = FastAPI(title="KiN", version=settings.version, lifespan=lifespan)


@app.exception_handler(BifrostError)
async def handle_bifrost_error(_: Request, exc: BifrostError):
    return JSONResponse(status_code=502, content={"error": str(exc)})


@app.exception_handler(TrueForgeUnavailable)
async def handle_trueforge_error(_: Request, exc: TrueForgeUnavailable):
    return JSONResponse(status_code=502, content={"error": str(exc)})


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "KiN",
        "version": settings.version,
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
def ready() -> dict:
    checks: dict[str, str] = {}
    try:
        with container.db.connection() as conn:
            conn.execute("SELECT 1").fetchone()
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {exc}"
    try:
        container.db.redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
    try:
        container.bifrost.health()
        checks["bifrost"] = "ok"
    except Exception as exc:
        checks["bifrost"] = f"error: {exc}"
    try:
        import httpx

        response = httpx.get(f"{settings.trueforge_url.rstrip('/')}/healthz", timeout=5)
        checks["trueforge"] = "ok" if response.is_success else f"http {response.status_code}"
    except Exception as exc:
        checks["trueforge"] = f"error: {exc}"
    ok = all(value == "ok" for value in checks.values())
    payload = {"status": "ready" if ok else "not_ready", "checks": checks}
    if not ok:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=payload)
    return payload


@app.post("/v1/memory", response_model=MemoryRecord, status_code=201)
def create_memory(item: MemoryCreate):
    try:
        result = container.memories.create(item)
    except BifrostError:
        raise
    except Exception as exc:
        logger.exception("memory creation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    container.events.create(
        EventCreate(
            event_type="memory.created",
            summary=f"Created {item.memory_type.value} memory",
            payload={"memory_id": str(result.id), "importance": item.importance, "tags": item.tags},
        )
    )
    return result


@app.post("/v1/memory/search", response_model=list[MemorySearchResult])
def search_memory(request: MemorySearchRequest):
    return container.memories.search(request)


@app.get("/v1/working-memory", response_model=WorkingMemoryResponse)
def get_working_memory(session_id: str = "default"):
    return container.memories.get_working(session_id)


@app.get("/v1/goals", response_model=list[GoalRecord])
def list_goals():
    return [GoalRecord.model_validate(row) for row in container.goals.list()]


@app.post("/v1/goals", response_model=GoalRecord, status_code=201)
def create_goal(item: GoalCreate):
    result = container.goals.create(item)
    container.events.create(
        EventCreate(
            event_type="goal.created",
            goal_id=result["id"],
            summary=f"Created goal: {item.title}",
            payload={"priority": item.priority},
        )
    )
    return result


@app.get("/v1/events", response_model=list[EventRecord])
def list_events(limit: int = 100):
    limit = max(1, min(limit, 500))
    return [EventRecord.model_validate(row) for row in container.events.list(limit)]


@app.post("/v1/events", response_model=EventRecord, status_code=201)
def create_event(item: EventCreate):
    return container.events.create(item)


@app.get("/v1/integrations")
def integrations():
    return {
        "bifrost": {"url": settings.bifrost_url, "model": settings.decision_model},
        "trueforge": {
            "url": settings.trueforge_url,
            "enabled": settings.trueforge_enabled,
            "agent_name": settings.trueforge_agent_name or None,
            "model": settings.trueforge_model,
        },
        "memory": {
            "provider": "mem0",
            "vector_store": "pgvector",
            "collection": settings.memory_collection,
            "memory_llm_model": settings.memory_llm_model,
            "embedding_model": settings.embedding_model,
            "embedding_dimensions": settings.embedding_dimensions,
        },
    }


@app.post("/v1/decide", response_model=DecisionResponse)
def decide(request: DecisionRequest):
    working = container.memories.get_working(request.session_id)
    memory_results = container.memories.search(
        MemorySearchRequest(
            query=request.input,
            limit=settings.memory_search_limit,
            min_similarity=settings.memory_min_similarity,
        )
    )
    decision = container.decision_maker.decide(
        user_input=request.input,
        memory=[item.model_dump() for item in memory_results],
        working=working["state"],
        context=request.context,
    )
    policy = container.autonomy.evaluate(decision)

    new_working = {
        "last_input": request.input,
        "last_decision": decision.model_dump(mode="json"),
        "last_policy": policy.model_dump(mode="json"),
        "recent_inputs": [*(working["state"].get("recent_inputs", [])), request.input],
    }
    container.memories.update_working(request.session_id, new_working)
    event = container.events.create(
        EventCreate(
            event_type="decision.created",
            session_id=request.session_id,
            goal_id=request.goal_id,
            summary=decision.next_step,
            payload={
                "decision": decision.model_dump(mode="json"),
                "policy": policy.model_dump(mode="json"),
                "retrieved_memory_ids": [str(item.id) for item in memory_results],
            },
        )
    )

    # Let Mem0 perform durable-memory extraction/consolidation for curated
    # directives. Mem0 decides whether to add, update, or delete related facts.
    for directive in decision.memory_directives:
        if directive.remember and directive.content.strip():
            memory_results = container.memories.remember_directive(
                directive.content.strip(),
                session_id=request.session_id,
                memory_type=directive.memory_type.value,
                importance=directive.importance,
                reason=directive.reason,
                goal_id=str(request.goal_id) if request.goal_id else None,
                decision_event_id=str(event["id"]),
            )
            container.events.create(
                EventCreate(
                    event_type="memory.consolidated",
                    session_id=request.session_id,
                    goal_id=request.goal_id,
                    summary="Mem0 consolidated a Decision Maker memory directive",
                    payload={"results": memory_results, "reason": directive.reason},
                )
            )

    return DecisionResponse(decision=decision, policy=policy, event_id=event["id"])


@app.post("/v1/trueforge/run", response_model=TrueForgeRunResponse)
def run_trueforge(request: TrueForgeRunRequest):
    result = container.trueforge.run(
        input_text=request.input,
        session_id=request.session_id,
        agent_name=request.agent_name,
        model=request.model,
    )
    container.events.create(
        EventCreate(
            event_type="trueforge.turn.completed" if result["status"] not in {"running", "error"} else "trueforge.turn.observed",
            session_id=result["session_id"],
            summary=f"TrueForge turn {result['status']}",
            payload=result,
        )
    )
    return result

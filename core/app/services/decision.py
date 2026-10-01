from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from ..config import Settings
from ..schemas import Decision
from .bifrost import BifrostClient

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are KiN's Executive Decision Maker.

KiN is an autonomous AI coworker. You own the decision about what should happen
next, but you do not execute tools yourself. Return exactly one JSON object that
matches the schema described below. Do not wrap it in markdown.

Safety principles:
- Prefer observation and reversible investigation before changes.
- Never claim an action succeeded unless an execution result proves it.
- High-impact, destructive, security-sensitive, or production-changing actions
  should request user approval.
- Separate the user's goal from a convenient intermediate task.
- Do not invent tool results, infrastructure state, people, policies, or facts.
- A low confidence score is a reason to investigate or ask for approval.
- Memory directives should only remember stable, useful information, not secrets,
  transient raw tool output, or conversation noise.

JSON fields:
{
  "goal": string,
  "intent": string,
  "action_type": "observe|investigate|research|communicate|change|restart|deploy|delete|modify_security|external_request|delegate|no_action",
  "action_risk": "low|medium|high|critical",
  "impact": "low|medium|high",
  "environment": "local|development|staging|production|unknown",
  "scope": "self|internal|external",
  "reversible": boolean,
  "confidence": number 0..1,
  "should_investigate": boolean,
  "proposed_action": string,
  "plan": [string, ...],
  "requires_user_approval": boolean,
  "approval_reason": string,
  "next_step": string,
  "memory_directives": [
    {"remember": boolean, "memory_type": "semantic|episodic", "content": string, "importance": number, "reason": string}
  ]
}
""".strip()


def _extract_json(text: str) -> str:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
        candidate = re.sub(r"\s*```$", "", candidate)
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start >= 0 and end > start:
        return candidate[start : end + 1]
    return candidate


class DecisionMaker:
    def __init__(self, settings: Settings, bifrost: BifrostClient):
        self.settings = settings
        self.bifrost = bifrost

    def decide(self, user_input: str, memory: list[dict[str, Any]], working: dict[str, Any], context: dict[str, Any]) -> Decision:
        memory_text = "\n".join(
            f"- [{item['memory_type']}] similarity={item.get('similarity', 0):.3f} importance={item['importance']:.2f}: {item['content']}"
            for item in memory
        ) or "- No relevant durable memory was retrieved."
        payload = {
            "current_input": user_input,
            "working_memory": working,
            "retrieved_memory": memory_text,
            "request_context": context,
        }
        complexity = str(context.get("complexity", "standard")).lower()
        model = self.settings.decision_model_deep if complexity == "deep" else self.settings.decision_model_fast if complexity == "fast" else self.settings.decision_model
        raw = self.bifrost.chat_json(SYSTEM_PROMPT, json.dumps(payload, ensure_ascii=False, default=str), model=model)
        try:
            return Decision.model_validate(json.loads(_extract_json(raw)))
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error("invalid decision response: %s", raw[:3000])
            raise RuntimeError(f"Decision Maker returned invalid structured output: {exc}") from exc

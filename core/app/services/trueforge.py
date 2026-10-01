from __future__ import annotations

import logging

from ..config import Settings

logger = logging.getLogger(__name__)


class TrueForgeUnavailable(RuntimeError):
    pass


class TrueForgeClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = None

    def run(self, input_text: str, session_id: str | None = None, agent_name: str | None = None, model: str | None = None) -> dict:
        if not self.settings.trueforge_enabled:
            raise TrueForgeUnavailable("TrueForge integration is disabled")

        agent_name = agent_name or self.settings.trueforge_agent_name
        model = model or self.settings.trueforge_model

        try:
            if self.client is None:
                from trueforge_sdk import TrueForge

                kwargs = {"base_url": self.settings.trueforge_url, "timeout": 600}
                if self.settings.trueforge_token:
                    kwargs["token"] = self.settings.trueforge_token
                self.client = TrueForge(**kwargs)
            if session_id:
                session = type("Session", (), {"data": type("SessionData", (), {"id": session_id})()})()
            elif agent_name:
                session = self.client.sessions.create(agent={"name": agent_name})
            else:
                session = self.client.sessions.create(
                    agent={
                        "spec": {
                            "model": {"name": model},
                            "instructions": (
                                "You are the execution worker for KiN. Follow the user task exactly, "
                                "use tools only when available, report evidence, and stop for required approvals."
                            ),
                        }
                    }
                )

            created = self.client.sessions.create_turn(
                session_id=session.data.id,
                input=[{"type": "user.message", "content": input_text}],
            )
            turn = created.data
            for _ in range(720):
                if turn.state.status != "running":
                    break
                import time

                time.sleep(0.5)
                turn = self.client.sessions.get_turn(session_id=session.data.id, turn_id=created.data.id).data

            output = None
            if getattr(turn.state, "output", None) is not None:
                output = getattr(turn.state.output, "content", None)
            required_actions = getattr(turn.state, "required_actions", None) or getattr(turn.state, "requiredActions", None) or []
            return {
                "session_id": session.data.id,
                "turn_id": created.data.id,
                "status": turn.state.status,
                "output": output,
                "required_actions": required_actions,
            }
        except Exception as exc:
            logger.exception("TrueForge execution failed")
            raise TrueForgeUnavailable(f"TrueForge execution failed: {exc}") from exc

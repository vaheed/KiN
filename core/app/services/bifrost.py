from __future__ import annotations

import logging
from typing import Any

import httpx

from ..config import Settings

logger = logging.getLogger(__name__)


class BifrostError(RuntimeError):
    pass


class BifrostClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = httpx.Client(timeout=httpx.Timeout(120.0, connect=10.0))

    def close(self) -> None:
        self.client.close()

    def health(self) -> dict[str, Any]:
        response = self.client.get(f"{self.settings.bifrost_url.rstrip('/')}/health")
        response.raise_for_status()
        return response.json()

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.settings.bifrost_api_key:
            headers["Authorization"] = f"Bearer {self.settings.bifrost_api_key}"
        return headers

    def chat_json(self, system_prompt: str, user_prompt: str, model: str | None = None) -> str:
        payload = {
            "model": model or self.settings.decision_model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        response = self.client.post(
            f"{self.settings.bifrost_url.rstrip('/')}/v1/chat/completions",
            headers=self._headers(),
            json=payload,
        )
        if response.is_error:
            logger.error("Bifrost decision request failed status=%s body=%s", response.status_code, response.text[:1000])
            raise BifrostError(f"Bifrost returned HTTP {response.status_code}")
        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise BifrostError("Bifrost response did not contain a chat completion") from exc

    def embed(self, text: str) -> list[float]:
        payload: dict[str, Any] = {"model": self.settings.embedding_model, "input": text}
        # The column width and provider model are configured together. The
        # dimensions field is understood by OpenAI-compatible embedding APIs.
        payload["dimensions"] = self.settings.embedding_dimensions
        response = self.client.post(
            f"{self.settings.bifrost_url.rstrip('/')}/v1/embeddings",
            headers=self._headers(),
            json=payload,
        )
        if response.is_error:
            logger.error("Bifrost embedding request failed status=%s body=%s", response.status_code, response.text[:1000])
            raise BifrostError(f"Bifrost returned HTTP {response.status_code} for embeddings")
        data = response.json()
        try:
            vector = data["data"][0]["embedding"]
        except (KeyError, IndexError, TypeError) as exc:
            raise BifrostError("Bifrost response did not contain an embedding") from exc
        if len(vector) != self.settings.embedding_dimensions:
            raise BifrostError(
                f"Embedding dimension mismatch: expected {self.settings.embedding_dimensions}, got {len(vector)}"
            )
        return [float(value) for value in vector]

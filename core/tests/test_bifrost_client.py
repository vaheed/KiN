from __future__ import annotations

import httpx

from app.services.bifrost import BifrostClient, BifrostError


def test_chat_json_request(settings) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["json"] = request.content.decode()
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"ok": true}'}}]},
            request=request,
        )

    client = BifrostClient(settings)
    client.client.close()
    client.client = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        assert client.chat_json("system", "user") == '{"ok": true}'
        assert seen["url"].endswith("/v1/chat/completions")
    finally:
        client.close()


def test_embedding_dimension_validation(settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"embedding": [1.0]}]}, request=request)

    client = BifrostClient(settings)
    client.client.close()
    client.client = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        try:
            client.embed("x")
        except BifrostError as exc:
            assert "dimension mismatch" in str(exc).lower()
        else:
            raise AssertionError("dimension mismatch must fail")
    finally:
        client.close()

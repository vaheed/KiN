# Model setup

## Bifrost

The example config supports OpenAI through `OPENAI_API_KEY`. Set the key in `.env` and restart Bifrost:

```bash
docker compose up -d --force-recreate bifrost
```

The KiN Decision Maker calls Bifrost, which routes to OpenRouter. Standard/fast/deep lanes are selected with `context.complexity=standard|fast|deep`.

Embeddings use `KiN_EMBEDDING_MODEL` and `KiN_EMBEDDING_DIMENSIONS`.

## TrueForge

Open `http://127.0.0.1:8790` and configure a model provider/agent in the TrueForge UI. For a Compose-internal provider, Bifrost is reachable at:

```text
http://bifrost:8080
```

Before making that internal endpoint available to TrueForge, keep `NETWORK_POLICY_ENABLED=true` and add only the intended internal host(s) to `OUTBOUND_URL_ALLOWED_HOSTS`.

Set `TRUEFORGE_AGENT_NAME` to the saved agent name when you want KiN to run that agent through `POST /v1/trueforge/run`.

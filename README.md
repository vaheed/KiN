# KiN

**KiN — an AI coworker that thinks, remembers, and acts.**

KiN is a self-hosted executive layer for a persistent AI coworker. It owns goals, durable memory, decision state, autonomy policy, and audit history while delegating actual agent execution to [TrueForge](https://github.com/truefoundry/trueforge) and model access to [Bifrost](https://github.com/maximhq/bifrost).

## What KiN does

KiN v0.1.0 is intentionally small, but it is real software rather than a scaffold. It provides:

- an executive decision loop: observe → retrieve → decide → policy → record
- curated semantic and episodic memory in PostgreSQL + pgvector
- working memory in Redis
- explicit goal storage
- deterministic autonomy/approval gates around model-generated decisions
- audit events for decisions, memory, goals, and integration calls
- Bifrost-backed model calls for the Decision Maker
- a TrueForge execution client for running a configured agent session
- a small HTTP API and health/readiness endpoints

The v1 boundary is deliberately clear:

```text
KiN = identity + goals + memory + decision making + autonomy + orchestration
TrueForge = agent execution + tools + MCP + sandbox + sessions
Bifrost = model gateway + provider routing
PostgreSQL/pgvector = durable state + semantic retrieval
Redis = working state + transient execution context
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for Mermaid diagrams and the design decisions behind each boundary.

## Quick start

Requirements:

- Docker Engine / Docker Desktop with Compose v2
- 4 GB RAM available to the Compose project is a practical starting point
- an API key for at least one Bifrost provider if you want live decisions

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Replace the demo secrets and set your provider credentials. Generate strong values with:

```bash
openssl rand -hex 32
```

3. Start the stack:

```bash
docker compose up -d
```

4. Check KiN:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

5. Create a memory:

```bash
curl -X POST http://127.0.0.1:8000/v1/memory \\
  -H 'Content-Type: application/json' \\
  -d '{"content":"KiN should prefer reversible actions unless a user policy says otherwise.","memory_type":"semantic","importance":0.9,"tags":["kin","autonomy"]}'
```

6. Ask the Decision Maker:

```bash
curl -X POST http://127.0.0.1:8000/v1/decide \\
  -H 'Content-Type: application/json' \\
  -d '{"input":"Check why an internal service is unavailable and propose the safest next step.","goal_id":null,"session_id":"default"}'
```

The Decision Maker calls Bifrost, with **OpenRouter behind Bifrost**. The standard lane uses `anthropic/claude-sonnet-5.5`; fast and deep lanes use `google/gemini-3.8-flash` and `anthropic/claude-opus-5.5`. The lane can be selected with `context.complexity=fast|standard|deep`.

## Decision model and JEV

JEV 1.13 remains an optional future gate setting and is disabled by default. OpenRouter documents JEV as a non-generative model exposed through its Decisions API, not the normal chat-completions API, so it is not used as KiN's primary Bifrost chat model. The main executive path uses reasoning models with structured output support.

## TrueForge

TrueForge is intentionally not reimplemented in KiN. KiN talks to the current TrueForge SDK and delegates execution to a TrueForge agent/session. The first setup step is to create an agent in the TrueForge UI and configure its model provider to reach Bifrost (or another OpenAI-compatible model endpoint).

TrueForge is served at:

```text
http://127.0.0.1:8790
```

The service is kept on the Compose network and its Web UI + API are mapped to `127.0.0.1:8790` by default. Hosted mode is used (`STANDALONE=false`) so TrueForge uses PostgreSQL + Redis, matching its current upstream deployment model.

For an OpenAI-compatible model provider in TrueForge, the internal Bifrost endpoint is:

```text
http://bifrost:8080
```

The KiN TrueForge client uses a configurable agent name when `TRUEFORGE_AGENT_NAME` is set, or an inline agent spec using `TRUEFORGE_MODEL` when it is not. The latter still requires the model to exist in the TrueForge model registry/catalog.

## TrueForge Web UI

TrueForge serves its Web UI and API from the same server. KiN publishes it on `127.0.0.1:8790` so you can configure agents, models, skills, MCP servers, and approvals. Keep this local by default; for remote/shared access use TLS and TrueForge OIDC. Upstream warns that an unauthenticated hosted deployment gives anyone who can reach the URL the shared admin identity.

## Bifrost

Bifrost is configured declaratively using `infra/bifrost/config.json`. **OpenRouter is the sample provider behind Bifrost**. The configuration is file-only (`config_store.enabled=false`) and request-log persistence is disabled in v0.1.0. The provider credential is referenced with Bifrost's `env.OPENROUTER_API_KEY` syntax; no real secret is stored in Git.

Bifrost is served at:

```text
http://127.0.0.1:8080
```

The internal inference API is:

```text
http://bifrost:8080/v1/chat/completions
http://bifrost:8080/v1/embeddings
```

## Memory model

KiN uses three explicit memory classes:

1. **Working memory** — JSON state in Redis for the current session/task.
2. **Semantic memory** — curated durable facts/preferences/projects in PostgreSQL + pgvector.
3. **Episodic memory** — durable event history recording what KiN decided, what it attempted, and what the result was.

Memory is never automatically persisted merely because text appeared in a conversation. The API requires the caller to create a durable memory, and the decision schema can emit memory directives for future consolidation logic.

## Autonomy

Autonomy uses a configurable profile (`cautious`, `balanced`, `autonomous`) plus a mode derived from the actual decision (`idle`, `observe`, `investigate`, `communicate`, `execute`, `delegate`, `destructive`). The local gate evaluates risk, impact, reversibility, confidence, environment, and scope; the model cannot grant itself permission.

Examples:

```text
mtr / read-only diagnostics      -> automatic
restart development container   -> conditional/automatic
restart production router       -> approval
production database deletion    -> approval
```

The v0.1.0 API does not execute arbitrary system actions by itself. Approval is represented explicitly in the decision state and audit log; actual tool execution remains a TrueForge concern.

## API

```text
GET  /health
GET  /ready
POST /v1/decide
POST /v1/memory
POST /v1/memory/search
GET  /v1/working-memory
GET  /v1/goals
POST /v1/goals
GET  /v1/events
POST /v1/events
GET  /v1/integrations
POST /v1/trueforge/run
```

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r core/requirements.txt
make test
make validate
```

Integration tests use the same service URLs as Compose. They are disabled by default so a developer can run unit tests without Docker. To enable them:

```bash
export KiN_RUN_INTEGRATION=1
make test-integration
```

## Testing and validation

The repository contains tests for configuration parsing, decision schemas, autonomy policy, API behavior, memory repositories, and optional PostgreSQL/Redis integration.

Before a release, run:

```bash
docker compose config
make validate
make test
```

The delivery environment used for this v0.1.0 package did not have Docker installed or external registry/DNS access, so image pull/build/start/runtime validation could not be performed here. See `docs/UPSTREAM.md` for the exact upstream versions and the validation boundary.

## Security

The default Compose ports bind only to loopback. PostgreSQL and Redis are never published to the host. The production hardening checklist is in [SECURITY.md](SECURITY.md).

High-risk actions must be approved. Treat the TrueForge agent runtime as a privileged system: restrict its MCP servers and tool permissions and enable authentication before exposing it beyond a trusted local network.

## Troubleshooting

**`/ready` reports Bifrost unavailable:** verify `docker compose logs bifrost` and the provider/API key configuration in `.env`.

**Decision calls fail with provider errors:** confirm the Bifrost model name and provider mapping. Verify that the selected OpenRouter model ID is enabled in the Bifrost provider configuration.

**TrueForge execution fails:** configure a TrueForge agent/model first and set `TRUEFORGE_AGENT_NAME`, or configure the selected model in the TrueForge model catalog before using inline execution.

**Postgres fails to initialize after changing credentials:** this usually means an existing volume contains the old credentials. For a disposable development installation:

```bash
docker compose down -v
docker compose up -d
```

Do not use `down -v` against data you need.

## Roadmap

Future versions can add proactive goal workers, scheduled execution, richer memory consolidation, channels such as Telegram/email/web, MCP registries, infrastructure connectors, and a browser/mobile UI without moving those responsibilities into KiN's executive core.

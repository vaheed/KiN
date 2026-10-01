# Upstream / integration manifest

This file records the upstream components that KiN directly relies on and the interface assumptions used in v0.1.0.

> Verified against current upstream pages available on 2026-10-01. Docker runtime validation was not possible in the delivery sandbox because the Docker CLI/daemon and external DNS were unavailable.

## TrueForge

- Repository: `truefoundry/trueforge`
- Application package: `@truefoundry/trueforge`
- KiN pin: **0.3.1**
- SDK pin: **trueforge-sdk 0.2.1**
- Container strategy: KiN builds a local image from `node:24-slim` and installs the published npm package, matching the upstream production Dockerfile pattern.
- Internal port: **8790**
- Health endpoint: **GET /healthz**
- Hosted mode: `STANDALONE=false`
- Storage: PostgreSQL + Redis
- SDK behavior used by KiN: `sessions.create(...)`, `sessions.create_turn(...)`, `sessions.get_turn(...)`
- Token: optional when OIDC is disabled; required when TrueForge OIDC is enabled.
- Model spec: `agent.spec.model.name` is a `provider/model` FQN when using an inline agent spec.
- Agent model and tool approvals remain under TrueForge; KiN does not reproduce that runtime.

Why 0.3.1: the current upstream release list shows `@truefoundry/trueforge@0.3.1` as the latest release on 2026-09-30, with commit `75e877f`.

Sources:

- https://github.com/truefoundry/trueforge
- https://github.com/truefoundry/trueforge/blob/main/Dockerfile
- https://github.com/truefoundry/trueforge/blob/main/docs/quickstart.mdx
- https://github.com/truefoundry/trueforge/blob/main/docs/api/quickstart.mdx
- https://github.com/truefoundry/trueforge/blob/main/docs/api/use-agent.mdx
- https://github.com/truefoundry/trueforge/blob/main/docs/create-agent/overview.mdx
- https://github.com/truefoundry/trueforge/blob/main/packages/trueforge/.env.example

## Mem0 OSS

- Repository: mem0ai/mem0
- Python package: mem0ai
- KiN pin: **2.2.1**
- License: Apache-2.0
- Integration: Python library inside KiN Core via Memory.from_config(...)
- Durable vector store: PostgreSQL + pgvector
- Memory history: local SQLite file under /app/data/mem0/history.db
- LLM + embeddings: Mem0's OpenAI-compatible providers point to **Bifrost /v1**, not directly to OpenRouter
- Durable-memory calls use Mem0's add(..., infer=True) for Decision Maker directives; explicit API writes use infer=False
- Memory retrieval is scoped with filters containing user_id and agent_id plus configurable top-k/threshold
- Native expiration dates are passed to Mem0 when an explicit memory has an expiry date
- KiN deliberately does not pass OPENROUTER_API_KEY to the KiN container. Current Mem0 OpenAI LLM code checks that environment variable first and would otherwise route around the configured Bifrost endpoint.

Why 2.2.1: PyPI shows **2.2.1** released on 2026-09-25 and lists it as the current release. The upstream documentation confirms Python OSS configuration with Memory.from_config, OpenAI-compatible endpoints, and pgvector support.

Sources:

- https://pypi.org/project/mem0ai/2.2.1/
- https://github.com/mem0ai/mem0/blob/main/docs/open-source/configuration.mdx
- https://github.com/mem0ai/mem0/blob/main/docs/components/vectordbs/dbs/pgvector.mdx
- https://github.com/mem0ai/mem0/blob/main/mem0/memory/main.py
- https://github.com/mem0ai/mem0/blob/main/mem0/llms/openai.py
## Bifrost

- Repository: `maximhq/bifrost`
- Container: `maximhq/bifrost`
- KiN pin: **v2.2.4**
- Internal port: **8080**
- Health endpoint: **GET /health**
- Inference endpoint: **POST /v1/chat/completions**
- Embeddings endpoint: **POST /v1/embeddings**
- Configuration: `infra/bifrost/config.json`
- Config mode: `config_store.enabled=false` (file-only)
- Log store: `logs_store.enabled=false` in KiN v0.1.0 to keep the gateway stateless; KiN retains its own durable audit history.
- Secrets: `env.*` references, never hard-coded provider credentials
- Example provider: OpenRouter with model wildcard routing

Why 2.2.4: the upstream release page documents the Docker image `maximhq/bifrost:v2.2.4` for that release.

Sources:

- https://github.com/maximhq/bifrost
- https://github.com/maximhq/bifrost/releases
- https://github.com/maximhq/bifrost/blob/dev/docs/deployment-guides/config-json.mdx
- https://github.com/maximhq/bifrost/blob/dev/docs/openapi/paths/management/health.yaml
- https://github.com/maximhq/bifrost/blob/dev/docs/quickstart/gateway/provider-configuration.mdx

## Decision model note

JEV 1.13 is not the primary Decision Maker in v0.1.0. OpenRouter documents JEV as a non-generative model served by its Decisions API, while KiN uses Bifrost's chat/embeddings interface. A disabled JEV gate setting is kept for a future integration path; the main executive path uses structured-output reasoning models.

## PostgreSQL + pgvector

- PostgreSQL line: **17.x** through the official pgvector image.
- pgvector: **0.8.6**.
- Compose image: `pgvector/pgvector:0.8.6-pg17`
- Extension: `vector`
- Vector width: **1536** by default, matching `text-embedding-3-small` in the sample configuration.
- KiN uses a dedicated `kin` database/user.
- TrueForge uses a separate `trueforge` database/user on the same Postgres server.

Sources:

- https://github.com/pgvector/pgvector
- https://github.com/pgvector/pgvector/blob/master/README.md
- https://github.com/pgvector/pgvector/blob/master/CHANGELOG.md
- https://hub.docker.com/_/postgres

Note: pgvector's current upstream Docker docs publish `0.8.6-pg17`/`pg17` tags; KiN chooses PostgreSQL 17 for the v0.1.0 Compose contract because it matches the Postgres major used by the current TrueForge hosted-mode example while retaining the current pgvector 0.8.6 release.

## Redis

- Compose image: **redis:8.10.1-alpine**
- Internal port: **6379**
- Persistence: AOF (`appendonly yes`)
- Host port: not published

Source:

- https://hub.docker.com/_/redis

## Application dependencies

KiN Core is implemented in Python with FastAPI, Pydantic, psycopg, redis-py, HTTPX, Mem0 OSS, and the official TrueForge SDK. These are pinned in `core/requirements.txt`. They are ordinary application dependencies rather than external services, and their exact pins are part of the v0.1.0 reproducibility contract.

## Integration assumptions and non-claims

1. The sandbox did not contain Docker (`docker: command not found`), so `docker compose pull/build/up/ps/runtime` could not be executed.
2. External DNS resolution was unavailable, so image registry access could not be tested from the sandbox.
3. Python source compilation, JSON validation, static Compose parsing, and unit tests were run locally where possible.
4. A successful static build does not prove the external provider/model credentials work. The README never claims that the provider call was live-tested in the sandbox.

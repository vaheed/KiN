# Upstream / integration manifest

This file records the upstream components that KIN directly relies on and the interface assumptions used in v0.1.0.

> Verified against current upstream pages available on 2026-10-01. Docker runtime validation was not possible in the delivery sandbox because the Docker CLI/daemon and external DNS were unavailable.

## TrueForge

- Repository: `truefoundry/trueforge`
- Application package: `@truefoundry/trueforge`
- KIN pin: **0.3.1**
- SDK pin: **trueforge-sdk 0.2.1**
- Container strategy: KIN builds a local image from `node:24-slim` and installs the published npm package, matching the upstream production Dockerfile pattern.
- Internal port: **8790**
- Health endpoint: **GET /healthz**
- Hosted mode: `STANDALONE=false`
- Storage: PostgreSQL + Redis
- SDK behavior used by KIN: `sessions.create(...)`, `sessions.create_turn(...)`, `sessions.get_turn(...)`
- Token: optional when OIDC is disabled; required when TrueForge OIDC is enabled.
- Model spec: `agent.spec.model.name` is a `provider/model` FQN when using an inline agent spec.
- Agent model and tool approvals remain under TrueForge; KIN does not reproduce that runtime.

Why 0.3.1: the current upstream release list shows `@truefoundry/trueforge@0.3.1` as the latest release on 2026-09-30, with commit `75e877f`.

Sources:

- https://github.com/truefoundry/trueforge
- https://github.com/truefoundry/trueforge/blob/main/Dockerfile
- https://github.com/truefoundry/trueforge/blob/main/docs/quickstart.mdx
- https://github.com/truefoundry/trueforge/blob/main/docs/api/quickstart.mdx
- https://github.com/truefoundry/trueforge/blob/main/docs/api/use-agent.mdx
- https://github.com/truefoundry/trueforge/blob/main/docs/create-agent/overview.mdx
- https://github.com/truefoundry/trueforge/blob/main/packages/trueforge/.env.example

## Bifrost

- Repository: `maximhq/bifrost`
- Container: `maximhq/bifrost`
- KIN pin: **v2.2.4**
- Internal port: **8080**
- Health endpoint: **GET /health**
- Inference endpoint: **POST /v1/chat/completions**
- Embeddings endpoint: **POST /v1/embeddings**
- Configuration: `infra/bifrost/config.json`
- Config mode: `config_store.enabled=false` (file-only)
- Log store: `logs_store.enabled=false` in KIN v0.1.0 to keep the gateway stateless; KIN retains its own durable audit history.
- Secrets: `env.*` references, never hard-coded provider credentials
- Example provider: OpenAI with model wildcard routing

Why 2.2.4: the upstream release page documents the Docker image `maximhq/bifrost:v2.2.4` for that release.

Sources:

- https://github.com/maximhq/bifrost
- https://github.com/maximhq/bifrost/releases
- https://github.com/maximhq/bifrost/blob/dev/docs/deployment-guides/config-json.mdx
- https://github.com/maximhq/bifrost/blob/dev/docs/openapi/paths/management/health.yaml
- https://github.com/maximhq/bifrost/blob/dev/docs/quickstart/gateway/provider-configuration.mdx

## PostgreSQL + pgvector

- PostgreSQL line: **17.x** through the official pgvector image.
- pgvector: **0.8.6**.
- Compose image: `pgvector/pgvector:0.8.6-pg17`
- Extension: `vector`
- Vector width: **1536** by default, matching `text-embedding-3-small` in the sample configuration.
- KIN uses a dedicated `kin` database/user.
- TrueForge uses a separate `trueforge` database/user on the same Postgres server.

Sources:

- https://github.com/pgvector/pgvector
- https://github.com/pgvector/pgvector/blob/master/README.md
- https://github.com/pgvector/pgvector/blob/master/CHANGELOG.md
- https://hub.docker.com/_/postgres

Note: pgvector's current upstream Docker docs publish `0.8.6-pg17`/`pg17` tags; KIN chooses PostgreSQL 17 for the v0.1.0 Compose contract because it matches the Postgres major used by the current TrueForge hosted-mode example while retaining the current pgvector 0.8.6 release.

## Redis

- Compose image: **redis:8.10.1-alpine**
- Internal port: **6379**
- Persistence: AOF (`appendonly yes`)
- Host port: not published

Source:

- https://hub.docker.com/_/redis

## Application dependencies

KIN Core is implemented in Python with FastAPI, Pydantic, psycopg, redis-py, HTTPX, and the official TrueForge SDK. These are pinned in `core/requirements.txt`. They are ordinary application dependencies rather than external services, and their exact pins are part of the v0.1.0 reproducibility contract.

## Integration assumptions and non-claims

1. The sandbox did not contain Docker (`docker: command not found`), so `docker compose pull/build/up/ps/runtime` could not be executed.
2. External DNS resolution was unavailable, so image registry access could not be tested from the sandbox.
3. Python source compilation, JSON validation, static Compose parsing, and unit tests were run locally where possible.
4. A successful static build does not prove the external provider/model credentials work. The README never claims that the provider call was live-tested in the sandbox.

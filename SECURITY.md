# Security

KIN can eventually control real infrastructure, so the security model treats model output as an untrusted proposal rather than an authorization decision.

## Defaults

- Host ports bind to `127.0.0.1` by default.
- PostgreSQL and Redis are internal-only and have no host port mapping.
- Bifrost credentials are injected as environment variables and referenced from its config with `env.*`.
- TrueForge runs in hosted mode with a service API key.
- KIN applies a deterministic autonomy policy after model output.
- High/critical risk, destructive/security-sensitive, high-impact, irreversible, or low-confidence actions require user approval.

## Before exposing anything beyond localhost

Enable an authenticated reverse proxy with TLS. Do not directly publish PostgreSQL or Redis. Enable TrueForge OIDC for shared deployments, replace demo secrets, restrict MCP connectors and skills, and use least-privilege identities for infrastructure tools.

For production, prefer a dedicated secret manager and short-lived credentials. Avoid placing credentials in Compose YAML or Git. Rotate the Bifrost encryption key and application/database credentials according to your operational policy.

## Model/provider boundaries

A model may suggest an action, but the model response is not an authorization grant. KIN's policy code is the final safety floor for the executive decision. TrueForge tool approvals remain independently enforced by TrueForge for tools marked `@write` or `@destructive`.

## Auditability

The `events` table records decision creation, goal creation, memory creation/consolidation, and TrueForge turn outcomes. Keep the database protected and back it up. Do not log provider secrets or raw authorization tokens.

## Production hardening checklist

1. Set `HOST_BIND_IP` only to a trusted interface if a reverse proxy is required; otherwise retain loopback.
2. Generate unique database passwords and Bifrost/TrueForge API keys.
3. Enable TrueForge OIDC before sharing its URL.
4. Restrict the TrueForge model-provider outbound allowlist to only the model gateways you intentionally use.
5. Require approvals for production changes and destructive tools.
6. Back up both KIN and TrueForge PostgreSQL databases.
7. Monitor `/health`, `/ready`, TrueForge `/healthz`, and Bifrost `/health`.
8. Review and rotate provider credentials.

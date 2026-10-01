# ADR 0001 — Keep KIN as the executive layer

## Decision

KIN owns identity, goals, memory, decision making, autonomy policy, and orchestration. TrueForge owns agent execution. Bifrost owns model routing.

## Why

Duplicating MCP, sandbox, session, tool-approval, model-provider, or workflow functionality would create two competing runtimes and make long-running behavior harder to reason about.

## Consequences

- KIN remains small enough to run in one Compose project.
- Upstream improvements in TrueForge/Bifrost can be adopted without replacing KIN's core state model.
- Some execution setup is intentionally delegated to TrueForge's model/tool configuration.

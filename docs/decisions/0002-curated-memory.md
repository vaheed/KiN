# ADR 0002 — Curated memory, not a vector dump

## Decision

KiN remains responsible for deciding what is worth remembering. Mem0 OSS is responsible for the durable-memory mechanics: extraction, consolidation, deduplication, updates, semantic search, expiration handling, and memory history.

The storage boundary is deliberately simple:

- Redis stores short-lived working state.
- Mem0 OSS stores durable semantic memory in PostgreSQL + pgvector.
- KiN's PostgreSQL events table stores episodic/audit history for decisions and execution observations.

KiN does not maintain a second vector-search or memory-consolidation implementation.

## Why

A vector database by itself is not a memory system. Durable agent memory also needs extraction, lifecycle, provenance, entity scoping, update/delete behavior, and retrieval semantics.

Mem0 OSS already provides those memory operations and supports PostgreSQL + pgvector as a self-hosted vector store. Reusing it keeps KiN's executive core small and avoids maintaining parallel memory logic.

Decision Maker memory directives remain intentionally curated: the model must explicitly request remembering useful information. Those directives are sent to Mem0 with inference enabled so Mem0 can reconcile them with existing memory. Explicit /v1/memory API writes use infer=false because the caller has already supplied the final memory content. Mem0 supports scoping memory by user_id, agent_id, and run_id, which KiN uses for owner/agent/session isolation.

## Consequences

- Mem0 OSS is a runtime dependency of KiN Core rather than a separate Compose service.
- Mem0's durable vector/payload data lives in the KiN PostgreSQL database through pgvector.
- Mem0's local history database is persisted under the KiN named data volume.
- Redis remains independent working memory and is not treated as durable personal memory.
- KiN events remain append-oriented operational history rather than semantic memory documents.
- Future memory features should prefer supported Mem0 primitives before introducing custom memory infrastructure.

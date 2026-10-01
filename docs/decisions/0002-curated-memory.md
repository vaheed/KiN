# ADR 0002 — Curated memory, not a vector dump

## Decision

Memory is explicitly typed and curated. Semantic memory is vector-searchable; episodic history is append-oriented event data. Redis is only working state.

## Why

A vector database is not an adequate substitute for lifecycle, provenance, importance, expiry, or event history. Durable memory should be understandable and maintainable by a human.

## Consequences

- v0.1.0 stores provenance metadata with memory records.
- Consolidation is explicit rather than automatic on every model response.
- Future versions can add summarization, deduplication, and forgetting without redesigning the storage boundary.

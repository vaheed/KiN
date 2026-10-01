# Changelog

All notable changes to KiN are documented here.

## [Unreleased]

### Changed

- Replaced KiN's custom semantic-memory implementation with Mem0 OSS 2.2.1.
- Routed Mem0 LLM and embedding traffic through Bifrost so OpenRouter remains behind one model gateway.
- Moved durable vector storage to Mem0 + PostgreSQL/pgvector while retaining Redis for working state and KiN PostgreSQL events for episodic/audit history.
- Removed obsolete custom-memory repositories and tests.
- Normalized public health metadata and documentation to the KiN brand.

## [0.1.0] - 2026-10-01

### Added

- Initial KiN executive core with goals, memory, decision state, and autonomy policy.
- PostgreSQL + pgvector durable memory and episodic events.
- Redis working memory.
- Bifrost model gateway integration for chat decisions and embeddings.
- TrueForge SDK integration for execution sessions/turns.
- Localhost-only Docker Compose topology.
- Mermaid architecture documentation, operational docs, tests, and validation targets.

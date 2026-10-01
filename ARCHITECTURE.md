# KiN Architecture

KiN is an executive/orchestration layer around two upstream systems rather than a competing agent framework or model gateway.

## 1. System architecture

```mermaid
flowchart TD
    U[You / Channel] --> K[KiN Core]
    K --> D[Decision Maker]
    D --> B[Bifrost]
    B --> M[Model Providers]
    K --> A[Autonomy Policy]
    K --> G[Goal Manager]
    K --> MM[Memory Manager]
    K --> E[Event / Audit Store]
    MM --> R[Redis Working Memory]
    MM --> M[Mem0 OSS]
    M --> P[PostgreSQL + pgvector]
    K --> T[TrueForge]
    T --> X[Planner / Executor / Reviewer]
    X --> TOOLS[Tools / MCP / Sandbox]
```

### Boundary rule

KiN decides **what should happen next**. TrueForge decides **how agent work is executed**. Bifrost decides **which model/provider serves a model request**.

## 2. Main decision loop

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant K as KiN Core
    participant R as Redis
    participant P as PostgreSQL/pgvector
    participant B as Bifrost
    participant T as TrueForge

    C->>K: POST /v1/decide
    K->>R: Read working memory
    K->>P: Semantic memory search
    K->>B: Executive decision request
    B-->>K: Structured decision
    K->>K: Apply autonomy policy
    K->>P: Persist decision event
    K->>R: Update working state
    alt action is approved/automatic and execution is requested
        K->>T: Run agent session/turn
        T-->>K: Result / paused approval
        K->>P: Persist episodic outcome
        K->>K: Review / replan boundary
    end
    K-->>C: Decision + policy result
```

## 3. Memory architecture

```mermaid
flowchart LR
    OBS[Conversation / Tool Result / Decision] --> CUR[KiN Memory Manager]
    CUR -->|temporary| R[(Redis)]
    CUR -->|durable| M[Mem0 OSS]
    M --> L[Extraction / consolidation / dedup / retrieval]
    L --> P[(PostgreSQL + pgvector)]
    M --> H[(Mem0 SQLite history)]
    CUR -->|episodic audit| E[(KiN PostgreSQL events)]
    RET[Decision retrieval] --> R
    RET --> M
```

Mem0 OSS owns durable memory semantics. KiN does not maintain a second vector-search, extraction, deduplication, or consolidation engine. Redis remains working memory and the KiN events table remains the durable episodic/audit stream.

## 4. Autonomy policy

```mermaid
flowchart TD
    X[Decision] --> MODE[Derive decision mode]
    MODE --> O[idle / observe / investigate]
    MODE --> C[communicate]
    MODE --> E[execute / delegate]
    MODE --> D[destructive]
    O --> P[Apply autonomy profile + risk checks]
    C --> P
    E --> P
    D --> AP[Require approval]
    P -->|safe + reversible + confident| AUTO[Automatic]
    P -->|moderate risk / external effect| COND[Conditional]
    P -->|high risk / production / irreversible / low confidence| AP
```

The profile (`cautious`, `balanced`, `autonomous`) adjusts thresholds. The mode is derived from the decision itself. JEV 1.13 is an optional future gate because its OpenRouter interface is a Decisions API rather than normal chat completions.

## 5. TrueForge integration

```mermaid
flowchart TD
    K[KiN Core] --> TF[TrueForge SDK]
    TF --> S[Session]
    S --> TURN[Turn]
    TURN --> EX[TrueForge Agent Loop]
    EX --> PLAN[Planning / Context]
    EX --> MCP[MCP Tools]
    EX --> SB[Sandbox]
    EX --> REV[Review / Human Checkpoints]
```

KiN does not implement MCP, sandboxing, tool approval protocols, or a separate agent runtime. The TrueForge SDK is used only for session/turn orchestration.

## 6. Bifrost / model routing

```mermaid
flowchart TD
    K[KiN Decision Maker] --> G[Bifrost -> OpenRouter API]
    G --> R{Routing / Provider}
    R --> O[OpenAI]
    R --> A[Anthropic]
    R --> L[Other / compatible endpoint]
    G --> E[Embedding endpoint]
```

KiN uses OpenRouter model IDs, such as `anthropic/claude-sonnet-5.5`, and does not contain provider-specific SDK code.

## 7. Docker Compose topology

```mermaid
graph TB
    subgraph Compose[Docker Compose network]
        K[kin:8000]
        T[trueforge:8790]
        B[bifrost:8080]
        P[(postgres:5432)]
        R[(redis:6379)]
    end

    K --> B
    K --> T
    K --> P
    K --> R
    T --> P
    T --> R
    B --> Internet[Model provider network]
    Host[localhost] --> K
    Host --> T
    Host --> B
```

PostgreSQL and Redis have no host port mapping. TrueForge publishes its Web UI + API on localhost:8790 by default; public exposure requires TLS + OIDC.

## 8. Future proactive / long-running goal loop

```mermaid
flowchart TD
    GOAL[Durable Goal] --> TRIGGER[Time / Event / Observation]
    TRIGGER --> OBS[Observe]
    OBS --> MEM[Retrieve + Consolidate Memory]
    MEM --> DEC[Decision Maker]
    DEC --> POLICY[Autonomy Policy]
    POLICY --> EXEC[TrueForge execution]
    EXEC --> REVIEW[Review result]
    REVIEW --> LEARN[Learn]
    LEARN --> GOAL
    POLICY --> APPROVAL[User approval]
    APPROVAL --> EXEC
```

The worker/scheduler is intentionally future architecture for v0.1.0. TrueForge itself already supports schedules; KiN will consume that capability rather than building another scheduler when the proactive layer is added.

## State model

```text
Goal
  -> Decision
      -> Policy evaluation
          -> Task / execution request
              -> Observation
                  -> Review
                      -> Event / memory
                          -> next Decision
```

## Data ownership

| Data | Owner | Store |
| --- | --- | --- |
| Current working context | KiN | Redis |
| Goals | KiN | PostgreSQL |
| Durable semantic memory | Mem0 OSS under KiN | PostgreSQL + pgvector |
| Mem0 memory history | Mem0 OSS under KiN | SQLite on the KiN data volume |
| Episodic audit/events | KiN | PostgreSQL |
| Agent sessions/turns | TrueForge | TrueForge PostgreSQL schema |
| Provider routing/config | Bifrost | Bifrost file config in v0.1.0 |

The Compose project uses a single PostgreSQL server with separate databases/users: KiN's `kin` database and TrueForge's `trueforge` database.

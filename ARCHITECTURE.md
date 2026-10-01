# KIN Architecture

KIN is an executive/orchestration layer around two upstream systems rather than a competing agent framework or model gateway.

## 1. System architecture

```mermaid
flowchart TD
    U[You / Channel] --> K[KIN Core]
    K --> D[Decision Maker]
    D --> B[Bifrost]
    B --> M[Model Providers]
    K --> A[Autonomy Policy]
    K --> G[Goal Manager]
    K --> MM[Memory Manager]
    K --> E[Event / Audit Store]
    MM --> R[Redis Working Memory]
    MM --> P[PostgreSQL + pgvector]
    K --> T[TrueForge]
    T --> X[Planner / Executor / Reviewer]
    X --> TOOLS[Tools / MCP / Sandbox]
```

### Boundary rule

KIN decides **what should happen next**. TrueForge decides **how agent work is executed**. Bifrost decides **which model/provider serves a model request**.

## 2. Main decision loop

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant K as KIN Core
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
    OBS[Conversation / Tool Result / Decision] --> CUR[Memory Manager]
    CUR -->|temporary| R[(Redis)]
    CUR -->|semantic| S[(PostgreSQL)]
    S --> V[(pgvector)]
    CUR -->|episodic| E[(PostgreSQL events)]
    RET[Retrieval] --> R
    RET --> V
    RET --> E
    CONS[Future consolidation] --> CUR
```

The v0.1.0 memory API deliberately requires an explicit memory type and importance. Expiration and tags are stored as metadata. Episodic events are append-oriented audit records, not free-form semantic blobs.

## 4. Autonomy policy

```mermaid
flowchart TD
    X[Proposed action] --> R{Risk}
    R -->|low| I{Impact}
    R -->|medium| C{Confidence + Reversibility}
    R -->|high/critical| AP[Require approval]
    I -->|low| AUTO[Automatic]
    I -->|medium| C
    C -->|high confidence + reversible| COND[Conditional / automatic]
    C -->|otherwise| AP
    ENV[Environment / scope] --> AUTO
    ENV --> COND
    ENV --> AP
```

The local policy is intentionally stricter than the model prompt. The model cannot grant itself permission.

## 5. TrueForge integration

```mermaid
flowchart TD
    K[KIN Core] --> TF[TrueForge SDK]
    TF --> S[Session]
    S --> TURN[Turn]
    TURN --> EX[TrueForge Agent Loop]
    EX --> PLAN[Planning / Context]
    EX --> MCP[MCP Tools]
    EX --> SB[Sandbox]
    EX --> REV[Review / Human Checkpoints]
```

KIN does not implement MCP, sandboxing, tool approval protocols, or a separate agent runtime. The TrueForge SDK is used only for session/turn orchestration.

## 6. Bifrost / model routing

```mermaid
flowchart TD
    K[KIN Decision Maker] --> G[Bifrost OpenAI-compatible API]
    G --> R{Routing / Provider}
    R --> O[OpenAI]
    R --> A[Anthropic]
    R --> L[Other / compatible endpoint]
    G --> E[Embedding endpoint]
```

KIN uses logical model names, such as `openai/gpt-4o-mini`, and does not contain provider-specific SDK code.

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

PostgreSQL and Redis have no host port mapping.

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

The worker/scheduler is intentionally future architecture for v0.1.0. TrueForge itself already supports schedules; KIN will consume that capability rather than building another scheduler when the proactive layer is added.

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
| Current working context | KIN | Redis |
| Goals | KIN | PostgreSQL |
| Semantic memory | KIN | PostgreSQL + pgvector |
| Episodic audit/events | KIN | PostgreSQL |
| Agent sessions/turns | TrueForge | TrueForge PostgreSQL schema |
| Provider routing/config | Bifrost | Bifrost file config in v0.1.0 |

The Compose project uses a single PostgreSQL server with separate databases/users: KIN's `kin` database and TrueForge's `trueforge` database.

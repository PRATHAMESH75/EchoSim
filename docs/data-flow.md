# Data Flow

## Sentiment campaign flow

```mermaid
sequenceDiagram
    participant User
    participant FE as Frontend
    participant Graph as Graph API
    participant Sent as Sentiment API
    participant Task as TaskManager
    participant Run as CampaignManager

    User->>FE: Submit product seed
    FE->>Sent: POST /seed/preview
    Sent-->>FE: markdown + simulation_requirement

    FE->>Graph: POST /ontology/generate
    Graph-->>FE: project_id
    FE->>Graph: POST /build
    Graph->>Task: create graph build task
    Graph-->>FE: task_id

    loop Poll graph task
        FE->>Graph: GET /task/:task_id
        Graph-->>FE: progress + message
    end

    FE->>Sent: POST /campaign/create
    Sent-->>FE: campaign_id
    FE->>Sent: POST /campaign/:id/prepare
    Sent->>Task: create campaign prepare task
    Sent-->>FE: prepare task_id

    loop Poll preparation task
        FE->>Sent: GET /campaign/:id/prepare/status
        Sent-->>FE: progress + message
    end

    FE->>Sent: POST /campaign/:id/start
    Sent->>Run: start parallel scenarios
    FE->>Sent: GET /campaign/:id
    Sent-->>FE: runner status + recent actions

    FE->>Sent: GET /campaign/:id/sentiment
    Sent-->>FE: cached sentiment result
    FE->>Sent: GET /campaign/:id/compare
    Sent-->>FE: cached scenario comparison
```

## Cache invalidation rule

Sentiment analysis is reused until any simulation action log changes in size or modification time. When a log changes, the next request recalculates and replaces the cached analysis entry.

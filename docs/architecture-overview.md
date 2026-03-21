# Architecture Overview

Sentiment Simulator is a product launch workflow that turns a structured brief into a runnable market model.

## System context

```mermaid
flowchart LR
    User[Product team]
    Frontend[Vue frontend]
    Backend[Flask backend]
    LLM[OpenAI-compatible LLM]
    Zep[Zep Cloud]
    OASIS[CAMEL-OASIS runner]

    User --> Frontend
    Frontend --> Backend
    Backend --> LLM
    Backend --> Zep
    Backend --> OASIS
```

## Public product path

```mermaid
flowchart LR
    Seed[Product seed] --> Review[Population review]
    Review --> Prepare[Async preparation task]
    Prepare --> Run[Parallel scenario runner]
    Run --> Dashboard[Sentiment dashboard]
```

## Launch decisions

- Only the sentiment simulator is part of the public frontend surface.
- Campaign preparation is asynchronous and polled through persisted task state.
- Scenario execution is parallel across baseline, competitive, and crisis runs.
- Sentiment analysis is cached and invalidated when simulation action logs change.
- Legacy report and interaction flows remain backend-capable but are not launch-critical UI.

## Architectural risks addressed

- The previous docs described one-after-another campaign execution while the code already ran in parallel.
- The frontend exposed unfinished legacy routes that were not launch-ready.
- Production runtime defaults were still development-oriented.
- Sentiment refreshes recalculated expensive analysis instead of using persisted cache state.

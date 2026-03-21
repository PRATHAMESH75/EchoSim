# API Reference

This document covers the **shipped launch workflow API** for Sentiment Simulator. It focuses on the endpoints used by the current frontend and the backend artifacts they affect.

## Conventions

- Base path for the backend API in local development: `http://localhost:5001`
- Most JSON endpoints return a top-level `success` boolean.
- The frontend Axios client rejects responses where `success` is explicitly `false`.
- Long-running operations use persisted task polling rather than streaming.

## Health

### `GET /health`

Simple backend liveness check.

Response:

```json
{
  "status": "ok",
  "service": "sentiment-simulator-backend"
}
```

## Seed and Launch Modeling

### `POST /api/sentiment/seed/validate`

Validates a structured seed payload before any graph or campaign work begins.

Request body:

```json
{
  "product_name": "Signal Desk",
  "product_category": "B2B SaaS",
  "tagline": "Run launch decisions with evidence",
  "target_market": "Product marketers at software companies",
  "core_features": [
    {
      "name": "Launch monitoring",
      "description": "Tracks market reaction"
    }
  ],
  "pricing_tiers": [
    {
      "name": "Growth",
      "price": "$99",
      "description": "Small teams"
    }
  ]
}
```

Response:

```json
{
  "success": true,
  "valid": true,
  "errors": []
}
```

Validation rules enforced today:

- `product_name`, `product_category`, `tagline`, and `target_market` are required
- at least one `core_feature` is required
- at least one `pricing_tier` is required

### `POST /api/sentiment/seed/preview`

Builds the internal seed derivatives without creating a project.

Purpose:

- preview the markdown that will feed the graph pipeline
- preview the `simulation_requirement` that will feed simulation configuration

Request body:

- same shape as `seed/validate`

Response:

```json
{
  "success": true,
  "markdown": "# Signal Desk\n...",
  "simulation_requirement": "Simulate market sentiment and consumer reactions ..."
}
```

### `GET /api/sentiment/archetypes`

Returns the archetype definitions used by the launch workflow UI.

Response shape:

```json
{
  "success": true,
  "archetypes": [
    {
      "key": "early_adopter",
      "name": "Early Adopter",
      "population_pct": 0.12,
      "risk_tolerance": "high",
      "price_sensitivity": "low",
      "social_influence": "medium",
      "brand_loyalty": "low",
      "decision_trigger": "Tries anything new and innovative immediately after launch",
      "amplification_behavior": "medium",
      "memory_decay": "fast",
      "interests": ["technology", "startups"],
      "sentiment_momentum": 0.3,
      "influence_weight": 0.6,
      "activity_level": 0.8
    }
  ]
}
```

## Graph Pipeline

### `POST /api/graph/ontology/generate`

Creates a project, saves uploaded source material, extracts text, and asks the ontology generator to define graph entity and edge types.

Content type:

- `multipart/form-data`

Form fields:

- `files`: one or more uploaded files
- `simulation_requirement`: required
- `project_name`: optional
- `additional_context`: optional

Response:

```json
{
  "success": true,
  "data": {
    "project_id": "proj_xxx",
    "project_name": "Signal Desk Launch",
    "ontology": {
      "entity_types": [],
      "edge_types": []
    },
    "analysis_summary": "..."
  }
}
```

Primary side effects:

- creates `backend/uploads/projects/<project_id>/project.json`
- writes uploaded files into `backend/uploads/projects/<project_id>/files/`
- writes extracted text into `backend/uploads/projects/<project_id>/extracted_text.txt`

### `POST /api/graph/build`

Starts an asynchronous graph build task using a previously created project.

Request body:

```json
{
  "project_id": "proj_xxx",
  "graph_name": "Signal Desk Graph",
  "chunk_size": 500,
  "chunk_overlap": 50,
  "force": false
}
```

Response:

```json
{
  "success": true,
  "data": {
    "project_id": "proj_xxx",
    "task_id": "task_xxx",
    "message": "Graph build started. Poll /task/{task_id} for progress."
  }
}
```

Primary side effects:

- creates a persisted task in `backend/uploads/tasks/<task_id>.json`
- updates `project.json`
- builds a Zep graph and stores the resulting `graph_id` on the project

### `GET /api/graph/task/<task_id>`

Reads the persisted graph-build task state.

Response:

```json
{
  "success": true,
  "data": {
    "task_id": "task_xxx",
    "task_type": "graph_build",
    "status": "processing",
    "progress": 55,
    "message": "Waiting for Zep to process uploaded chunks"
  }
}
```

### `GET /api/graph/data/<graph_id>`

Returns graph data for visualization after build completion.

Response:

```json
{
  "success": true,
  "data": {
    "nodes": [],
    "edges": [],
    "node_count": 0,
    "edge_count": 0
  }
}
```

### `GET /api/graph/project/<project_id>`

Returns persisted project metadata.

Typical response fields:

- `project_id`
- `name`
- `status`
- `files`
- `ontology`
- `analysis_summary`
- `graph_id`
- `graph_build_task_id`
- `simulation_requirement`

## Campaign Lifecycle

### `POST /api/sentiment/campaign/create`

Creates a campaign and provisions three simulations.

Request body:

```json
{
  "project_id": "proj_xxx",
  "graph_id": "graph_xxx",
  "seed_data": {
    "product_name": "Signal Desk",
    "product_category": "B2B SaaS",
    "tagline": "Run launch decisions with evidence",
    "target_market": "Product marketers at software companies",
    "core_features": [
      { "name": "Launch monitoring", "description": "Tracks market reaction" }
    ],
    "pricing_tiers": [
      { "name": "Growth", "price": "$99", "description": "Small teams" }
    ]
  },
  "competitive_event_type": "price_drop",
  "crisis_event_type": "security_breach",
  "competitive_event_weights": {
    "price_drop": 40,
    "feature_match": 30,
    "comparison_campaign": 30
  },
  "crisis_event_weights": {
    "security_breach": 40,
    "harsh_review": 30,
    "misleading_comparison": 30
  },
  "total_agents": 50,
  "enable_twitter": true,
  "enable_reddit": true
}
```

Response:

```json
{
  "success": true,
  "campaign": {
    "campaign_id": "camp_xxx",
    "project_id": "proj_xxx",
    "graph_id": "graph_xxx",
    "sim_id_a": "sim_xxx",
    "sim_id_b": "sim_xxx",
    "sim_id_c": "sim_xxx",
    "status": "created"
  }
}
```

Primary side effects:

- creates `backend/uploads/campaigns/<campaign_id>/campaign.json`
- creates three simulation directories under `backend/uploads/simulations/`

### `POST /api/sentiment/campaign/<campaign_id>/prepare`

Starts asynchronous campaign preparation for all three scenarios.

Response:

```json
{
  "success": true,
  "campaign": {
    "campaign_id": "camp_xxx",
    "status": "preparing",
    "prepare_task_id": "task_xxx"
  },
  "task": {
    "task_id": "task_xxx",
    "status": "pending",
    "progress": 0
  },
  "task_id": "task_xxx"
}
```

Preparation work includes:

- generating archetype profiles
- generating simulation configuration
- writing `reddit_profiles.json`, `twitter_profiles.csv`, `simulation_config.json`, and `archetype_map.json`

### `GET /api/sentiment/campaign/<campaign_id>/prepare/status`

Reads campaign preparation task state.

Optional query params:

- `task_id`

Response:

```json
{
  "success": true,
  "campaign": {
    "campaign_id": "camp_xxx",
    "status": "preparing",
    "prepare_progress": 65,
    "prepare_message": "Generating profiles"
  },
  "task": {
    "task_id": "task_xxx",
    "status": "processing",
    "progress": 65,
    "message": "Generating profiles"
  }
}
```

### `POST /api/sentiment/campaign/<campaign_id>/start`

Starts all three prepared scenarios in parallel.

Request body:

```json
{
  "platform": "parallel",
  "max_rounds": 20
}
```

`platform` values:

- `parallel`
- `twitter`
- `reddit`

Response:

```json
{
  "success": true,
  "campaign": {
    "campaign_id": "camp_xxx",
    "status": "running"
  }
}
```

### `GET /api/sentiment/campaign/<campaign_id>`

Returns aggregated campaign and scenario runtime state.

Response shape:

```json
{
  "success": true,
  "campaign": {
    "campaign_id": "camp_xxx",
    "status": "running",
    "sim_id_a": "sim_a",
    "sim_id_b": "sim_b",
    "sim_id_c": "sim_c",
    "scenario_b_inject_round": 7,
    "scenario_c_inject_round": 14,
    "scenario_b_injected": false,
    "scenario_c_injected": false
  },
  "scenario_a": {
    "runner_status": "running",
    "current_round": 4,
    "total_rounds": 20,
    "recent_actions": []
  },
  "scenario_b": {
    "runner_status": "running",
    "current_round": 4,
    "total_rounds": 20,
    "recent_actions": []
  },
  "scenario_c": {
    "runner_status": "running",
    "current_round": 4,
    "total_rounds": 20,
    "recent_actions": []
  }
}
```

This is the primary polling endpoint for the scenario runner view.

### `GET /api/sentiment/campaign`

Lists campaigns currently persisted on disk.

Response:

```json
{
  "success": true,
  "campaigns": []
}
```

### `POST /api/sentiment/campaign/<campaign_id>/inject`

Injects a manual event into Scenario B or C while a campaign is running.

Request body:

```json
{
  "scenario": "b",
  "event_type": "price_drop",
  "custom_prompt": "A major competitor just announced a 50% discount.",
  "timeout": 60.0
}
```

Notes:

- `scenario` must be `b` or `c`
- `custom_prompt` overrides `event_type`
- used by the manual injection panel in the current frontend

Response:

```json
{
  "success": true,
  "result": {
    "status": "ok"
  }
}
```

## Sentiment Analysis

### `GET /api/sentiment/campaign/<campaign_id>/sentiment`

Runs or reuses sentiment analysis for all three scenarios.

Optional query params:

- `advocate_threshold`
- `detractor_threshold`
- `percentile_factions`

Response:

```json
{
  "success": true,
  "campaign_id": "camp_xxx",
  "scenario_a": {
    "simulation_id": "sim_a",
    "total_posts_analyzed": 42,
    "overall": {
      "avg_score": 0.24,
      "weighted_avg_score": 0.31,
      "nps_score": 18.0,
      "positive": 22,
      "negative": 8,
      "neutral": 12
    },
    "timeline": [],
    "factions": {},
    "top_objections": [],
    "persona_heatmap": {}
  },
  "scenario_b": {},
  "scenario_c": {},
  "event_markers": {
    "scenario_b_inject_round": 7,
    "scenario_c_inject_round": 14,
    "competitive_event_type": "price_drop",
    "crisis_event_type": "security_breach"
  }
}
```

Primary cache file:

- `backend/uploads/simulations/<simulation_id>/sentiment_cache.json`

### `GET /api/sentiment/campaign/<campaign_id>/compare`

Returns a unified round axis and per-scenario average scores for overlay comparison charts.

Response:

```json
{
  "success": true,
  "comparison": {
    "rounds": [1, 2, 3],
    "scenario_a": [0.1, 0.2, 0.3],
    "scenario_b": [0.1, 0.0, -0.2],
    "scenario_c": [0.1, -0.1, -0.4],
    "details": {
      "a": {
        "overall": { "avg_score": 0.3 },
        "factions": { "advocates_pct": 60.0, "detractors_pct": 15.0 }
      }
    }
  }
}
```

### `GET /api/sentiment/sim/<simulation_id>/live`

Returns live or partial sentiment analysis for a single simulation.

This route exists in the backend API and can be useful for debugging or future UI work, but it is not the main dashboard route in the current launch flow.

Response:

```json
{
  "success": true,
  "sentiment": {
    "simulation_id": "sim_xxx",
    "overall": {},
    "timeline": []
  }
}
```

## Launch Scope vs Legacy Scope

These routes are in active launch use:

- `/health`
- `/api/sentiment/seed/*`
- `/api/sentiment/archetypes`
- `/api/graph/ontology/generate`
- `/api/graph/build`
- `/api/graph/task/<task_id>`
- `/api/graph/data/<graph_id>`
- `/api/sentiment/campaign/*`
- `/api/sentiment/sim/<simulation_id>/live`

There is also a broader `simulation` blueprint in the backend for older simulation-management flows. It is useful for debugging and internal work, but it is not the primary public workflow in the shipped frontend.

## Error Handling Notes

- Validation failures generally return `400`
- missing projects or campaigns generally return `404`
- missing runtime configuration such as `ZEP_API_KEY` generally returns `500`
- long-running tasks do not stream progress; poll the relevant task endpoint

## Polling Guidance

Current frontend behavior:

- graph build polling interval: `5s`
- campaign preparation polling interval: `2.5s`
- campaign run-state polling interval: `8s`

If you build new clients, follow the same model unless you also change backend task semantics.

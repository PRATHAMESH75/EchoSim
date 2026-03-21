# Runbook

This runbook is for engineers operating, debugging, or extending the shipped Sentiment Simulator workflow locally.

## 1. What this runbook covers

This document assumes you are working on the current launch path:

1. product seed
2. graph build
3. campaign creation
4. asynchronous preparation
5. parallel scenario execution
6. sentiment dashboard

It focuses on:

- local setup
- required environment variables
- how to start the stack
- how to verify each stage
- where runtime artifacts live
- how to debug failures quickly

## 2. Prerequisites

Required versions from the repo:

- Node.js `18+`
- Python `3.11+`
- `uv`

Useful checks:

```bash
node -v
python --version
uv --version
```

## 3. Environment configuration

Create `.env` in the project root and set at least:

```bash
SECRET_KEY=replace-me
LLM_API_KEY=replace-me
ZEP_API_KEY=replace-me
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini
FRONTEND_ORIGIN=http://localhost:3000
CORS_ORIGINS=http://localhost:3000
VITE_API_BASE_URL=http://localhost:5001
```

Important runtime behavior:

- `backend/run.py` validates `SECRET_KEY`, `LLM_API_KEY`, and `ZEP_API_KEY` before startup
- if any are missing, the backend exits immediately
- `FLASK_DEBUG` defaults to `false`
- `SERVE_FRONTEND` defaults to `true`

Useful optional variables:

```bash
FLASK_DEBUG=true
FLASK_HOST=0.0.0.0
FLASK_PORT=5001
LOG_REQUEST_BODIES=true
SENTIMENT_DEFAULT_TOTAL_AGENTS=50
SENTIMENT_DEFAULT_MAX_ROUNDS=20
SENTIMENT_SCENARIO_B_INJECT_ROUND=7
SENTIMENT_SCENARIO_C_INJECT_ROUND=14
```

## 4. Install dependencies

From the repo root:

```bash
npm install
npm install --prefix frontend
cd backend && uv sync --frozen
```

Equivalent repo scripts:

```bash
npm run setup
npm run setup:backend
```

## 5. Start the stack

### Recommended dev command

From the repo root:

```bash
npm run dev
```

This starts:

- backend on `http://localhost:5001`
- frontend on `http://localhost:3000`

### Start services separately

Backend:

```bash
npm run backend
```

Frontend:

```bash
npm run frontend
```

### Production-style Docker run

```bash
docker compose up --build
```

This builds the frontend once and serves the app through the backend container on port `5001`.

## 6. First checks after startup

### Backend health

```bash
curl http://localhost:5001/health
```

Expected:

```json
{"status":"ok","service":"sentiment-simulator-backend"}
```

### Frontend

Open:

- `http://localhost:3000` during local split frontend/backend development
- `http://localhost:5001` when using the container or backend-served frontend

### Confirm API base URL

In frontend dev mode, `VITE_API_BASE_URL` should point at the backend:

- `http://localhost:5001`

If it is empty or wrong, the UI will load but API calls will fail or hit the wrong origin.

## 7. Normal operator flow to verify

Use this order when checking whether the product is working.

### A. Seed preview works

Expected behavior:

- the form submits
- preview generation succeeds
- no validation errors for required fields

Relevant endpoints:

- `POST /api/sentiment/seed/validate`
- `POST /api/sentiment/seed/preview`

### B. Ontology generation works

Expected behavior:

- a project is created
- uploaded file is saved
- ontology and analysis summary are returned

Artifacts to inspect:

- `backend/uploads/projects/<project_id>/project.json`
- `backend/uploads/projects/<project_id>/extracted_text.txt`

### C. Graph build works

Expected behavior:

- graph build task starts
- polling progresses from pending to processing to completed
- graph preview renders

Artifacts to inspect:

- `backend/uploads/tasks/<task_id>.json`
- `project.json` contains `graph_id`

### D. Campaign creation and preparation work

Expected behavior:

- campaign is created with `sim_id_a`, `sim_id_b`, `sim_id_c`
- prepare endpoint creates a task
- status polling reaches `completed`

Artifacts to inspect:

- `backend/uploads/campaigns/<campaign_id>/campaign.json`
- `backend/uploads/simulations/<simulation_id>/state.json`
- `backend/uploads/simulations/<simulation_id>/simulation_config.json`
- `backend/uploads/simulations/<simulation_id>/archetype_map.json`

### E. Scenario execution works

Expected behavior:

- campaign status becomes `running`
- each scenario gains a `run_state.json`
- action logs appear under `twitter/` and `reddit/`

Artifacts to inspect:

- `backend/uploads/simulations/<simulation_id>/run_state.json`
- `backend/uploads/simulations/<simulation_id>/simulation.log`
- `backend/uploads/simulations/<simulation_id>/twitter/actions.jsonl`
- `backend/uploads/simulations/<simulation_id>/reddit/actions.jsonl`

### F. Sentiment analysis works

Expected behavior:

- dashboard loads scenario analytics
- comparison view returns a unified round axis
- a sentiment cache file is written

Artifacts to inspect:

- `backend/uploads/simulations/<simulation_id>/sentiment_cache.json`

## 8. File-system map

The fastest way to debug this product is to know where state lives.

```text
backend/uploads/
  campaigns/
    camp_xxx/
      campaign.json
  projects/
    proj_xxx/
      files/
      extracted_text.txt
      project.json
  simulations/
    sim_xxx/
      state.json
      run_state.json
      simulation_config.json
      reddit_profiles.json
      twitter_profiles.csv
      archetype_map.json
      sentiment_cache.json
      simulation.log
      twitter/
        actions.jsonl
      reddit/
        actions.jsonl
  tasks/
    task_xxx.json
```

## 9. Most useful runtime files

### `project.json`

Use when debugging:

- project lifecycle
- ontology generation
- graph build linkage

### `task_xxx.json`

Use when debugging:

- graph build progress
- campaign preparation progress

### `campaign.json`

Use when debugging:

- scenario IDs
- campaign lifecycle status
- injection scheduling
- preparation progress

### `state.json`

Use when debugging:

- whether a simulation was prepared successfully
- whether profiles and config generation completed

### `run_state.json`

Use when debugging:

- current round
- runner status
- recent actions
- process state

### `simulation.log`

Use when debugging:

- subprocess startup failure
- OASIS runtime issues
- crashes not clearly visible in the frontend

### `actions.jsonl`

Use when debugging:

- whether agents are producing output
- whether event injections happened
- whether sentiment analysis has content to classify

### `sentiment_cache.json`

Use when debugging:

- cache hits
- stale analytics
- whether analysis output was persisted

## 10. Quick failure triage

### Backend does not start

Check:

- missing `SECRET_KEY`
- missing `LLM_API_KEY`
- missing `ZEP_API_KEY`

The backend entrypoint validates these before launching Flask.

### Frontend loads but API requests fail

Check:

- `VITE_API_BASE_URL`
- backend is actually running on `5001`
- `CORS_ORIGINS` and `FRONTEND_ORIGIN`

### Graph build never completes

Check:

- `backend/uploads/tasks/<task_id>.json`
- backend logs for Zep API failures
- whether `ZEP_API_KEY` is valid
- whether the project has extracted text and ontology saved correctly

### Campaign preparation fails

Check:

- `campaign.json`
- corresponding preparation task JSON
- `state.json` for each `sim_id_*`
- backend logs for LLM or config-generation failures

### Campaign starts but no scenario progresses

Check:

- `simulation_config.json` exists
- `run_state.json` exists
- `simulation.log` for subprocess errors
- whether `twitter/actions.jsonl` or `reddit/actions.jsonl` are being created

### Dashboard loads but shows no sentiment data

Check:

- whether there are any action logs at all
- whether posts were created instead of only non-content actions
- `sentiment_cache.json`
- backend logs for sentiment classification failures

## 11. Debugging order

When something breaks, use this order:

1. Check the browser network request that failed.
2. Check the matching persisted JSON or log file under `backend/uploads/`.
3. Check backend console output.
4. Check the owning service class.
5. Only then start changing prompts, thresholds, or models.

This order matters because many failures are orchestration or file-state issues, not model-quality issues.

## 12. Useful checks with `curl`

### Health

```bash
curl http://localhost:5001/health
```

### Validate a seed

```bash
curl -X POST http://localhost:5001/api/sentiment/seed/validate \
  -H 'Content-Type: application/json' \
  -d '{
    "product_name":"Signal Desk",
    "product_category":"B2B SaaS",
    "tagline":"Run launch decisions with evidence",
    "target_market":"Product marketers",
    "core_features":[{"name":"Launch monitoring","description":"Tracks reactions"}],
    "pricing_tiers":[{"name":"Growth","price":"$99","description":"Small teams"}]
  }'
```

### Poll a graph task

```bash
curl http://localhost:5001/api/graph/task/<task_id>
```

### Poll campaign status

```bash
curl http://localhost:5001/api/sentiment/campaign/<campaign_id>
```

### Fetch campaign sentiment

```bash
curl http://localhost:5001/api/sentiment/campaign/<campaign_id>/sentiment
```

## 13. Running tests

Backend tests:

```bash
backend/.venv/bin/python -m pytest -q backend/tests
```

What the current test suite is most useful for:

- launch sentiment routes
- task manager behavior
- sentiment cache behavior

It is not a full end-to-end simulation reliability suite.

## 14. Data cleanup during local work

This system persists state aggressively. Old runs can confuse debugging if you forget they exist.

Common places to inspect or clean manually:

- `backend/uploads/projects/`
- `backend/uploads/tasks/`
- `backend/uploads/campaigns/`
- `backend/uploads/simulations/`

Be careful when deleting persisted state if you are sharing the workspace with someone else or comparing runs.

## 15. Notes on launch-specific architecture

The current shipped path has a few important constraints:

- campaign preparation is asynchronous
- scenario execution is parallel
- launch population generation is archetype-based
- sentiment analysis is cached
- the public frontend is narrowed to the sentiment workflow

If your debugging assumptions conflict with any of those, update the assumption first.

## 16. When to inspect which service

Inspect [`backend/app/services/seed_template_processor.py`](../backend/app/services/seed_template_processor.py) when:

- seed validation is wrong
- preview text is poor
- downstream prompt context is incomplete

Inspect [`backend/app/services/campaign_manager.py`](../backend/app/services/campaign_manager.py) when:

- preparation status looks wrong
- scenarios do not start together
- injection timing is wrong
- campaign status aggregation is wrong

Inspect [`backend/app/services/simulation_manager.py`](../backend/app/services/simulation_manager.py) when:

- profile files are missing
- config files are malformed
- simulation preparation fails before runtime

Inspect [`backend/app/services/simulation_runner.py`](../backend/app/services/simulation_runner.py) when:

- subprocesses never start
- runs stall
- action logs are not parsed
- run-state polling is wrong

Inspect [`backend/app/services/sentiment_analyzer.py`](../backend/app/services/sentiment_analyzer.py) when:

- sentiment scores are missing or stale
- objections or topics look wrong
- cache invalidation seems broken

## 17. Fastest path to confidence

If you want to sanity-check the whole stack quickly:

1. start backend and frontend
2. confirm `/health`
3. submit a minimal valid seed
4. confirm graph build task completion
5. confirm campaign preparation completion
6. confirm `simulation.log` and `actions.jsonl` are being written
7. confirm the dashboard writes `sentiment_cache.json`

If all seven happen, the launch workflow is functioning end to end.

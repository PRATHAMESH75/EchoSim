# Sentiment Simulator

Sentiment Simulator is a launch-focused product workflow for product teams that want to pressure-test messaging, pricing, and market risk before shipping.

## What it does

- Converts a structured product brief into a knowledge graph.
- Expands the audience into archetype-driven consumer segments.
- Runs three scenarios in parallel: baseline, competitive pressure, and crisis response.
- Compares sentiment movement, objections, faction shifts, and archetype heatmaps in one dashboard.

## Public scope

This repository now ships a single public frontend workflow:

1. Product seed
2. Population review
3. Scenario runner
4. Sentiment dashboard

Legacy graph, simulation, and report capabilities remain backend-capable, but they are not part of the launch frontend surface.

## Architecture notes

- Campaign execution is parallel, and the documentation and UI copy now match that behavior.
- Campaign preparation is asynchronous and exposed as a tracked task with polling.
- Sentiment analysis is cached per simulation output and invalidated when action logs change.
- Production defaults are locked down: `SECRET_KEY` is required, `FLASK_DEBUG` defaults to `false`, and CORS is origin-based.
- The report/chat stack is treated as non-launch scope for the public UI.

## Local development

### Prerequisites

- Node.js 18+
- Python 3.11+

### Environment

Copy `.env.example` to `.env` and fill in the required values:

```bash
cp .env.example .env
```

Required keys:

```bash
SECRET_KEY=        # generate: python -c "import secrets; print(secrets.token_hex(32))"
LLM_API_KEY=       # OpenAI-compatible API key
ZEP_API_KEY=       # Zep Cloud key — free tier: https://app.getzep.com/
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini
```

For local development (separate frontend/backend processes), also add:

```bash
FRONTEND_ORIGIN=http://localhost:3000
CORS_ORIGINS=http://localhost:3000
VITE_API_BASE_URL=http://localhost:5001
```

### Install

```bash
# Frontend dependencies
npm run setup

# Backend dependencies (Python 3.11+, standard pip)
pip install -r backend/requirements.txt
```

### Run

```bash
npm run dev
```

Services:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:5001`

## Production build

```bash
npm run build
```

Then start the backend; it serves the compiled frontend from the same process:

```bash
cd backend && python run.py
```

## Docker

Build and run the production image:

```bash
docker compose up --build
```

The container builds the frontend once, serves the compiled app from the backend process, and exposes a single public port on `5001` by default.

## Repository guides

- [AI Engineer Guide](./docs/ai-engineer-guide.md)
- [API Reference](./docs/api-reference.md)
- [Product Executive Summary](./docs/product-executive-summary.md)
- [Product Overview](./docs/product-overview.md)
- [Architecture Overview](./docs/architecture-overview.md)
- [Frontend Architecture](./docs/frontend-architecture.md)
- [Backend Architecture](./docs/backend-architecture.md)
- [Data Flow](./docs/data-flow.md)
- [Runbook](./docs/runbook.md)
- [Sentiment Simulator](./docs/sentiment-simulator.md)

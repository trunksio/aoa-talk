# Agent Oriented Architecture (AOA) Demo Stack

This repository demonstrates the AOA intent → discovery → plan → execute pipeline.

## Stack
- **Registry**: Postgres + pgvector + Apache AGE (graph memory + semantic discovery)
- **Planner**: FastAPI service compiling intents into agent DAGs
- **Orchestrator**: executes plans across Agentic Units
- **Frontend**: Intent Studio (React)
- **Agents**: Self-registering AUs with manifest-based capability contracts

Run locally:
```bash
docker compose up --build


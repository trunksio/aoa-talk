#!/usr/bin/env bash
# -------------------------------------------------------------------
# Script: create_aoa_issues.sh
# Purpose: Automatically create the next 5 issues for AOA-Talk project
# Requires: GitHub CLI (https://cli.github.com/), authenticated with `gh auth login`
# -------------------------------------------------------------------

REPO="trunksio/aoa-talk"

echo "🚀 Creating AOA-Talk project issues in $REPO ..."
echo

# -------------------------------------------------------------------
# 2. Registry MVP
# -------------------------------------------------------------------
gh issue create --repo "$REPO" \
  --title "Implement AOA Registry Service (Discovery Layer MVP)" \
  --body "$(cat <<'EOF'
### Description
Implement the foundational **backend/registry** FastAPI service for registering and discovering Agentic Units (AUs) and their capabilities.  
This forms the semantic and graph-based memory of the AOA pipeline.

### Tasks
- Create models: `Agent`, `Capability`, `Embedding` (Pydantic + SQLAlchemy)
- Implement `/register` endpoint: accepts AU manifest (`id`, `capabilities`, `embedding`)
- Implement `/search` endpoint: semantic + graph search using **pgvector** + **Apache AGE**
- Set up Postgres migrations (Alembic)
- Add Docker connection config for Postgres + AGE
- Add minimal unit tests for register/search round-trip

### Acceptance Criteria
- Running `uvicorn backend.registry.main:app` exposes working `/register` and `/search`
- Manifest registration and retrieval verified via pytest
- CI passes with no dependency conflicts
EOF
)"

# -------------------------------------------------------------------
# 3. Capability Manifest & Self-Registration
# -------------------------------------------------------------------
gh issue create --repo "$REPO" \
  --title "Add AU Capability Manifest & Self-Registration Logic" \
  --body "$(cat <<'EOF'
### Description
Each Agentic Unit (AU) should declare its capabilities via a manifest and self-register with the Registry service on startup.

### Tasks
- Add `agents/common/manifest.py` (Pydantic models for `AgentManifest`, `Capability`)
- Create sample `manifest.yaml` in one agent (e.g., OCR or Parser)
- Implement `register_on_start.py`: reads manifest and POSTs it to `/registry/register`
- Add unit test mocking the Registry service
- Update agent Dockerfiles to call `register_on_start.py` on boot

### Acceptance Criteria
- On agent startup, manifest auto-registers with Registry
- Example manifest round-trip verified
- Tests confirm manifest structure and registration behavior
EOF
)"

# -------------------------------------------------------------------
# 4. Planner MVP
# -------------------------------------------------------------------
gh issue create --repo "$REPO" \
  --title "Implement Planner Service (Intent to Plan Conversion)" \
  --body "$(cat <<'EOF'
### Description
Build a Planner service that converts natural-language intents into abstract plans (capability DAGs) and maps them to concrete AUs via Registry lookups.

### Tasks
- Add `backend/planner/intent_parser.py` for extracting task type, entities, constraints from intent text
- Add `backend/planner/plan_builder.py` to construct abstract DAG of required capabilities
- Add `/plan/abstract` and `/plan/concrete` endpoints in `planner/main.py`
- Integrate with Registry `/search` for capability resolution
- Write minimal tests verifying plan output structure

### Acceptance Criteria
- POST to `/plan/abstract` returns structured JSON plan
- POST to `/plan/concrete` maps abstract steps to registered AUs
- Planner runs via Docker Compose
- Tests validate output schema and Registry integration
EOF
)"

# -------------------------------------------------------------------
# 5. Orchestrator MVP
# -------------------------------------------------------------------
gh issue create --repo "$REPO" \
  --title "Implement Orchestrator Service (Plan Execution Engine)" \
  --body "$(cat <<'EOF'
### Description
Develop the Orchestrator service to execute DAGs produced by the Planner using Redis RQ, track run states, and stream outputs.

### Tasks
- Add Redis queue worker container to Docker Compose
- Create `backend/orchestrator/executor.py` (enqueue DAG nodes, monitor execution, handle retries/timeouts)
- Add `/execute` endpoint to accept plan JSON
- Add `/runs/{id}` endpoint to query status/results
- Simulate agent calls using mock REST endpoints
- Add unit test covering one mock plan execution

### Acceptance Criteria
- `/execute` accepts valid DAG and runs asynchronously
- Run status retrievable via `/runs/{id}`
- Redis queue functional in Docker Compose
- CI passes without hanging jobs
EOF
)"

# -------------------------------------------------------------------
# 6. Intent Studio UI
# -------------------------------------------------------------------
gh issue create --repo "$REPO" \
  --title "Build Minimal Intent Studio UI (React Frontend)" \
  --body "$(cat <<'EOF'
### Description
Create a simple React-based UI for capturing user intents, sending them to the Planner, and displaying the resulting plan graphically.

### Tasks
- Add `frontend/intent-studio/src/pages/IntentStudio.tsx`
- Implement:
  - Text input for user intent
  - “Generate Plan” button → calls `/planner/plan/abstract`
  - Visual DAG graph (React Flow)
- Display returned plan nodes + edges with minimal styling
- Add npm build step to CI

### Acceptance Criteria
- Running frontend shows working input → plan visualization
- Planner connection verified
- CI builds successfully with lint pass
EOF
)"

echo
echo "✅ All AOA-Talk issues have been created successfully!"

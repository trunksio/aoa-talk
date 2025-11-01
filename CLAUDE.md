# 🤖 Agent Oriented Architecture (AOA) — Claude Code Context

## Overview
This repository (`aoa-labs`) implements the **Agent Oriented Architecture (AOA)** — a modular AI framework built from **Agentic Units (AUs)**.  
Each AU is a self-contained microservice with its own model, manifest, and task queue, able to discover, collaborate, and adapt.

The goal is to demonstrate a *reusable, scalable reference implementation* of AOA suitable for real-world deployment.

---

## 🧱 Core Design Principles

1. **Agentic Units (AUs):**
   - Each AU encapsulates a focused capability (e.g., OCR, Parsing, Evaluation).
   - AU metadata (capabilities, queue name, model type) is registered in the **Registry**.

2. **Planner → Orchestrator → Registry Loop:**
   - **Planner:** Translates user intent → DAG of AU types.
   - **Registry:** Discovers concrete AUs matching those capabilities.
   - **Orchestrator:** Executes the DAG and reports results.

3. **Memory as a System Property:**
   - Planner DAGs = *Episodic memory* (what solved what)
   - Registry embeddings = *Semantic memory* (capability space)
   - Orchestrator logs = *Working memory* (execution context)

4. **Right-Sized Intelligence:**
   - Prefer local models over API calls for cost and autonomy.
   - **Default model:** `gpt-oss:20b`
   - **OCR AU:** `DeepSeek-OCR` (specialized visual model)
   - Future fine-tuning pipeline via local LoRA adapters.

---

## 🧠 Tech Stack & Implementation Choices

| Component | Technology | Purpose |
|------------|-------------|----------|
| **Registry** | FastAPI + Postgres + pgvector | AU discovery via embeddings |
| **Planner** | Python + local LLM (`gpt-oss:20b`) | Intent → Plan translation |
| **Orchestrator** | Redis + RQ + async queueing | AU coordination |
| **Memory Layer** | Postgres + Apache AGE | DAG + embedding persistence |
| **UI Layer (Intent Studio)** | React + FastAPI backend | Human-AI interface |
| **Infrastructure** | Docker + Compose (GPU enabled) | Portable local demo |
| **Testing** | Pytest + Integration tests (DGX Spark) | End-to-end validation |

---

## 🚀 Delivery Workflow

| Stage | Description | Tools |
|--------|--------------|-------|
| **Design** | Conceptual + architectural design by Lewis & ChatGPT | ChatGPT GPT-5 |
| **Implementation** | Incremental delivery via Claude Code (Web + GitHub) | Claude Code |
| **Integration Testing** | DGX Spark box (Lewis) — GPU accelerated containers | Pytest / Docker |
| **Review & Merge** | Human + AI review (Lewis + ChatGPT) | PR + gh workflow |

---

## 🔁 Development Phases

| Phase | Focus | Validation |
|--------|--------|------------|
| 1 | AU containers (OCR, Parser, Evaluator, Reporter) | Unit tests |
| 2 | Registry embeddings + semantic search | Integration tests |
| 3 | Planner + DAG persistence (AOA-026) | Graph memory replay |
| 4 | Orchestrator adaptive routing | Stress + failure recovery |
| 5 | Intent Studio (React UI) | Human-in-the-loop demonstration |

---

## ✅ Testing & Benchmarking
All changes must:
1. Pass `pytest` + integration tests.
2. Execute successfully on DGX Spark (NVIDIA CUDA 13).
3. Be benchmarked for speed and correctness vs. previous commit.

---

## 🤝 Collaboration Model
- **ChatGPT (GPT-5):** Architecture design, issue creation, PR review, roadmap curation.
- **Claude Code (Web + GitHub):** Implementation, refactor, test automation.
- **Lewis (Human):** Integration testing, DGX hardware validation, final review.

This repository demonstrates not only **AOA in practice**, but also **collaborative AI engineering** — where distinct models act as specialized AUs themselves.

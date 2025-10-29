# Claude Code Web Task Template for AOA-Talk

This document defines the standardized prompt template for using **Claude Code Web** to implement issues in the `aoa-talk` repository.

---

## 🧠 Template: "Claude Code Web Issue Implementation Prompt"

```
You are acting as the implementation engineer for the AOA-Talk repository.

Task:
Pick up GitHub issue #<ISSUE_NUMBER> from the public repo https://github.com/trunksio/aoa-talk.
Read the issue description carefully and implement everything specified.

Development environment:
- The repo follows the Agent Oriented Architecture (AOA) pattern.
- Backend services (registry, planner, orchestrator) are FastAPI microservices.
- Persistence: Postgres + pgvector + Apache AGE.
- CI/CD: GitHub Actions workflow already exists (.github/workflows/lint-and-test.yml).
- Python 3.11, Docker-based local execution.
- All code must pass lint, black, and pytest checks.

Workflow you must follow:
1. **Sync the latest main branch** from GitHub.
2. **Create a new branch** named:
   `claude/issue-<ISSUE_NUMBER>-<short-description>`
   Example: `claude/issue-3-manifest-selfreg`
3. Implement the solution described in the issue.
   - Keep changes isolated to relevant folders (backend, agents, or frontend).
   - Use consistent docstrings and type hints.
   - Add or update unit tests where relevant.
   - Do not commit large model binaries or datasets.
4. Run local tests and lint checks:
   ```bash
   black --check .
   flake8 .
   pytest --maxfail=1 --disable-warnings -q
   ```
   Ensure everything passes.
5. **Commit and push** all changes to the new branch with a descriptive commit message:
   `"Implements issue #<ISSUE_NUMBER>: <short summary>"`
6. When complete, post a summary back to the chat including:
   - ✅ Confirmation of branch name and push success  
   - 🔍 List of major changes and new files  
   - 🧪 Note on tests passing locally  
   - 📝 A short recommended PR title and description  
   - A link to create the PR manually, e.g.:
     `https://github.com/trunksio/aoa-talk/pull/new/<branch-name>`

Rules:
- Never push directly to `main`.
- Never install or run untrusted dependencies.
- Keep responses concise and structured.
- If an issue requires multiple services, scaffold minimal stubs and note what to fill later.

Once pushed, I (the user) will open the PR manually and ChatGPT will perform the code review.
```

---

## 🔖 Notes

- Claude Code Web should be used only for implementation tasks that involve code creation or refactoring.
- ChatGPT (Codex Connector) remains responsible for architecture review and validation.
- Each Claude-generated branch must be reviewed and merged following the **AOA Dev Loop** process.

---

**Filename suggestion:** `CLAUDE_TASK_TEMPLATE.md`

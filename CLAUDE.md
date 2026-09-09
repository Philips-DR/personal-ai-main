
# Personal AI Assistant — Development Guidelines

## Project Overview

An agentic AI assistant built by the AyaData AI Solutions team. Hybrid architecture: Python (FastAPI) backend + TypeScript (Next.js) frontend. Claude via AWS Bedrock for AI, Supabase for persistence, pgvector for RAG memory.

## Architecture Principles

### Modular Component-Based Architecture

Modules are independent components handling specific tasks (email, meeting, tasks, etc.) that can be swapped or updated without affecting the rest of the system. Every module implements the `ModuleHandler` abstract base class defined in `backend/app/modules/base.py`.

- Modules **never** import or call each other directly
- Inter-module communication happens exclusively through the orchestrator via `follow_up_intents`
- New modules are registered in the module router — no other files need to change
- External service integrations use abstract provider interfaces (e.g., `TranscriptionProvider`) with factory functions for swappability

### Single Responsibility Principle

Each module has one clear, focused goal:
- **Orchestrator**: Intent classification and routing — never business logic
- **Email Module**: Gmail lifecycle — never task management
- **Meeting Module**: Transcript processing — never email operations
- **Task Module**: Task CRUD and reminders — never meeting processing
- **Morning Brief**: Aggregation and formatting — never data mutation
- **GitHub Docs**: Repository analysis and doc generation — never persistence

Each file within a module should have a single responsibility. Prefer many small, focused files over large monolithic ones.

### Independent Modules

- Modules are stateless between requests — all state lives in Supabase
- Modules declare their supported intents and the orchestrator routes to them
- Modules can be developed, tested, and deployed independently
- Adding a new module requires: (1) implement `ModuleHandler`, (2) register in router — nothing else

## Security

### Secrets Management
- **NEVER** hardcode API keys, tokens, passwords, or connection strings in source code
- All secrets live in `.env.local` (gitignored) and are loaded via `pydantic-settings`
- `.env.example` documents every required variable with placeholder values
- OAuth tokens are stored encrypted in Supabase, never in plain text or local files

### Authentication
- Gmail integration uses OAuth 2.0 with minimal required scopes
- OAuth tokens are refreshed automatically before expiry
- GitHub tokens are scoped to read-only access
- All external API calls use token-scoped clients, never raw credentials

### Review Gates (Human-in-the-Loop)
- **No autonomous email sending** — all drafts require explicit user approval before send
- Critical actions surface `PendingAction` objects in the module response for user confirmation
- The review gate is enforced at the code level in the Gmail client, not just the UI
- Audit log captures both the proposed action and the user's approval/rejection

### Data Protection
- No PII in logs — use structured logging with sanitized fields
- Audit log is append-only (no UPDATE/DELETE operations)
- File uploads (meeting audio) are processed and not retained beyond the session unless explicitly saved

## Single Source of Truth (SSOT)

- **Data models**: Pydantic models in `backend/app/models/` are the SSOT for all data shapes
- **Database schema**: Alembic migrations are the SSOT for database structure
- **Configuration**: `backend/app/config.py` (pydantic-settings) is the SSOT for all runtime configuration
- **Intent definitions**: The `Intent` enum in `backend/app/models/orchestrator.py` is the SSOT for all supported intents
- **Frontend types**: `frontend/app/lib/types.ts` mirrors backend Pydantic models — generate from OpenAPI schema when possible, never maintain separately
- Never duplicate constants, enums, or type definitions across files. Import from the canonical source.

## No Hardcoding

- All external URLs, API endpoints, and service configurations come from environment variables
- Default values for user-facing settings (brief time, timezone) live in `config.py`, not scattered in module code
- Magic numbers and strings are defined as named constants in the relevant model or config file
- Cron schedules, retry counts, timeout values, and token budgets are configurable via env vars with sensible defaults

## Scalability

- All FastAPI route handlers and module methods are `async`
- Database connections use async clients with connection pooling
- Long-running operations (transcription, large repo analysis) use background tasks with status polling
- Large documents and transcripts are processed in chunks to stay within context window limits
- Embedding generation is batched where possible
- The module registry pattern allows horizontal scaling — modules can be extracted to separate services without changing the orchestrator interface

## Performance

- Cache frequently accessed data: email thread metadata, project/contact lists, recent memory entries
- Batch Supabase operations where possible (bulk inserts for action items, batch embedding storage)
- Set token budgets for Claude calls — don't send unbounded context
- Use RAG retrieval (top-k similarity search) instead of loading all memory into prompts
- Gmail polling uses incremental sync (history ID) rather than full inbox scans
- GitHub repo analysis fetches only the file tree first, then selectively downloads key files

## Clean Codebase

### Code Style
- Python: type hints on all function signatures, follow PEP 8, use `ruff` for linting and formatting
- TypeScript: strict mode enabled, no `any` types, use ESLint + Prettier
- Prefer explicit over implicit — no `**kwargs` passthrough unless truly needed
- Use descriptive variable names — avoid abbreviations except universally understood ones (id, url, db)

### Error Handling
- Use custom exception classes defined in `backend/app/models/` — never raise bare `Exception`
- FastAPI exception handlers convert domain errors to appropriate HTTP responses
- External API calls (Gmail, AssemblyAI, GitHub) wrap errors with context about what operation failed
- Never swallow exceptions silently — log and re-raise or handle explicitly

### Logging
- Use structured logging (JSON format in production) with consistent fields: module, action, duration
- Log at appropriate levels: ERROR for failures, WARNING for degraded states, INFO for key actions, DEBUG for development
- Every module action should produce at least one INFO log entry
- Never log sensitive data (tokens, email content, PII)

### Imports & Dependencies
- Group imports: stdlib, third-party, local — separated by blank lines
- No circular imports — if two modules need shared types, they import from `models/`
- Pin all dependency versions in `pyproject.toml` and `package.json`

## Reliability & Evaluation

### Testing
- **Unit tests**: Every module handler, parser, and utility function has pytest tests
- **Integration tests**: End-to-end orchestrator flows with mocked external services
- **Fixture-based**: Use pytest fixtures for Supabase test data, mock Claude responses, sample emails/transcripts
- Tests run in CI before merge — no exceptions

### Human-in-the-Loop (HITL) Checkpoints
- Email sends require explicit approval
- Meeting action items are presented for review before task creation
- Morning brief can be regenerated on request
- GitHub docs are previewed before export

### Validation
- Pydantic models validate all data at system boundaries (API input, external service responses)
- Claude outputs use structured output schemas (tool_use) to enforce response format
- Action items include source quotes so users can verify against the original transcript

## Observability & Monitoring

### Audit Log
- Every orchestrator action is logged: intent, module, input summary, output summary, duration, errors
- The audit log is the system's runtime diary — treat it as critical infrastructure
- Query patterns: "what did the assistant do today?", "why was this email drafted?", "when was this task created?"

### AgentOps Principles
- Monitor intent classification accuracy — log confidence scores, flag low-confidence routing
- Track module execution time — identify slow modules and API calls
- Log token usage per request — monitor cost and context window utilization
- Surface errors in the UI, not just logs — the user should know when something fails
- Structured logging makes it possible to build dashboards and alerts later

### Health Checks
- FastAPI health endpoint at `/health` checks: database connectivity, Bedrock reachability, Gmail token validity
- Morning brief scheduler reports its next-run time and last-success timestamp

## Agentic Design Principles

### Tool Use & Execution
- Claude is invoked with `tool_use` for structured outputs (intent classification, task extraction, triage)
- Tools are defined per module — the orchestrator selects which tools to expose based on the classified intent
- Tool definitions are kept in sync with Pydantic models to prevent schema drift

### Reflection & Self-Correction
- After generating drafts or summaries, modules can invoke a validation step (e.g., "does this draft address all the points in the original email?")
- Action item extraction includes a self-check: "are there any items in the transcript I might have missed?"
- Failed operations log the error context so the orchestrator can attempt a corrective action

### Context Management (Memory)
- The memory store (pgvector) maintains state across interactions: people, projects, preferences, conversation history
- Context is injected into every module prompt via `context_builder.py` — modules don't query memory directly
- Memory entries have optional TTLs for transient context (e.g., "currently working on X")
- RAG retrieval uses semantic similarity — relevant context is surfaced even with imprecise queries

### Goal-Oriented Planning
- The intent classifier breaks user messages into discrete intents, not vague categories
- Complex requests (e.g., "process this meeting and email the action items to attendees") are decomposed into sequential sub-intents via `follow_up_intents`
- The orchestrator chains module calls in order, passing output from one as input to the next

### Multi-Agent Collaboration
- Modules act as specialized agents that share information through the orchestrator
- Meeting output feeds into Task creation; Email triage feeds into Task auto-capture; Tasks + Email feed into Morning Brief
- The orchestrator is the coordination layer — it decides what flows where

### Incremental Implementation
- Start with the simplest working version of each module, then iterate
- Phase 0 → Foundation → Tasks → Email → Meeting → Brief → GitHub Docs
- Each phase produces a usable system — don't wait for "everything" to be done
- Avoid premature optimization — measure first, then optimize

### Continuous Improvement (AgentOps)
- Gather metrics on every module's output quality (acceptance rates, edit rates)
- Refine prompts based on observed failures — store prompt versions for A/B comparison
- The audit log is the raw data source for identifying improvement opportunities
- Regular review: "what did the assistant get wrong this week?" drives prompt and logic refinements

## Development Workflow

### Adding a New Module
1. Create the module directory under `backend/app/modules/<name>/`
2. Implement `ModuleHandler` in `handler.py`
3. Define supported intents in `backend/app/models/orchestrator.py`
4. Register the handler in `backend/app/orchestrator/module_router.py`
5. Add API routes in `backend/app/routes/<name>.py`
6. Write tests in `backend/tests/test_modules/`

### Environment Setup
```bash
# Backend
cd backend && pip install -e ".[dev]"
# Frontend
cd frontend && npm install
# Both
./scripts/run_dev.sh
```

### Running Tests
```bash
cd backend && pytest
cd frontend && npm test
```

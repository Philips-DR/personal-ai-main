# Personal AI Assistant

An agentic AI assistant that reads your inbox, processes meeting recordings, tracks your
tasks, and writes you a morning brief — built by the AyaData AI Solutions team.

A FastAPI backend routes every user message through an orchestrator that classifies intent,
pulls relevant context from a pgvector memory store, and dispatches to one of eight
independent modules. A Next.js frontend provides the chat surface, an audit viewer, and
settings. Claude runs on AWS Bedrock.

---

## Contents

- [How it works](#how-it-works)
- [Modules](#modules)
- [Tech stack](#tech-stack)
- [Project layout](#project-layout)
- [Getting started](#getting-started)
- [Running the services](#running-the-services)
- [API reference](#api-reference)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)

---

## How it works

Every message posted to `/api/chat` flows through the orchestrator
(`backend/app/orchestrator/orchestrator.py`):

```
User message
     │
     ▼
1. Build context        ← pgvector similarity search over memory_entries
     │
     ▼
2. Classify intent      ← Claude returns JSON → Intent + parameters + confidence
     │
     ▼
3. Route to module      ← ModuleRouter registry (intent → handler)
     │
     ▼
4. Execute handler      → ModuleResponse
     │
     ▼
5. Chain follow-ups     ← follow_up_intents, max depth 3
     │
     ▼
6. Persist memory       → memory_entries
     │
     ▼
7. Write audit entry    → audit_log (intent, module, duration, tokens, confidence)
     │
     ▼
ChatResponse (content + structured data + pending actions)
```

Classification below `INTENT_CONFIDENCE_THRESHOLD` (default `0.6`) falls back to
`general.chat` rather than guessing at a module.

Three properties are worth calling out:

**Modules never talk to each other.** They communicate only by returning
`follow_up_intents`, which the orchestrator resolves and chains. Meeting output can feed
task creation without the meeting module knowing the task module exists.

**Nothing consequential happens without approval.** Modules return `PendingAction` objects
rather than executing directly. The UI surfaces them; the user confirms via
`/api/actions/execute` or discards via `/api/actions/reject`. Email sending is gated in the
Gmail client itself, not just in the UI.

**Every action is logged.** The `audit_log` table is append-only and records intent, module,
input/output summaries, duration, token usage, and classification confidence. Browse it at
`/admin/audit`.

---

## Modules

Each module implements the `ModuleHandler` ABC in `backend/app/modules/base.py` and declares
which intents it serves. Registration happens in one place —
`backend/app/routes/chat.py`.

| Module | Intents | Responsibility |
| --- | --- | --- |
| **General chat** | `general.chat`, `memory.recall` | Conversation and memory lookup |
| **Tasks** | `task.create`, `task.list`, `task.update`, `task.remind` | Task CRUD, reminders, auto-capture from other modules |
| **Email** | `email.read`, `email.triage`, `email.draft`, `email.summarize`, `email.send` | Gmail lifecycle: polling, triage, draft generation, review-gated send |
| **Meeting** | `meeting.transcribe`, `meeting.summarize`, `meeting.actions` | Audio → transcript → summary → action items |
| **Morning brief** | `brief.generate`, `brief.configure` | Scheduled daily aggregation across tasks, email, and roadmaps |
| **GitHub docs** | `github.document` | Repository analysis and documentation generation |
| **Drive** | `drive.search`, `drive.read`, `doc.create`, `doc.append`, `sheet.append_row` | Google Drive, Docs, and Sheets |
| **Learning coach** | `learning.plan`, `learning.review`, `learning.prompt`, `life.suggest` | Skill roadmaps and review prompts |

The `Intent` enum in `backend/app/models/orchestrator.py` is the single source of truth for
every supported intent.

### Transcription providers

The meeting module speaks to an abstract `TranscriptionProvider` interface with a factory
that selects the implementation at runtime — AssemblyAI (hosted) or faster-whisper (local).
Set `TRANSCRIPTION_PROVIDER=assemblyai|whisper`.

---

## Tech stack

| Layer | Choice |
| --- | --- |
| Backend | Python 3.11+, FastAPI, Uvicorn, Pydantic v2 |
| AI | Claude via AWS Bedrock (`anthropic[bedrock]`), Titan v2 embeddings |
| Database | PostgreSQL 16 + pgvector, asyncpg, SQLAlchemy 2 (async) |
| Migrations | Alembic |
| Scheduling | APScheduler (morning brief cron) |
| Integrations | Gmail API (OAuth 2.0), Google Drive/Docs/Sheets, GitHub REST, AssemblyAI, faster-whisper |
| Frontend | Next.js 15, React 19, TypeScript (strict), Tailwind CSS |
| Logging | structlog |
| Tooling | ruff, pytest, ESLint, Vitest |

---

## Project layout

```
backend/
  app/
    main.py                  FastAPI app, router registration, /health
    config.py                pydantic-settings — SSOT for all runtime config
    claude.py, bedrock.py    Bedrock client and token accounting
    models/                  Pydantic models — SSOT for data shapes
    orchestrator/
      orchestrator.py        Classify → route → chain → persist → audit
      intent_classifier.py   Claude-based intent classification
      context_builder.py     Memory retrieval and prompt context assembly
      module_router.py       Intent → handler registry
    modules/
      base.py                ModuleHandler ABC
      email/ meeting/ tasks/ morning_brief/ github_docs/ drive/
      learning_coach/ general_chat/ calendar/
    memory/                  pgvector store, embeddings, retriever
    audit/                   Append-only action logger
    preferences/             User preference store
    routes/                  FastAPI routers, one per domain
  migrations/                Alembic versions (SSOT for schema)
  tests/
    test_modules/            Per-module handler tests
    test_orchestrator/       End-to-end flows with mocked services
    evals/                   Eval harness — intent routing, action extraction

frontend/
  app/
    page.tsx                 Chat interface
    admin/audit/             Audit log viewer and metrics
    settings/                User preferences
    components/              ChatWindow, MessageBubble
    lib/
      api-client.ts          Typed fetch wrapper
      types.ts               Mirrors backend Pydantic models

infra/
  docker-compose.yml         pgvector/pgvector:pg16 on host port 5433
  nginx/                     Reverse proxy config

scripts/
  run_dev.sh                 Start both services
  backend.sh frontend.sh     Per-service process managers
  db.sh                      Postgres container lifecycle
  nginx.sh                   Nginx install and config deployment
  migrate.py                 Apply raw SQL migrations in backend/migrations/versions
  seed_memory.py             Seed baseline people/project/preference memory entries
  setup_oauth.py             CLI Gmail OAuth flow (Desktop app clients only)
```

### Database tables

`memory_entries` (pgvector), `tasks`, `projects`, `email_threads`, `meetings`,
`meeting_action_items`, `audit_log`, `oauth_tokens`, `user_preferences`.

---

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for local Postgres)
- An AWS account with Bedrock access to Claude and Titan embeddings

### 1. Configuration

```bash
cp backend/.env.example backend/.env.local
```

Fill in `backend/.env.local` — at minimum:

| Variable | Purpose |
| --- | --- |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | Bedrock access |
| `DATABASE_URL` | `postgresql+asyncpg://assistant:assistant@localhost:5433/assistant` |
| `OAUTH_TOKEN_ENCRYPTION_KEY` | Fernet key — see below |
| `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET` | Gmail OAuth (optional; email module only) |
| `ASSEMBLYAI_API_KEY` | Hosted transcription (optional; use `whisper` to run locally) |
| `GITHUB_TOKEN` | Read-only token (optional; GitHub docs module only) |

Generate the token encryption key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Every other setting — token budgets, result limits, cron schedules, timeouts — has a sensible
default in `config.py` and can be overridden through the environment. Nothing is hardcoded in
module code.

> `backend/.env.local` is the one place configuration lives. `config.py` resolves it by
> absolute path, and the service scripts read the same file for `BACKEND_URL` and
> `FRONTEND_URL` to decide which ports to bind — so everything agrees no matter which
> directory you run from. Ports default to `8001` (backend) and `3001` (frontend), matching
> the nginx config.

### 2. Database

```bash
./scripts/db.sh start          # Postgres 16 + pgvector on localhost:5433
cd backend && alembic upgrade head
```

### 3. Dependencies

```bash
cd backend && pip install -e ".[dev]"
cd frontend && npm install
```

### 4. Run

```bash
./scripts/run_dev.sh dev
```

Backend on `:8001` (`/docs` for interactive API docs), frontend on `:3001`.

### 5. Connect Gmail (optional)

With the backend running, visit `/api/auth/gmail`. This redirects through Google's consent
screen and stores the resulting tokens **encrypted** in the `oauth_tokens` table.

Register `GMAIL_REDIRECT_URI` (default `http://localhost:8001/api/auth/gmail/callback`) as an
authorized redirect URI on your OAuth client, or the consent screen will reject the request.

There is also a command-line path that writes through the same encrypted storage:

```bash
python scripts/setup_oauth.py
```

It uses an ephemeral localhost port, so it needs an OAuth client of type **Desktop app**. If
yours is a **Web application** client, use the browser flow above instead.

Scopes cover Gmail (`readonly`, `compose`, `send`, `modify`), read-only Calendar, and Drive,
Docs, and Sheets — see `SCOPES` in `backend/app/modules/email/oauth.py`, the single place
they are declared.

---

## Running the services

Each script accepts `start`, `stop`, `restart`, `status`, `logs [N]`, and `kill`.

| Command | Effect |
| --- | --- |
| `./scripts/run_dev.sh dev` | Backend + frontend in dev mode (hot reload) |
| `./scripts/run_dev.sh start` | Both in production mode |
| `./scripts/run_dev.sh status` | Health of both services |
| `./scripts/run_dev.sh logs 50` | Last 50 lines from each |
| `./scripts/backend.sh logs -f` | Stream backend logs |
| `./scripts/frontend.sh dev` | Frontend only, hot reload |
| `./scripts/db.sh psql` | Interactive psql shell |
| `./scripts/db.sh reset` | Destroy the container **and its data volume** |

---

## API reference

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/chat` | Main entry point — orchestrated message handling |
| `GET` | `/api/tasks/` | List tasks (filter by `status`, `owner`) |
| `POST` | `/api/tasks/` | Create a task |
| `PATCH` | `/api/tasks/{id}` | Update a task |
| `POST` | `/api/tasks/{id}/complete` | Mark complete |
| `GET` | `/api/email/threads` | List tracked threads |
| `POST` | `/api/email/triage` | Run triage over untriaged threads |
| `POST` | `/api/email/draft/{thread_id}/approve` | Approve a draft (review gate) |
| `POST` | `/api/email/draft/{thread_id}/reject` | Discard a draft |
| `POST` | `/api/meeting/process` | Upload and process a recording |
| `GET` | `/api/meeting/{id}` | Fetch a processed meeting |
| `GET` | `/api/brief/` | Generate the morning brief |
| `POST` | `/api/brief/configure` | Update brief schedule and content |
| `POST` | `/api/github-docs/generate` | Analyze a repo and generate docs |
| `GET` | `/api/auth/gmail` | Start the Gmail OAuth flow |
| `POST` | `/api/actions/execute` | Approve a `PendingAction` |
| `POST` | `/api/actions/reject` | Reject a `PendingAction` |
| `GET` | `/api/preferences` | Read user preferences |
| `PATCH` | `/api/preferences` | Update user preferences |
| `GET` | `/api/admin/audit` | Paginated audit log |
| `GET` | `/api/admin/metrics` | Intent accuracy, latency, token usage |
| `GET` | `/health` | Liveness and environment |

Interactive docs are served at `/docs` in non-production environments.

---

## Testing

```bash
cd backend && pytest              # unit + integration
cd backend && pytest -m eval      # eval harness (intent routing, action extraction)
cd backend && ruff check .        # lint
cd frontend && npm test           # Vitest
cd frontend && npm run lint       # ESLint
```

External services are mocked throughout — the suite needs no AWS credentials, no Gmail
connection, and no network access. Eval tests are marked separately so they can run on their
own cadence.

---

## Deployment

`infra/nginx/personal-assistant.conf` terminates HTTP and splits traffic: `/api/` and
`/health` to the FastAPI upstream, everything else to Next.js. The frontend calls relative
`/api/*` paths, so it expects to sit behind this proxy (or an equivalent rewrite).

```bash
sudo ./scripts/nginx.sh install   # install, deploy config, start
sudo ./scripts/nginx.sh reload    # after editing the config
```

Update the upstream addresses and `server_name` in that config for your host. Long timeouts
are already configured — model responses can take a while.

---

## Contributing

[`CLAUDE.md`](CLAUDE.md) holds the full development guidelines. The essentials:

**Adding a module**

1. Create `backend/app/modules/<name>/`
2. Implement `ModuleHandler` in `handler.py`
3. Add intents to the `Intent` enum in `backend/app/models/orchestrator.py`
4. Register the handler in `backend/app/routes/chat.py`
5. Add routes in `backend/app/routes/<name>.py` if it needs its own endpoints
6. Write tests in `backend/tests/test_modules/`

**Conventions**

- Modules stay independent — no cross-module imports, ever
- Every handler and route is `async`
- Type hints on all Python signatures; TypeScript strict mode, no `any`
- Custom exception classes from `models/` — never a bare `Exception`
- Structured logs with `module`, `action`, `duration` — never tokens, email bodies, or PII
- Secrets belong in `.env.local` (gitignored); document new variables in `.env.example`
- Import shared constants from their canonical source rather than redefining them

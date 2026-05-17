# SmartAgile — Backend (Django API)

REST API for authentication, usage ingestion, analytics, attendance, tasks/projects (via `tasks` app), and the AI assistant.

**Requirements:** see [`requirements.txt`](requirements.txt) · **Config template:** [`.env.example`](.env.example)

---

## Stack

- Django 3.2 LTS, Django REST Framework, SimpleJWT
- Custom user: `accounts.User` (`email` login, `role`: `employee` | `admin`)
- PostgreSQL (configured in `backend/settings.py`)
- Celery + Redis (optional; eager mode works without Redis for local dev)
- LangGraph assistant (`smartagile/assistant_graph/`)

---

## Prerequisites

- Python **3.10–3.12**
- PostgreSQL **12+** with a database created (default name: `smartagile_database`)
- Optional: Redis (only if `CELERY_TASK_ALWAYS_EAGER=0`)

---

## Setup

### 1. Virtual environment & dependencies

**Windows**

```bat
cd backend
setup_venv.bat
.venv\Scripts\activate
```

**macOS / Linux**

```bash
cd backend
chmod +x setup_venv.sh && ./setup_venv.sh
source .venv/bin/activate
```

Or manually:

```bash
python -m venv .venv
source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Environment file

```bash
copy .env.example .env    # Windows
# cp .env.example .env
```

Edit `.env` for:

- `GROQ_API_KEY` / `OPENAI_API_KEY` (assistant)
- `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` (password reset OTP)
- Celery/Redis overrides (optional)

`.env` is gitignored — do not commit it.

### 3. Database

Create the DB, then align `DATABASES` in `backend/backend/settings.py` with your host, user, and password.

```bash
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
```

### 4. Run development server

```bash
python manage.py runserver
```

Base URL: **http://127.0.0.1:8000**

---

## URL map

| Path | Description |
|------|-------------|
| `/api/login/`, `/api/signup/`, `/api/logout/` | Auth (JWT access + refresh) |
| `/api/me/` | Current session (works with expired token → `authenticated: false`) |
| `/api/token/refresh/` | Refresh access token |
| `/api/usage-events/batch/` | Desktop agent ingest (authenticated POST) |
| `/api/appdata/` | Aggregated usage for dashboards |
| `/api/insights/summary/` | Daily features + insight cards |
| `/api/assistant/...` | Chat sessions & messages |
| `/api/attendence/` | Attendance records |
| `/taskapi/tasks/`, `/taskapi/admin/...` | Tasks & projects (`tasks` app) |
| `/admin/` | Django admin |
| `/media/` | Profile photos |

---

## Celery (usage queue & daily rollup)

**Local default:** `CELERY_TASK_ALWAYS_EAGER=true` — usage batches are saved in-process (no Redis required).

**Production-style:**

1. Install and start Redis.
2. In `.env`: `CELERY_TASK_ALWAYS_EAGER=0`
3. Run worker and beat from `backend/`:

```bash
celery -A backend worker -l info
celery -A backend beat -l info
```

Beat runs `usage-daily-rollup` at 03:05 (see `CELERY_BEAT_SCHEDULE` in settings).

---

## Django apps

| App | Role |
|-----|------|
| `accounts` | `AUTH_USER_MODEL`, registration |
| `smartagile` | Auth views, usage, insights, assistant, attendance hooks |
| `tasks` | Projects, project members, kanban tasks |

---

## Management commands (migration / repair)

```bash
python manage.py repair_accounts_dependency
python manage.py repair_legacy_auth_to_accounts
```

Use when upgrading from older DB layouts (legacy `SignupData` → `accounts.User`).

---

## Assistant configuration

Controlled via `.env` (see `.env.example`):

| Variable | Purpose |
|----------|---------|
| `LLM_PROVIDER` | `auto`, `groq`, or `openai` |
| `GROQ_API_KEY`, `OPENAI_API_KEY` | LLM providers |
| `ASSISTANT_LLM_CLASSIFY` | `0` = rules, `1` = LLM intent |
| `ASSISTANT_LLM_SYNTHESIZE` | `1` = LLM answers (default) |

Without API keys, the assistant falls back to deterministic productivity snapshots.

---

## Testing the API

```bash
# Health: current user (no auth)
curl http://127.0.0.1:8000/api/me/

# Login
curl -X POST http://127.0.0.1:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"you@example.com\",\"password\":\"your-password\"}"
```

Use the returned `access` token: `Authorization: Bearer <access>`.

---

## Related docs

- [Root README](../README.md) — full stack & desktop pairing
- [Front-end README](../front-end/README.md)
- [Desktop agent README](../desktop-agent/README.md)
- [Usage partitioning notes](docs/USAGE_EVENTS_PARTITIONING.md) (optional advanced)

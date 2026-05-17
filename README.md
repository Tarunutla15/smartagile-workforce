# SmartAgile

Workforce productivity platform: desktop activity tracking, usage analytics, tasks/projects, attendance, and an AI assistant grounded in your work patterns.

| Service | Folder | Stack |
|---------|--------|--------|
| **API** | [`backend/`](backend/) | Django 3.2, DRF, JWT, Celery, PostgreSQL |
| **Web app** | [`front-end/`](front-end/) | React 18, MUI, Create React App |
| **Desktop agent** | [`desktop-agent/`](desktop-agent/) | Python (Windows), scikit-learn |

---

## Architecture (quick view)

```
┌─────────────────┐     JWT / REST      ┌──────────────────┐
│  React ( :3000 )│ ◄──────────────────►│ Django ( :8000 ) │
└────────┬────────┘                     └────────┬─────────┘
         │ localhost pairing                      │
         │ (Settings → Connect)                   │ PostgreSQL
         ▼                                        ▼
┌─────────────────┐     POST /api/usage-events/batch/
│ Desktop agent   │ ────────────────────────────────┘
│ (Windows, :38475)│
└─────────────────┘
```

- **Web** talks to Django at `/api/*` and `/taskapi/*` (dev proxy forwards from port 3000).
- **Agent** uploads usage batches with the same JWTs, obtained via one-click pairing (no copy-paste).

Details: [backend/README.md](backend/README.md) · [front-end/README.md](front-end/README.md) · [desktop-agent/README.md](desktop-agent/README.md)

---

## Prerequisites

| Tool | Version | Used by |
|------|---------|---------|
| **Python** | 3.10–3.12 | Backend, desktop agent |
| **Node.js** | 18 or 20 LTS | Front-end |
| **PostgreSQL** | 12+ | Backend database |
| **Redis** | Optional | Celery queue (production); dev defaults to inline tasks |

**Desktop agent:** Windows only (foreground window + input hooks).

---

## First-time setup (all services)

### 1. Database

Create a PostgreSQL database (default name in settings: `smartagile_database`):

```sql
CREATE DATABASE smartagile_database;
```

Update credentials in `backend/backend/settings.py` (`DATABASES`) if yours differ.

### 2. Backend

```bash
cd backend
# Windows
setup_venv.bat
# macOS / Linux
# chmod +x setup_venv.sh && ./setup_venv.sh

copy .env.example .env    # Windows
# cp .env.example .env    # macOS / Linux
# Edit .env — LLM keys, email, etc.

.venv\Scripts\activate    # Windows
# source .venv/bin/activate

python manage.py migrate
python manage.py createsuperuser   # optional
python manage.py runserver
```

API: **http://127.0.0.1:8000**

### 3. Front-end

```bash
cd front-end
npm install
npm start
```

App: **http://localhost:3000**

Optional: copy `front-end/.env.example` → `.env.local` if you change the agent pairing port.

### 4. Desktop agent (Windows)

```bash
cd desktop-agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python continous_task.py
```

Keep this running while you want activity tracked.

---

## Connect the desktop agent to your account

This links the agent on your PC to the same JWT session as the browser.

1. Start **backend** and **front-end**; log in as an employee.
2. Start the **desktop agent** (`python continous_task.py`).
3. Open **Employee dashboard → Settings**.
4. Click **Connect desktop app (save tokens to this PC)**.

The browser sends access + refresh tokens to `http://127.0.0.1:38475` (localhost only). Tokens are stored at:

- Windows: `%APPDATA%\SmartAgile\auth.json`

After pairing, usage events flow to `POST /api/usage-events/batch/` every few seconds.

**Troubleshooting**

| Issue | Fix |
|-------|-----|
| “Agent not detected” on Settings | Run `continous_task.py`; check firewall allows localhost |
| Port mismatch | Set same port in `SMARTAGILE_LOCAL_PORT` and `REACT_APP_AGENT_LOCAL_PORT` (default `38475`) |
| 401 on upload | Log in again in the browser and re-pair |
| No data in dashboard | Wait 1–2 minutes; confirm backend is running and Celery/eager ingest is enabled |

Full agent docs: [desktop-agent/README.md](desktop-agent/README.md)

---

## Typical dev workflow

Open **three terminals**:

| # | Directory | Command |
|---|-----------|---------|
| 1 | `backend/` | `python manage.py runserver` |
| 2 | `front-end/` | `npm start` |
| 3 | `desktop-agent/` | `python continous_task.py` |

Then: sign up or log in → employee dashboard → pair agent in Settings → use apps; check **Apps & Websites** and **Insights**.

**Admin:** register with `role` admin or promote user in Django admin → `/admin/dashboard`.

---

## API routes (reference)

| Prefix | App | Examples |
|--------|-----|----------|
| `/api/` | smartagile | `login/`, `me/`, `appdata/`, `insights/summary/`, `usage-events/batch/`, `assistant/` |
| `/taskapi/` | tasks | `tasks/`, `my-projects/`, `admin/projects/` |
| `/admin/` | Django admin | Staff users |

---

## Environment & secrets

- **Never commit** `backend/.env`, real API keys, or `auth.json` from the desktop agent.
- Safe templates: `backend/.env.example`, `front-end/.env.example`.
- Profile uploads live under `backend/media/` (gitignored in production setups).

---

## Production notes (short)

- Set `DEBUG = False`, configure `ALLOWED_HOSTS`, use a real secret key.
- Run Celery worker + beat; set `CELERY_TASK_ALWAYS_EAGER=0` and Redis URLs in `.env`.
- Serve React `build/` behind nginx/CDN; point `REACT_APP_API_BASE` at your API origin.
- Build and sign the desktop agent for distribution; users still pair via Settings.

---

## Repository layout

```
SmartAgile/
├── README.md                 ← this file
├── backend/                  ← Django API
│   ├── README.md
│   ├── requirements.txt
│   └── .env.example
├── front-end/                ← React SPA
│   ├── README.md
│   ├── package.json
│   └── .env.example
└── desktop-agent/            ← Windows usage collector
    ├── README.md
    ├── requirements.txt
    └── models/               ← ML pickles (required at runtime)
```

---

## License

Add your license here before publishing (e.g. MIT, proprietary).

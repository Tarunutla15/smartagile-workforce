# SmartAgile — Desktop agent (Windows)

Background service that tracks **foreground application and browser** usage, categorizes activity with on-device ML models, and sends **batched events** to the Django API.

**Requirements:** [`requirements.txt`](requirements.txt)  
**Entry point:** `continous_task.py`

> **Platform:** Windows only (`pywinctl`, Win32 foreground hooks). Run on the same machine where you work.

---

## What it does

1. Detects the active window (app or browser tab title).
2. Records duration, idle time, keystrokes, clicks, scrolls per segment.
3. Labels category (e.g. work-related) using bundled scikit-learn models in `models/`.
4. Queues events and POSTs batches to `POST /api/usage-events/batch/` with your JWT.

The web app never reads your screen directly — only this agent collects machine-local activity.

---

## Prerequisites

- **Windows 10/11**
- **Python 3.10–3.12**
- SmartAgile **backend** running and reachable (default `http://127.0.0.1:8000`)
- Bundled `models/` directory next to `continous_task.py` (`.pkl` + `exe_to_software.json` — required)

---

## Setup

```bash
cd desktop-agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python continous_task.py
```

Leave the process running while you want tracking enabled.

---

## Pair with your account (recommended)

No manual token copy.

1. Start this agent (`python continous_task.py`).
2. A **localhost pairing server** starts on `http://127.0.0.1:38475` (see `local_pairing_server.py`).
3. In the browser: log in → **Employee dashboard → Settings**.
4. Click **Connect desktop app (save tokens to this PC)**.

Tokens are saved to:

| OS | Path |
|----|------|
| Windows | `%APPDATA%\SmartAgile\auth.json` |
| Other | `~/.config/smartagile/auth.json` |

The agent refreshes the access token automatically (same refresh flow as the web app).

### Pairing port

Default **38475**. If you change it:

| Side | Variable |
|------|----------|
| Agent | `SMARTAGILE_LOCAL_PORT` |
| Front-end | `REACT_APP_AGENT_LOCAL_PORT` in `front-end/.env.local` |

Both must match.

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SMARTAGILE_API_BASE` | `http://127.0.0.1:8000` | Django API root (also set when pairing from Settings) |
| `SMARTAGILE_LOCAL_PORT` | `38475` | Localhost pairing HTTP port |
| `SMARTAGILE_ACCESS_TOKEN` | — | Optional JWT override (skips `auth.json`; dev only) |

---

## Manual / dev override

If pairing is not used, set a valid access token:

```bat
set SMARTAGILE_ACCESS_TOKEN=eyJ...
set SMARTAGILE_API_BASE=http://127.0.0.1:8000
python continous_task.py
```

Tokens expire — pairing from Settings is preferred.

---

## How uploads work

- Writer: `http_batch_writer.py`
- Batch interval: ~2 seconds, up to 48 events per request
- Endpoint: `{SMARTAGILE_API_BASE}/api/usage-events/batch/`
- Auth: `Authorization: Bearer <access_token>`

Until paired, the agent logs once: *“Not paired yet…”* and drops batches (normal until you connect from Settings).

---

## Backend / Celery

| Mode | Behavior |
|------|----------|
| `CELERY_TASK_ALWAYS_EAGER=true` (backend default) | Events saved immediately — no Redis |
| Production | Redis + Celery worker; `CELERY_TASK_ALWAYS_EAGER=0` |

See [backend/README.md](../backend/README.md).

---

## ML models (`models/`)

| File | Role |
|------|------|
| `rf_model.pkl` | Random forest classifier |
| `svm_pipeline.pkl` | SVM pipeline |
| `app_vectorizer.pkl` | Text vectorizer for app names |
| `exe_to_software.json` | Executable → friendly software name |

Do not delete or relocate `models/` — the agent loads them at startup.

---

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| Settings shows “agent offline” | Agent running? Port 38475 free? |
| 401 errors in agent log | Re-login in browser; pair again |
| No data in dashboard | Backend up? Wait 1–2 min after using apps |
| Import / sklearn errors | `pip install -r requirements.txt`; Python 3.10–3.12 |
| Model file missing | Ensure `models/*.pkl` exist in repo |

---

## Related docs

- [Root README](../README.md) — full stack setup
- [Backend README](../backend/README.md) — API & ingest
- [Front-end README](../front-end/README.md) — Settings pairing UI

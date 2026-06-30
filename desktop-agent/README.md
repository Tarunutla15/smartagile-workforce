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
4. Enriches context per app via **plugins** (e.g. `chrome.exe` → `YouTube` / "React Tutorial").
5. Queues events and POSTs batches to `POST /api/usage-events/batch/` with your JWT.

The web app never reads your screen directly — only this agent collects machine-local activity.

---

## Architecture

The tracker is split into a core pipeline plus an optional plugin layer:

```
agent/
  core/      window_tracker · input_tracker · idle_tracker · classifier · uploader · auth · engine · single_instance
  plugins/   base · registry · browser_plugin · vscode_plugin · outlook_plugin · app_plugin
continous_task.py     # thin entrypoint (start/stop + pairing server + single-instance guard + engine watchdog)
http_batch_writer.py  # resilient upload loop (retry, idempotent batches, status reporting)
agent_status.py       # in-process upload status shared with the pairing server /health
local_pairing_server.py  # localhost token pairing + /health (now includes live upload status)
```

> **Run only one agent at a time.** Two agents on the same PC both track the same
> foreground window and upload near-identical segments, so every tracked second is
> counted twice. `agent/core/single_instance.py` enforces this with a Windows named
> mutex: a second launch prints *"Another SmartAgile agent is already running…"* and
> exits immediately instead of double-counting.

**Plugins** turn a coarse `(exe, window title)` into a richer `(app, activity)`:

| Window | Default | With plugin |
|--------|---------|-------------|
| `chrome.exe` · "React Tutorial - YouTube" | Google Chrome · (session) | **Google Chrome** · "YouTube - React Tutorial" |
| `chrome.exe` · "asyncio … - Stack Overflow" | Google Chrome · (session) | **Google Chrome** · "Stack Overflow - asyncio …" |
| `Cursor.exe` · "● engine.py - smartagile - Cursor" | Cursor · (session) | **Cursor** · "engine.py - smartagile" |

Browsers stay **one card per browser** (Chrome/Edge/Brave); the site + page go in the
activity, so tabs are listed inside that card rather than fragmenting into many per-site apps.

If no plugin matches (or one errors), the engine falls back to the original behaviour
(ML category + exe→software name). Disable all specialised plugins with
`SMARTAGILE_PLUGINS=off`.

### Browser URLs (on by default)

Beyond the window **title**, the agent reads the active tab's **URL** via Windows UI
Automation (`uiautomation`). This is **on by default**; disable with
`SMARTAGILE_BROWSER_URL=0`. For each browser event it then:

- stores the `url` and registrable `domain` on the event (persisted by the backend), and
- uses the domain for a **deterministic category** — e.g. `github.com`/`docs.google.com`
  → `work`, `youtube.com`/`reddit.com` → `entertainment` — overriding the noisier
  title-based ML guess (`agent/plugins/browser_plugin.py`), and labels the site in the
  activity (e.g. `YouTube - React Tutorial`) while keeping the browser as the app card.

Capture is best-effort and fragile (active tab only, depends on the browser's accessibility
tree) — it degrades silently to title-only when the address bar can't be read. The full URL
(including query string) is stored; trim to domain-only in `browser_url.py` /
`usage_ingest.py` if you prefer.

### Accurate names & noise filtering

To behave like a proper digital-wellbeing tracker (rather than dumping raw process names):

- **Display names** — apps resolve to friendly names like Task Manager / Digital Wellbeing
  show: a curated override map, then `exe_to_software.json`, then the executable's version
  resource **`FileDescription`** (`Code.exe` → "Visual Studio Code"), then the exe stem
  (`agent/core/classifier.py`, `agent/core/win32.py:file_description`).
- **System / lock filtering** — OS surfaces (`LockApp`, `SearchHost`, `ShellExperienceHost`,
  `CredentialUIBroker`, `WidgetBoard`, `dwm`, …) are dropped, not recorded, so the lock
  screen and shell chrome no longer count as "work" (`agent/core/ignore.py`). `LockApp`
  also marks the machine as locked/away.
- **Deterministic categories** — known executables override the ML guess (which tends to
  label unknown apps "work"): editors/terminals/DB tools → `work`, Teams/Slack/WhatsApp/
  Outlook → `communication`, Spotify/Steam/VLC → `entertainment`
  (`_APP_CATEGORY` in `classifier.py`). Browser domains do the same (see above).

---

## Prerequisites

- **Windows 10/11**
- **Python 3.10–3.12**
- SmartAgile **backend** running and reachable (default `http://127.0.0.1:8000`)
- Bundled `models/` directory next to `continous_task.py` (`.pkl` + `exe_to_software.json` — required)

---

## Setup

```powershell
cd desktop-agent
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
py continous_task.py
```

Leave the process running while you want tracking enabled. **Run only one copy** — a
second one double-counts usage (the built `.exe` blocks this automatically; see
*Architecture*).

`pyinstaller` (for building the `.exe`, see *Packaging*) is the one extra left **commented
out** in `requirements.txt`; install it only when you need to build. Browser-URL capture
(`uiautomation`) is now a normal dependency and on by default — see below.

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
| `SMARTAGILE_PLUGINS` | `on` | Set `off` to disable per-app context plugins |
| `SMARTAGILE_BROWSER_URL` | `on` | Capture active-tab URL + domain (uses `uiautomation`); set `0` to disable |

---

## Packaging (build a downloadable `.exe`)

The repo ships a reproducible PyInstaller spec — **`SmartAgileAgent.spec`** — that bundles
`models/`, pins the hidden imports (`sklearn`, `pywinctl`, `pynput`, `comtypes`, …) and
builds a one-file exe. Use it instead of a raw `pyinstaller` command.

**1. Install the builder (once, into the same Python you run the agent with):**

```powershell
py -m pip install pyinstaller
```

**2. Stop any running agent first** — PyInstaller cannot overwrite a locked
`dist\SmartAgileAgent.exe`. A one-file exe runs as **two** processes (parent bootloader +
child), so kill by name and confirm zero remain:

```powershell
Get-Process SmartAgileAgent -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1
(Get-Process SmartAgileAgent -ErrorAction SilentlyContinue | Measure-Object).Count   # must print 0
```

**3. Build** (from the `desktop-agent` folder):

```powershell
py -m PyInstaller SmartAgileAgent.spec --noconfirm --clean
```

Output: **`dist\SmartAgileAgent.exe`** (~168 MB, takes a couple of minutes). The classifier
resolves `models/` from `sys._MEIPASS` when frozen, so the bundled `.pkl` +
`exe_to_software.json` are found automatically. Drop `--clean` for faster repeat builds.

**4. Verify the single-instance guard:**

```powershell
Start-Process .\dist\SmartAgileAgent.exe   # first copy: runs + starts pairing server
.\dist\SmartAgileAgent.exe                 # second copy: prints "already running…" and exits
```

> Build on Windows. Unsigned binaries that read keyboard/mouse input may trigger
> SmartScreen/AV warnings — code-sign for real distribution.

### Build fails with `PermissionError: [WinError 5] Access is denied: …\dist\SmartAgileAgent.exe`

The old exe is still locked. Re-run the stop step in **2** until the count is `0`, then if
needed delete the stale file before rebuilding:

```powershell
Remove-Item .\dist\SmartAgileAgent.exe -Force -ErrorAction SilentlyContinue
py -m PyInstaller SmartAgileAgent.spec --noconfirm --clean
```

If `Remove-Item` itself reports access denied, a process still holds the file (re-run
`Stop-Process`), or Windows Defender is mid-scan on the 168 MB file (retry, or add a
`dist\` exclusion).

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
- Optional header: `X-SmartAgile-Agent-Version: <build>` (recorded as the agent version server-side)

Until paired, the agent logs once: *“Not paired yet…”* and drops batches (normal until you connect from Settings).

---

## Reliability & resilience

The data pipeline is built so tracking **never stops silently**:

- **Crash-proof tracking loop** — each iteration of the engine loop is guarded; a transient
  error (COM hiccup, plugin edge case, bad foreground read) is logged and the loop
  continues instead of killing the thread (`agent/core/engine.py`).
- **Engine watchdog** — `continous_task.py` checks the tracking thread every 2 s and restarts
  a fresh `TrackingEngine` if it ever dies. The uploader has the same self-healing
  (`Uploader._ensure_alive`).
- **Upload loop never dies** — `http_batch_writer.py` catches all `requests` exceptions and a
  final catch-all; transient failures (network blips, sleep/wake, server restarts, 408/429/5xx)
  keep events **buffered and retried**, bounded by `MAX_PENDING_EVENTS` so memory can't grow
  without limit.
- **Idempotent batches** — every segment carries a `client_event_id` (UUID). The backend
  de-dupes on `(user, client_event_id)` (`bulk_create(ignore_conflicts=True)`), so a batch the
  agent retries after an unclear/transient failure is **never double-counted**.
- **Multi-user safety** — each event is tagged with the account paired at capture time; if the
  PC is re-paired to another user while events are still buffered, the old user's events are
  dropped rather than uploaded under the new account (`_purge_foreign_user`).
- **Status surfacing** — the upload loop records its outcome in `agent_status.py`, exposed via
  the pairing server `/health`. Settings shows **tracking active / last upload time**, a
  **temporary issue (retrying)** warning, or a **reconnect needed** prompt when the saved
  session expired — so an expired token is no longer a silent failure.
- **Server readiness** — the agent can probe `GET /api/health/` (DB-backed `200`/`503`) to tell
  a real outage from a cold start, and the backend records a per-user heartbeat
  (`GET /api/agent/status/` → `connected`, `last_seen_at`, `last_event_at`).

> **Known limitation — day boundaries use the server timezone.** Usage is stored with a UTC
> `occurred_at` and bucketed into days using the backend's configured `TIME_ZONE`, not each
> user's local timezone. Activity near midnight for users in a different timezone can land in
> the adjacent day. Fixing this properly means storing a per-user timezone and bucketing per
> user; it touches all analytics/rollup queries, so it is intentionally deferred.

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
| Settings shows “session expired — reconnect” | Token expired; click **Connect** again to re-pair (data keeps buffering until then) |
| 401 errors in agent log | Re-login in browser; pair again |
| No data in dashboard | Backend up? Probe `GET /api/health/`; wait 1–2 min after using apps |
| Usage not double-counted after a retry | Expected — batches are idempotent via `client_event_id` |
| Usage looks doubled | Two agents running at once. The guard prevents this on a rebuilt exe; otherwise `Get-Process SmartAgileAgent \| Stop-Process -Force` and run only one (also stop any `py continous_task.py` dev run) |
| Build: `Access is denied …dist\SmartAgileAgent.exe` | Exe still running/locked — stop all `SmartAgileAgent` processes (see Packaging) |
| Import / sklearn errors | `pip install -r requirements.txt`; Python 3.10–3.12 |
| Model file missing | Ensure `models/*.pkl` exist in repo |

---

## Related docs

- [Root README](../README.md) — full stack setup
- [Backend README](../backend/README.md) — API & ingest
- [Front-end README](../front-end/README.md) — Settings pairing UI

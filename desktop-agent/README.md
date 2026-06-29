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
continous_task.py   # thin entrypoint (start/stop + pairing server + single-instance guard)
```

> **Run only one agent at a time.** Two agents on the same PC both track the same
> foreground window and upload near-identical segments, so every tracked second is
> counted twice. `agent/core/single_instance.py` enforces this with a Windows named
> mutex: a second launch prints *"Another SmartAgile agent is already running…"* and
> exits immediately instead of double-counting.

**Plugins** turn a coarse `(exe, window title)` into a richer `(app, activity)`:

| Window | Default | With plugin |
|--------|---------|-------------|
| `chrome.exe` · "React Tutorial - YouTube" | Google Chrome | **YouTube** · "React Tutorial" |
| `chrome.exe` · "asyncio … - Stack Overflow" | Google Chrome | **Stack Overflow** · "asyncio …" |
| `Cursor.exe` · "● engine.py - smartagile - Cursor" | Cursor · (session) | **Cursor** · "engine.py - smartagile" |

If no plugin matches (or one errors), the engine falls back to the original behaviour
(ML category + exe→software name). Disable all specialised plugins with
`SMARTAGILE_PLUGINS=off`.

### Optional: real browser URLs

By default the agent only sees window **titles**. Set `SMARTAGILE_BROWSER_URL=1` (and
`pip install uiautomation`) to additionally read the active tab's **URL** via Windows UI
Automation. When captured, the domain improves the site label and `url`/`domain` are added
to each browser event. This is best-effort and fragile — it degrades silently to title-only
when the dependency is missing or the address bar can't be read.

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

Two extras are **commented out** in `requirements.txt` — uncomment/install them only if
needed: `uiautomation` (real browser URLs, `SMARTAGILE_BROWSER_URL=1`) and `pyinstaller`
(building the `.exe`, see *Packaging*).

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
| `SMARTAGILE_BROWSER_URL` | `0` | Set `1` to capture active-tab URLs (needs `uiautomation`) |

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
| Usage looks doubled | Two agents running at once. The guard prevents this on a rebuilt exe; otherwise `Get-Process SmartAgileAgent \| Stop-Process -Force` and run only one (also stop any `py continous_task.py` dev run) |
| Build: `Access is denied …dist\SmartAgileAgent.exe` | Exe still running/locked — stop all `SmartAgileAgent` processes (see Packaging) |
| Import / sklearn errors | `pip install -r requirements.txt`; Python 3.10–3.12 |
| Model file missing | Ensure `models/*.pkl` exist in repo |

---

## Related docs

- [Root README](../README.md) — full stack setup
- [Backend README](../backend/README.md) — API & ingest
- [Front-end README](../front-end/README.md) — Settings pairing UI

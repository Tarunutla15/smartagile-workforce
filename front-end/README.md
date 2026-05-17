# SmartAgile — Front-end (React)

Employee and admin dashboards, auth flows, usage charts, intelligence insights, and desktop-agent pairing UI.

**Dependencies:** [`package.json`](package.json) (install with **npm**, not pip).  
**Optional env:** [`.env.example`](.env.example)

---

## Stack

- React 18, React Router 6
- Material UI (MUI) + charts (Chart.js, Recharts, MUI X Charts)
- Axios (`src/api/client.js`) with JWT in `sessionStorage`
- Create React App — dev proxy to Django (`src/setupProxy.js`)

---

## Prerequisites

- **Node.js 18.x or 20.x LTS** ([nodejs.org](https://nodejs.org/))
- **npm** (included with Node)
- Backend running at **http://127.0.0.1:8000** (see [backend/README.md](../backend/README.md))

---

## Setup & run

```bash
cd front-end
npm install
npm start
```

Opens **http://localhost:3000** with hot reload.

### Production build

```bash
npm run build
```

Output: `build/`. Serve static files and set `REACT_APP_API_BASE` to your API URL (see below).

---

## Environment variables

Copy the example file when you need non-default URLs or pairing port:

```bash
copy .env.example .env.local    # Windows
# cp .env.example .env.local
```

| Variable | Default | Purpose |
|----------|---------|---------|
| `REACT_APP_PROXY_TARGET` | `http://127.0.0.1:8000` | CRA dev proxy target for `/api`, `/taskapi`, `/media` |
| `REACT_APP_API_BASE` | *(empty)* | API base for Axios; empty = same origin (use proxy in dev) |
| `REACT_APP_API_ORIGIN` | `http://127.0.0.1:8000` | Origin for profile photo / media URLs |
| `REACT_APP_AGENT_LOCAL_PORT` | `38475` | Desktop agent pairing port (must match agent) |

`.env.local` is gitignored.

---

## Dev proxy

`src/setupProxy.js` forwards these paths to Django so the browser stays on port 3000:

- `/api/*`
- `/taskapi/*`
- `/media/*`

No extra CORS setup needed for local development.

---

## Main routes

| Path | Screen |
|------|--------|
| `/` | Landing |
| `/login`, `/signup` | Auth |
| `/employee/dashboard` | Employee hub (tabs: Home, Tasks, Attendance, Projects, Apps, Settings) |
| `/admin/dashboard` | Org admin (requires `role === admin`) |
| `/admin/sprint-dashboard` | Sprint view |
| `/data-collection` | Tracking disclosure copy |

Global **assistant chat** widget is mounted from `App.js`.

---

## Connect desktop agent (from the UI)

1. Log in and open **Employee dashboard → Settings**.
2. Ensure the Windows agent is running (`desktop-agent/continous_task.py`).
3. Click **Connect desktop app**.

The page calls `http://127.0.0.1:<REACT_APP_AGENT_LOCAL_PORT>/health` and posts JWTs to the agent. See [desktop-agent/README.md](../desktop-agent/README.md).

---

## Project structure (high level)

```
src/
├── api/client.js           # Axios, JWT storage, refresh
├── context/SessionContext.jsx
├── components/             # Auth, assistant widget, pairing, insights
├── Dashboards/
│   ├── EmployeeDBComponent/
│   └── AdminOrg/
├── setupProxy.js
└── App.js                  # Routes
```

---

## Scripts

| Command | Description |
|---------|-------------|
| `npm start` | Dev server (:3000) |
| `npm run build` | Production bundle |
| `npm test` | Jest (CRA) |

---

## Related docs

- [Root README](../README.md)
- [Backend README](../backend/README.md)
- [Desktop agent README](../desktop-agent/README.md)

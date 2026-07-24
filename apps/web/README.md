# Meridian — web frontend

This is the Next.js dashboard (nurse worklist, PA approval, metrics). It is
**only the frontend**. It talks over HTTP to a separate Python/FastAPI
backend — this `package.json` does not and cannot start that backend.

> For the full, canonical run instructions (first-time setup, seeding, evals),
> see the **root `README.md` → "Running it (step by step)"**. This file is the
> quick reference.

## The app is two processes

| Process | Language | Where | How to run | Port |
|---|---|---|---|---|
| **Backend** (API + rule engine) | Python / FastAPI | repo root | `python -m app.main` | 8000 |
| **Frontend** (this project) | Next.js | `apps/web` | `npm run dev` | 3000 |

Start the **backend first** — the frontend reads from it. `package.json` only
controls the frontend; the backend is Python and is never launched by npm.

## Run the backend (from the repo root, not here)

```bash
# first time only
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt   # backend deps live in requirements.txt
.venv/bin/python -m app.seed                # load synthetic referrals into meridian.db

# every time
.venv/bin/python -m app.main                # API on http://localhost:8000 — leave running
```

Verify: <http://localhost:8000/health> should return `{"status":"ok","demo_mode":true}`.
Backend entrypoint: `app/main.py`. Backend config/keys: `.env.example`.

## Run the frontend (this project)

```bash
cd apps/web
npm install                                 # first time only
cp .env.local.example .env.local            # first time only (points at localhost:8000)
npm run dev                                  # UI on http://localhost:3000
```

Then open <http://localhost:3000/worklist>.

### Frontend scripts (`package.json`)

| Command | Does |
|---|---|
| `npm run dev` | Dev server with hot reload |
| `npm run build` | Production build |
| `npm start` | Serve the production build (run `build` first) |
| `npm run lint` | ESLint |

## Deployment

The frontend deploys to Vercel; the backend does not (it needs persistent
disk for SQLite). See the root `README.md → Deployment (Vercel)`.

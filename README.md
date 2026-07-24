# Meridian

An agent that moves a patient from "something's wrong" to a booked colonoscopy with
prior authorization approved. It never diagnoses — it decides exactly one thing: **does
this person need a GI appointment, and how fast.** See `CLAUDE.md` for the full spec and
the non-negotiable invariants this codebase enforces in code, not prompts.

> **DEMO — synthetic data. Not for clinical use.**

## What it does

Two entry points, one deterministic core:

- **Voice intake** — patient calls, a fixed-order question flow elicits red-flag
  features, and a slot is booked at the matching urgency in the same call.
- **Referral triage** — a scanned GI referral is parsed inside a Daytona sandbox,
  features are extracted, and a nurse worklist shows the verdict, the rules that fired,
  and the source snippet behind every feature. If it needs prior auth, the agent drafts
  the packet (every sentence source-linked) and later dials a mock payer IVR to chase
  status.

The architecture that governs everything: **LLMs extract, rules decide.** Messy input
becomes structured features via a model; a versioned, unit-tested rule engine — no model
calls — maps those features to an urgency level. Every verdict records its `rule_version`
and the exact `rules_fired[]`.

## How a referral flows through the system

Follow the demo case — a faxed referral for a 42-year-old, annotated by the
referring office as "probable hemorrhoids":

```
 faxed PDF ──▶ Daytona sandbox ──▶ Fireworks LLM ──▶ rule engine ──▶ nurse worklist
              (untrusted file      (extracts facts:   (deterministic:   (a human approves
               opened in an         age 42, bleeding,  YOUNG_BLEEDING_   before anything
               isolated,            3 weeks, abdominal PLUS_FEATURE      is booked)
               throwaway VM)        pain — nothing     fires → URGENT)
                                    more)
```

1. **Sandbox** — the document is untrusted input, so all decoding/OCR happens in a
   throwaway Daytona VM with networking blocked. Only plain text comes back. The
   worklist shows a 🔒 badge with the sandbox ID as proof it ran isolated.
2. **Extraction** — the LLM's only job is perception: turn text into the structured
   red-flag features in `app/schemas.py`. It is never asked for an opinion.
3. **Decision** — `app/rules.yaml` is evaluated deterministically. All matching rules
   fire, the highest urgency wins, and the full list is stored for the audit trail.
4. **Human sign-off** — the verdict lands on the nurse worklist. Nothing is booked
   until a named human approves it.

If **any** step fails — sandbox error, LLM timeout, unparseable document, low
extraction confidence — the referral routes to `ESCALATE` for human review. There is
no code path that auto-clears a patient.

## Layout

```
app/                 schemas, monotonic urgency, rule engine, output filter, DB, FastAPI app
services/referral/   Daytona-sandboxed parsing -> Fireworks extraction -> rule engine
services/intake/     voice intake: fixed-order questions, deterministic parsing, booking
services/priorauth/  PA packet drafting with enforced source_refs
services/ivr/        mock payer IVR state machine + agent navigation
evals/               Braintrust-ready triage accuracy + red-team safety datasets
data/synthetic/      seed referrals, incl. the 42-year-old demo case
apps/web/            Next.js + Tailwind frontend (nurse worklist, PA approval, dashboard)
tests/               pytest, incl. the hypothesis monotonicity property test
```

## Tech stack

Backend: Python 3.11+, FastAPI, Pydantic v2, SQLite via SQLAlchemy.
Frontend: Next.js 16 (App Router) + Tailwind.
Inference: Fireworks. Voice: ElevenLabs. Sandboxing: Daytona. Evals: Braintrust.
Tests: pytest + hypothesis.

> **No API keys are required to run the demo.** Fireworks, ElevenLabs, Daytona,
> and Braintrust are all optional — every integration degrades safely when its
> key is absent (e.g. a referral with no LLM key routes to `ESCALATE` for a
> human instead of guessing). The seeded synthetic data drives the full UI
> without any of them.

## API keys (optional — for the live pipeline)

Create a `.env` file in the repo root (it's git-ignored, and the backend loads it
automatically at startup via `app/env.py` — no `export` needed; real shell
environment variables always win over `.env` values):

```
FIREWORKS_API_KEY=...    # live LLM extraction of uploaded referrals + PA prose
DAYTONA_API_KEY=...      # real sandboxed document parsing (🔒 badge in the worklist)
ELEVENLABS_API_KEY=...   # voice for intake + payer IVR calls
BRAINTRUST_API_KEY=...   # uploads eval runs to Braintrust (project "meridian")
```

What each key unlocks, and what happens without it:

| Key | With it | Without it |
|---|---|---|
| Fireworks | Uploaded referral text is extracted into structured features | Upload routes to `ESCALATE` for human review (seeded demo cases still work — they carry known features) |
| Daytona | Documents are decoded in an isolated sandbox; provenance (`sandbox_id`, duration) is logged and badged | Parsing is refused and the referral escalates — it never falls back to parsing untrusted files in-process |
| ElevenLabs | Audible voice calls | Text-transcript simulation of the same call flow |
| Braintrust | `python -m evals.run` also logs experiments remotely | Evals still run and write `data/evals_summary.json` locally |

Tuning knobs (all optional, sane defaults): `FIREWORKS_MODEL` (default
`accounts/fireworks/models/deepseek-v4-pro`), `FIREWORKS_TIMEOUT_S` (60),
`FIREWORKS_MAX_TOKENS` (8192 — reasoning models spend tokens thinking before they
answer), `DAYTONA_SANDBOX_TIMEOUT_S` (60), `DAYTONA_SANDBOX_CREATE_TIMEOUT_S` (180),
`MERIDIAN_DB_URL` (defaults to SQLite at `./meridian.db`).

## Running it (step by step)

The app is two processes: a **Python backend** (the API + rule engine) and a
**Next.js frontend** (the dashboard). You run each in its own terminal and
leave both running. **Start the backend first** — the frontend reads from it.

### Prerequisites

- **Python 3.11+** (`python3 --version`)
- **Node.js 20+** and npm (`node --version`)
- macOS or Linux (Windows works via WSL)

### Terminal 1 — backend (start this first)

```bash
# from the repo root
python3 -m venv .venv                        # first time only
.venv/bin/pip install -r requirements.txt    # first time only

.venv/bin/python -m app.seed                 # load synthetic referrals + verdicts into the DB
.venv/bin/python -m evals.run                # compute the dashboard's eval numbers

.venv/bin/python -m app.main                 # start the API on http://localhost:8000  — LEAVE RUNNING
```

Leave this terminal running. Verify it's up: open <http://localhost:8000/health>
in a browser — you should see `{"status":"ok","demo_mode":true}`.

Optional: create a `.env` file with API keys (see [API keys](#api-keys-optional--for-the-live-pipeline)
above) **only** if you want live LLM extraction / voice / sandboxed parsing. The
demo works without it.

### Terminal 2 — frontend

```bash
cd apps/web
npm install                                  # first time only
cp .env.local.example .env.local             # first time only (defaults to localhost:8000)

npm run build && npm start                   # start the UI on http://localhost:3000  — LEAVE RUNNING
```

Then open <http://localhost:3000/worklist>. During active development you can
use `npm run dev` instead of `build && start` for hot reload.

### What you should see

- **`/worklist`** — the nurse worklist: 15 seeded patients including the
  42-year-old "probable hemorrhoids" demo case, each with its urgency, the
  rules that fired, and the source snippet behind every extracted feature.
  Approve/escalate requires typing an actor name (humans sign everything).
  Referrals parsed in a live Daytona sandbox carry a 🔒 badge; referrals whose
  pipeline failed show an amber **"not assessed"** badge instead of a
  misleading urgency (they were never evaluated — a human must look).
- **`/pa-packets`** — prior-auth packets; every sentence links to its source.
  Physician approve, then submit, then "call" the mock payer IVR.
- **`/dashboard`** — the eval metrics (escalation recall 100%, false
  reassurance 0%) plus the red-team output-safety numbers.

A persistent **"DEMO — synthetic data. Not for clinical use."** banner sits on
every page and is intentionally not dismissible.

### Verify everything works (optional)

```bash
.venv/bin/python -m pytest -q     # full backend test suite (rules, filters, pipelines, IVR, intake)
cd apps/web && npm run build      # confirms the frontend compiles clean
```

### Public tunnel (only if hosting the frontend remotely)

```bash
cloudflared tunnel --url http://localhost:8000
# → set NEXT_PUBLIC_API_URL to the printed https URL
```

## Troubleshooting

**The worklist loads but is empty.** The backend isn't running, or wasn't
seeded. In Terminal 1, confirm <http://localhost:8000/health> responds, and
that you ran `python -m app.seed`. Check what's listening: `lsof -iTCP:8000 -sTCP:LISTEN`.

**The dashboard says "no evals run yet."** Run `.venv/bin/python -m evals.run`
in Terminal 1 (it writes `data/evals_summary.json`), then reload.

**Frontend requests fail silently in the browser (but curl works).** That's
CORS — the backend only allows `http://localhost:3000` and the Vercel origins.
Run the frontend on port 3000 (the default), not another port.

**`npm audit` reports vulnerabilities.** They're transitive dependencies of
build tooling and are not reachable in this demo. **Do not run
`npm audit fix --force`** — it downgrades Next.js and breaks the app. The
`overrides` block in `apps/web/package.json` already pins the fixable ones.

**You changed frontend code but don't see it.** `npm start` serves a build.
Stop it (`Ctrl+C`) and re-run `npm run build && npm start`, then hard-refresh
the browser (`Cmd/Ctrl+Shift+R`).

## A note on the frontend (no CopilotKit)

The frontend was originally scaffolded with CopilotKit, but nothing in the app
was ever wired to it — no chat, no `useCopilotReadable`, no actions. With no
LLM adapter provisioned, the only thing the CopilotKit provider did was a
runtime/agent-discovery handshake against an adapter-less route, which threw
`CopilotApiDiscoveryError` and broke page rendering ("This page couldn't
load"). Since it added no function and broke the app, it was removed from the
render path — the frontend is now plain Next.js + Tailwind talking to the
backend over `fetch`. `src/components/Providers.tsx` and
`src/app/api/copilotkit/route.ts` document how to reinstate a real copilot
(with an LLM adapter) if you want one later.

## Deployment (Vercel)

The Next.js dashboard deploys to Vercel; the FastAPI backend does not (SQLite needs
persistent disk — run it on a laptop behind a `cloudflared` tunnel, or on Railway/Render).

Deploy from the **repo root** — the root `vercel.json` points the build at `apps/web`,
so there's no need to `cd` in:

```bash
npx vercel login     # one-time, interactive
npx vercel link      # link the repo root to a Vercel project (once)
npx vercel --prod    # deploy; prints the production URL
```

Set these in the Vercel dashboard (Settings → Environment Variables), never in a
committed file:

```
NEXT_PUBLIC_API_URL=https://<tunnel-or-backend-host>
NEXT_PUBLIC_DEMO_MODE=true
```

`NEXT_PUBLIC_*` is client-visible — **no Fireworks / ElevenLabs / Braintrust / Daytona
keys with that prefix, ever.** Those stay server-side on the backend.

> **Live URL:** _pending first deploy — replace with the `vercel --prod` output._

## Demo path

1. Patient voice call -> red flags elicited -> urgent slot booked live (`POST /intake/call`)
2. Faxed referral, 42yo, "probable hemorrhoids" -> agent flags urgent -> nurse approves
   (`POST /referrals` upload, worklist UI, `POST /referrals/{id}/verdicts/{id}/approve`)
3. PA packet drafted, criteria linked to evidence -> physician one-click approves
   (`POST /pa-packets`, `POST /pa-packets/{id}/approve`)
4. Agent dials mock IVR -> navigates tree -> status retrieved -> dashboard flips to approved
   (`POST /pa-packets/{id}/submit`, `POST /pa-packets/{id}/call-ivr`)

## Why Daytona

Scanned referrals are attacker-controlled input, and PDF/OCR toolchains have a long
history of RCE. Document decoding/OCR runs inside a throwaway Daytona sandbox
(`services/referral/sandbox.py`); only plain text crosses back into the API process.

## Invariants (enforced in code, not prompts)

- **Escalate-only urgency** — the system may raise urgency, never lower it (property-tested).
- **No diagnostic language** — a fail-closed output filter blocks condition names,
  probabilities, and reassurance on every patient-facing string and document.
- **Fail-safe defaults** — low confidence, timeouts, unparseable docs, or any unhandled
  exception all route to `ESCALATE`. No code path auto-clears a patient.
- **Humans sign everything** — nurse approves every triage verdict, physician approves
  every PA packet, recorded with actor, timestamp, and a hash of what was approved.
- **Every clinical claim traces to a source** — a PA sentence with no `source_ref` does
  not render.
- **Synthetic data only** — the "DEMO — synthetic data" banner stays, including in screenshots.

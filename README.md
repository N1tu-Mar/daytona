# Scoped

An agent that moves a patient from "something's wrong" to a booked colonoscopy with
prior authorization approved. It never diagnoses — it decides exactly one thing: does
this person need a GI appointment, and how fast. See `CLAUDE.md` for the full spec and
the non-negotiable invariants this codebase enforces in code, not prompts.

**DEMO — synthetic data. Not for clinical use.**

## Layout

```
app/                  schemas, monotonic urgency, rule engine, output filter, DB, FastAPI app
services/referral/     Daytona-sandboxed parsing -> Fireworks extraction -> rule engine
services/intake/        voice intake: fixed-order questions, deterministic parsing, booking
services/priorauth/    PA packet drafting with enforced source_refs
services/ivr/          mock payer IVR state machine + agent navigation
evals/                 Braintrust-ready triage accuracy + red-team safety datasets
data/synthetic/         seed referrals, incl. the 42-year-old demo case
apps/web/                Next.js + CopilotKit frontend (nurse worklist, PA approval, dashboard)
tests/                  pytest, incl. the hypothesis monotonicity property test
```

## Backend

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # fill in keys if you have them; every integration degrades safely without one

.venv/bin/python -m app.seed        # seed synthetic referrals + verdicts
.venv/bin/python -m evals.run       # run both eval datasets, writes data/evals_summary.json
.venv/bin/python -m pytest -q       # full test suite

.venv/bin/python -m app.main        # run the API on :8000 (or: uvicorn app.main:app --reload)
```

Public tunnel for the frontend to reach a local backend:

```bash
cloudflared tunnel --url http://localhost:8000
```

## Frontend

```bash
cd apps/web
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL to your backend
npm run dev
```

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

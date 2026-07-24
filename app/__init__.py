"""Meridian backend package. Importing it loads .env (see app/env.py) so every
entry point — uvicorn, seeds, evals — sees the same API keys."""

from app import env as _env  # noqa: F401  (side effect: load .env)

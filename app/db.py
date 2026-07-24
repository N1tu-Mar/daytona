"""SQLite via SQLAlchemy. Upgrade path to Postgres exists but isn't built here.

Tables mirror the Pydantic schemas closely. TriageVerdict rows are
append-only at the application layer (app/rule_engine.py + app/routes never
UPDATE a verdict; corrections INSERT a new row with corrects_verdict_id set).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    create_engine,
    inspect as sa_inspect,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

# Repo-root-anchored default so the DB is the same file no matter which
# working directory the backend is launched from. A relative "./meridian.db"
# resolves against the process CWD, which lets a uvicorn --reload restart
# create a stray empty DB if it fires from the wrong directory.
_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "meridian.db"

# Overridable so tests (and any throwaway environment) can point at an
# isolated DB instead of the demo's meridian.db. See tests/conftest.py.
DATABASE_URL = os.environ.get("MERIDIAN_DB_URL", f"sqlite:///{_DEFAULT_DB_PATH}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class ReferralRecord(Base):
    __tablename__ = "referrals"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String)  # "fax_scan" | "voice_call" | "synthetic"
    raw_text: Mapped[str] = mapped_column(String, default="")
    patient_name: Mapped[str] = mapped_column(String, default="")  # synthetic only
    features_json: Mapped[str] = mapped_column(String)  # ReferralFeatures.model_dump_json()
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Daytona sandbox provenance: auditable evidence the document was decoded
    # in an isolated sandbox. Null/False for synthetic seed data and for the
    # unsandboxed local-decode fallback (no DAYTONA_API_KEY).
    sandbox_id: Mapped[str | None] = mapped_column(String, nullable=True)
    sandbox_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sandboxed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    # Which OS decoded the document: "snapshot:meridian-parse:1", "image:<ref>",
    # or "declarative-build". Null for synthetic seed data and the local
    # fallback. The auditable "what parsed this", pinnable like rule_version.
    sandbox_source: Mapped[str | None] = mapped_column(String, nullable=True)


class TriageVerdictRecord(Base):
    __tablename__ = "triage_verdicts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    referral_id: Mapped[str] = mapped_column(String, ForeignKey("referrals.id"))
    urgency: Mapped[str] = mapped_column(String)
    disposition: Mapped[str] = mapped_column(String)
    rules_fired: Mapped[list] = mapped_column(JSON, default=list)
    rule_version: Mapped[str] = mapped_column(String)
    missing_features: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    corrects_verdict_id: Mapped[str | None] = mapped_column(String, nullable=True)

    approved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approval_hash: Mapped[str | None] = mapped_column(String, nullable=True)

    # booking confirmation, only set after nurse approval
    booked_slot: Mapped[str | None] = mapped_column(String, nullable=True)


class PAPacketRecord(Base):
    __tablename__ = "pa_packets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    referral_id: Mapped[str] = mapped_column(String, ForeignKey("referrals.id"))
    verdict_id: Mapped[str] = mapped_column(String, ForeignKey("triage_verdicts.id"))
    sentences_json: Mapped[str] = mapped_column(String)  # list[PASentence] as json
    status: Mapped[str] = mapped_column(String, default="drafted")  # drafted|approved|submitted|ivr_pending|approved_by_payer|denied
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    approved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approval_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    payer_status: Mapped[str | None] = mapped_column(String, nullable=True)
    days_saved: Mapped[int | None] = mapped_column(Integer, nullable=True)


def init_db() -> None:
    Base.metadata.create_all(engine)
    _migrate_referral_sandbox_columns()


def _migrate_referral_sandbox_columns() -> None:
    """Additive, idempotent migration for the sandbox-provenance columns.

    create_all() never ALTERs an existing table, so a meridian.db created before
    these columns existed would be missing them. Add them in place rather than
    forcing a manual DB reset — safe to run on every startup.
    """
    insp = sa_inspect(engine)
    if "referrals" not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns("referrals")}
    additions = {
        "sandbox_id": "ALTER TABLE referrals ADD COLUMN sandbox_id VARCHAR",
        "sandbox_ms": "ALTER TABLE referrals ADD COLUMN sandbox_ms INTEGER",
        "sandboxed": "ALTER TABLE referrals ADD COLUMN sandboxed BOOLEAN NOT NULL DEFAULT 0",
        "sandbox_source": "ALTER TABLE referrals ADD COLUMN sandbox_source VARCHAR",
    }
    with engine.begin() as conn:
        for col, ddl in additions.items():
            if col not in existing:
                conn.execute(text(ddl))


def get_session() -> Session:
    return SessionLocal()

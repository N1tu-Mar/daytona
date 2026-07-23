"""SQLite via SQLAlchemy. Upgrade path to Postgres exists but isn't built here.

Tables mirror the Pydantic schemas closely. TriageVerdict rows are
append-only at the application layer (app/rule_engine.py + app/routes never
UPDATE a verdict; corrections INSERT a new row with corrects_verdict_id set).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATABASE_URL = "sqlite:///./scoped.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


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


def get_session() -> Session:
    return SessionLocal()

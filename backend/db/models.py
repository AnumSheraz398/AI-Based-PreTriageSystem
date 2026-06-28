"""
Database setup — SQLAlchemy async with PostgreSQL.
Tables:
  - patient_sessions  : every patient that goes through the system
  - audit_log         : every decision, override, and consent event
"""

import os
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime,
    Text, Float, JSON, ForeignKey, Enum as SAEnum
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import enum


# ── Connection ─────────────────────────────────────────────────────────────────
def get_database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/pretriage"
    )


engine = None
AsyncSessionLocal = None


async def init_db():
    """Initialize database engine and create all tables."""
    global engine, AsyncSessionLocal

    db_url = get_database_url()
    engine = create_async_engine(
        db_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
    )
    AsyncSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return engine


async def get_session() -> AsyncSession:
    """Dependency — get a database session."""
    async with AsyncSessionLocal() as session:
        yield session


def now_utc():
    return datetime.now(timezone.utc)


# ── Base ───────────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Enums ──────────────────────────────────────────────────────────────────────
class TriageStatus(str, enum.Enum):
    pending   = "pending"       # Just arrived, not yet confirmed by nurse
    confirmed = "confirmed"     # Nurse confirmed AI decision
    overridden = "overridden"   # Nurse changed the AI level
    seen      = "seen"          # Patient has been seen
    escalated = "escalated"     # Escalated to higher urgency


class ConsentStatus(str, enum.Enum):
    granted = "granted"
    declined = "declined"


# ── Patient session table ──────────────────────────────────────────────────────
class PatientSession(Base):
    __tablename__ = "patient_sessions"

    # Identity
    id              = Column(String(36), primary_key=True)   # session_id (UUID)
    token_number    = Column(String(20), nullable=False)      # AE-001, GOPD-042

    # Intake data
    chief_complaint = Column(Text, nullable=False)
    age_group       = Column(String(20))
    sex             = Column(String(30))
    duration        = Column(String(200))
    language        = Column(String(5), default="ur")
    red_flag_symptoms = Column(JSON)                          # list of strings

    # Consent
    consent_status  = Column(SAEnum(ConsentStatus), default=ConsentStatus.granted)
    consented_at    = Column(DateTime(timezone=True))

    # Triage result
    triage_level    = Column(Integer)                         # 1-5
    triage_level_name = Column(String(30))
    confidence      = Column(Integer)
    safety_rule_fired = Column(Boolean, default=False)
    safety_rule_name  = Column(String(100))
    triage_reasoning  = Column(Text)

    # Routing
    department_code   = Column(String(10))                    # AE, EOPD, GOPD
    department_name   = Column(String(100))
    wait_mins         = Column(Integer)
    patient_message_ur = Column(Text)
    patient_message_en = Column(Text)

    # Status
    status          = Column(SAEnum(TriageStatus), default=TriageStatus.pending)
    escalate_now    = Column(Boolean, default=False)
    requires_review = Column(Boolean, default=False)

    # Override (if nurse changed the level)
    override_level  = Column(Integer)
    override_reason = Column(Text)
    overridden_by   = Column(String(100))
    overridden_at   = Column(DateTime(timezone=True))

    # Timestamps
    created_at      = Column(DateTime(timezone=True), default=now_utc)
    updated_at      = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    seen_at         = Column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        """Convert to dict for WebSocket / API response."""
        return {
            "id":                  self.id,
            "token_number":        self.token_number,
            "chief_complaint":     self.chief_complaint,
            "age_group":           self.age_group,
            "sex":                 self.sex,
            "duration":            self.duration,
            "language":            self.language,
            "red_flag_symptoms":   self.red_flag_symptoms or [],
            "consent_status":      self.consent_status,
            "triage_level":        self.triage_level,
            "triage_level_name":   self.triage_level_name,
            "confidence":          self.confidence,
            "safety_rule_fired":   self.safety_rule_fired,
            "safety_rule_name":    self.safety_rule_name,
            "triage_reasoning":    self.triage_reasoning,
            "department_code":     self.department_code,
            "department_name":     self.department_name,
            "wait_mins":           self.wait_mins,
            "patient_message_ur":  self.patient_message_ur,
            "patient_message_en":  self.patient_message_en,
            "status":              self.status,
            "escalate_now":        self.escalate_now,
            "requires_review":     self.requires_review,
            "override_level":      self.override_level,
            "override_reason":     self.override_reason,
            "overridden_by":       self.overridden_by,
            "overridden_at":       self.overridden_at.isoformat() if self.overridden_at else None,
            "created_at":          self.created_at.isoformat() if self.created_at else None,
            "seen_at":             self.seen_at.isoformat() if self.seen_at else None,
            # Computed: minutes waiting
            "waiting_since_mins":  self._waiting_mins(),
        }

    def _waiting_mins(self) -> int:
        if not self.created_at:
            return 0
        delta = now_utc() - self.created_at
        return int(delta.total_seconds() / 60)


# ── Audit log table ────────────────────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_log"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    session_id  = Column(String(36), ForeignKey("patient_sessions.id"), nullable=True)
    event_type  = Column(String(50), nullable=False)   # intake, triage, consent, override, seen
    actor       = Column(String(100))                   # "patient", "ai", "nurse:Dr.Khan"
    details     = Column(JSON)                          # flexible event details
    created_at  = Column(DateTime(timezone=True), default=now_utc)

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "actor":      self.actor,
            "details":    self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
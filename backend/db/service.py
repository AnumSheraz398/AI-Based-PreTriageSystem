"""
Database service — all database operations in one place.
Routers call these functions instead of touching SQLAlchemy directly.
"""

import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from db.models import PatientSession, AuditLog, TriageStatus, ConsentStatus

logger = logging.getLogger(__name__)


def now_utc():
    return datetime.now(timezone.utc)


# ── Patient session operations ─────────────────────────────────────────────────

async def save_patient_session(
    db: AsyncSession,
    route_result: dict,
    triage_result: dict,
    canonical: dict,
) -> PatientSession:
    """
    Save a completed patient session to the database.
    Called after POST /route completes successfully.
    """
    session = PatientSession(
        id                 = canonical.get("session_id"),
        token_number       = route_result.get("token_number"),
        chief_complaint    = canonical.get("chief_complaint"),
        age_group          = canonical.get("age_group"),
        sex                = canonical.get("sex"),
        duration           = canonical.get("duration"),
        language           = canonical.get("language", "ur"),
        red_flag_symptoms  = canonical.get("red_flag_symptoms"),
        consent_status     = ConsentStatus.granted,
        consented_at       = now_utc(),
        triage_level       = route_result.get("level"),
        triage_level_name  = route_result.get("level_name"),
        confidence         = route_result.get("confidence"),
        safety_rule_fired  = route_result.get("safety_rule_fired", False),
        safety_rule_name   = route_result.get("safety_rule_name"),
        triage_reasoning   = route_result.get("staff_summary"),
        department_code    = route_result.get("department_code"),
        department_name    = route_result.get("department_name_en"),
        wait_mins          = route_result.get("wait_mins"),
        patient_message_ur = route_result.get("patient_message_ur"),
        patient_message_en = route_result.get("patient_message_en"),
        escalate_now       = route_result.get("escalate_now", False),
        requires_review    = route_result.get("requires_review", False),
        status             = TriageStatus.pending,
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Log to audit
    await log_event(db, session.id, "triage_complete", "ai", {
        "level":        session.triage_level,
        "confidence":   session.confidence,
        "department":   session.department_code,
        "safety_rule":  session.safety_rule_name,
    })

    logger.info(f"Patient saved | id={session.id} | token={session.token_number} | level={session.triage_level}")
    return session


async def get_active_queue(db: AsyncSession) -> list[PatientSession]:
    """
    Get all patients who haven't been seen yet, sorted by urgency level.
    Level 1 first, Level 5 last. Within same level, FIFO (oldest first).
    """
    result = await db.execute(
        select(PatientSession)
        .where(PatientSession.status.notin_([TriageStatus.seen]))
        .order_by(
            PatientSession.triage_level.asc(),    # most urgent first
            PatientSession.created_at.asc(),       # then by arrival time
        )
    )
    return result.scalars().all()


async def get_session_by_id(db: AsyncSession, session_id: str) -> PatientSession | None:
    """Get a single patient session by ID."""
    result = await db.execute(
        select(PatientSession).where(PatientSession.id == session_id)
    )
    return result.scalar_one_or_none()


async def override_triage_level(
    db: AsyncSession,
    session_id: str,
    new_level: int,
    reason: str,
    nurse_id: str = "nurse",
) -> PatientSession | None:
    """
    Nurse overrides the AI triage level.
    Records the original level, new level, reason, and who did it.
    """
    session = await get_session_by_id(db, session_id)
    if not session:
        return None

    original_level = session.triage_level
    session.override_level  = new_level
    session.override_reason = reason
    session.overridden_by   = nurse_id
    session.overridden_at   = now_utc()
    session.status          = TriageStatus.overridden
    session.triage_level    = new_level    # update displayed level
    session.updated_at      = now_utc()

    await db.commit()
    await db.refresh(session)

    # Audit log
    await log_event(db, session_id, "override", f"nurse:{nurse_id}", {
        "original_level": original_level,
        "new_level":      new_level,
        "reason":         reason,
    })

    logger.info(f"Override | session={session_id} | {original_level}→{new_level} | by={nurse_id}")
    return session


async def mark_patient_seen(
    db: AsyncSession,
    session_id: str,
    nurse_id: str = "nurse",
) -> PatientSession | None:
    """Mark a patient as seen by a nurse."""
    session = await get_session_by_id(db, session_id)
    if not session:
        return None

    session.status   = TriageStatus.seen
    session.seen_at  = now_utc()
    session.updated_at = now_utc()

    await db.commit()
    await db.refresh(session)

    await log_event(db, session_id, "marked_seen", f"nurse:{nurse_id}", {})
    logger.info(f"Marked seen | session={session_id}")
    return session


# ── Audit log operations ───────────────────────────────────────────────────────

async def log_event(
    db: AsyncSession,
    session_id: str | None,
    event_type: str,
    actor: str,
    details: dict,
):
    """Write an event to the audit log."""
    entry = AuditLog(
        session_id = session_id,
        event_type = event_type,
        actor      = actor,
        details    = details,
    )
    db.add(entry)
    await db.commit()


async def get_audit_log(
    db: AsyncSession,
    limit: int = 200,
    session_id: str | None = None,
) -> list[AuditLog]:
    """Get audit log entries, most recent first."""
    query = select(AuditLog)
    if session_id:
        query = query.where(AuditLog.session_id == session_id)
    query = query.order_by(desc(AuditLog.created_at)).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


# ── Stats ──────────────────────────────────────────────────────────────────────

async def get_queue_stats(db: AsyncSession) -> dict:
    """Quick stats for dashboard header."""
    total = await db.scalar(
        select(func.count()).where(PatientSession.status.notin_([TriageStatus.seen]))
    )
    critical = await db.scalar(
        select(func.count()).where(
            PatientSession.triage_level.in_([1, 2]),
            PatientSession.status.notin_([TriageStatus.seen]),
        )
    )
    return {
        "total_waiting": total or 0,
        "critical_count": critical or 0,
    }
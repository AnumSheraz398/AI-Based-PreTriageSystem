"""
Dashboard router — all endpoints the staff dashboard needs.

Endpoints:
  GET  /dashboard/queue           — full active patient queue
  GET  /dashboard/stats           — header stats (total, critical count)
  POST /dashboard/override        — nurse overrides AI triage level
  POST /dashboard/seen/{id}       — nurse marks patient as seen
  GET  /dashboard/audit           — audit log (admin only)
  GET  /dashboard/audit/export    — download audit log as CSV
  WS   /dashboard/ws              — WebSocket for real-time updates
"""

import csv
import io
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import get_session
from db.service import (
    get_active_queue, override_triage_level,
    mark_patient_seen, get_audit_log, get_queue_stats
)
from db.websocket_manager import ws_manager

router = APIRouter(prefix="/dashboard", tags=["Staff Dashboard"])
logger = logging.getLogger(__name__)


# ── Request models ────────────────────────────────────────────────────────────
class OverrideRequest(BaseModel):
    session_id: str
    new_level:  int
    reason:     str
    nurse_id:   str = "nurse"


# ── Queue endpoints ───────────────────────────────────────────────────────────
@router.get("/queue", summary="Get full active patient queue sorted by urgency")
async def get_queue(db: AsyncSession = Depends(get_session)):
    """
    Returns all patients who haven't been marked as seen,
    sorted by urgency level (Level 1 first) then arrival time.
    This is what the staff dashboard table shows.
    """
    patients = await get_active_queue(db)
    return {
        "patients": [p.to_dict() for p in patients],
        "count":    len(patients),
    }


@router.get("/stats", summary="Queue header stats")
async def queue_stats(db: AsyncSession = Depends(get_session)):
    """Returns total waiting and critical (Level 1-2) count for dashboard header."""
    return await get_queue_stats(db)


# ── Nurse actions ─────────────────────────────────────────────────────────────
@router.post("/override", summary="Nurse overrides AI triage level")
async def override(
    request: OverrideRequest,
    db: AsyncSession = Depends(get_session),
):
    """
    Nurse disagrees with AI decision and changes the triage level.
    - Records original level, new level, reason, and nurse ID
    - Broadcasts the updated patient to all dashboards via WebSocket
    - Writes to audit log

    All AI decisions are advisory — nurse override is always available.
    """
    if request.new_level not in [1, 2, 3, 4, 5]:
        return {"error": "new_level must be between 1 and 5"}

    updated = await override_triage_level(
        db,
        session_id = request.session_id,
        new_level  = request.new_level,
        reason     = request.reason,
        nurse_id   = request.nurse_id,
    )

    if not updated:
        return {"error": f"Session {request.session_id} not found"}

    # Broadcast updated patient to all dashboards
    await ws_manager.send_patient_update(updated.to_dict())

    return {
        "status":        "overridden",
        "session_id":    updated.id,
        "new_level":     updated.triage_level,
        "token_number":  updated.token_number,
    }


@router.post("/seen/{session_id}", summary="Mark patient as seen by nurse")
async def mark_seen(
    session_id: str,
    nurse_id: str = Query(default="nurse"),
    db: AsyncSession = Depends(get_session),
):
    """
    Mark a patient as seen — removes them from the active queue.
    Broadcasts the update to all connected dashboards.
    """
    updated = await mark_patient_seen(db, session_id, nurse_id)

    if not updated:
        return {"error": f"Session {session_id} not found"}

    # Broadcast — dashboards remove this patient from queue
    await ws_manager.send_patient_update(updated.to_dict())

    return {
        "status":       "seen",
        "session_id":   updated.id,
        "token_number": updated.token_number,
        "seen_at":      updated.seen_at.isoformat() if updated.seen_at else None,
    }


# ── Audit log ─────────────────────────────────────────────────────────────────
@router.get("/audit", summary="Get audit log (admin only)")
async def audit_log(
    limit:      int           = Query(default=100, le=500),
    session_id: Optional[str] = Query(default=None),
    db:         AsyncSession  = Depends(get_session),
):
    """
    Returns the audit log — every patient interaction, AI decision,
    override, and consent event. Filter by session_id if needed.
    Add authentication middleware in production.
    """
    entries = await get_audit_log(db, limit=limit, session_id=session_id)
    return {
        "entries": [e.to_dict() for e in entries],
        "count":   len(entries),
    }


@router.get("/audit/export", summary="Download audit log as CSV")
async def export_audit_csv(
    db: AsyncSession = Depends(get_session),
):
    """
    Download the full audit log as a CSV file.
    Used by hospital administrators for compliance reporting.
    """
    entries = await get_audit_log(db, limit=10000)

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["id", "session_id", "event_type", "actor", "details", "created_at"])

    # Rows
    for entry in entries:
        writer.writerow([
            entry.id,
            entry.session_id,
            entry.event_type,
            entry.actor,
            str(entry.details),
            entry.created_at.isoformat() if entry.created_at else "",
        ])

    output.seek(0)
    filename = f"audit_log_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── WebSocket ─────────────────────────────────────────────────────────────────
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time dashboard updates.

    Connect from the dashboard frontend:
      const ws = new WebSocket("ws://localhost:8000/dashboard/ws");

    Events you'll receive:
      { type: "new_patient",    data: { ...patient } }
      { type: "patient_update", data: { ...patient } }
      { type: "queue_refresh",  data: [ ...patients ] }
      { type: "level1_alert",   data: { token_number, chief_complaint, department } }

    On connect: sends the current queue immediately so dashboard loads fast.
    """
    await ws_manager.connect(websocket)
    logger.info(f"Dashboard WebSocket connected | total={ws_manager.connection_count}")

    # Send current queue immediately on connect
    try:
        async with websocket.app.state.db_session() as db:
            patients = await get_active_queue(db)
            await ws_manager.send_queue_refresh([p.to_dict() for p in patients])
    except Exception as e:
        logger.warning(f"Could not send initial queue: {e}")

    try:
        # Keep connection alive — receive pings from client
        while True:
            data = await websocket.receive_text()
            # Client can send { "type": "ping" } to keep connection alive
            if data == '{"type":"ping"}':
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info(f"Dashboard disconnected | total={ws_manager.connection_count}")
"""
WebSocket manager — broadcasts patient updates to all connected dashboards.

Every time a patient completes triage, all nurse dashboards receive
the new patient data in real time without polling.
"""

import json
import logging
from fastapi import WebSocket
from typing import Any

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages all active WebSocket connections from staff dashboards.
    When a new patient is triaged, broadcast() sends their data to
    every connected dashboard instantly.
    """

    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept a new dashboard connection."""
        await websocket.accept()
        self._connections.append(websocket)
        logger.info(f"Dashboard connected. Total connections: {len(self._connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected dashboard."""
        if websocket in self._connections:
            self._connections.remove(websocket)
        logger.info(f"Dashboard disconnected. Total connections: {len(self._connections)}")

    async def broadcast(self, event_type: str, data: Any):
        """
        Send a JSON event to ALL connected dashboards.

        event_type examples:
          "new_patient"    — a new patient just completed triage
          "patient_update" — nurse confirmed/overridden/marked seen
          "queue_refresh"  — full queue refresh (sent on reconnect)
          "level1_alert"   — Level 1 emergency detected
        """
        if not self._connections:
            return

        message = json.dumps({
            "type": event_type,
            "data": data,
        })

        # Send to all — remove broken connections
        dead = []
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.warning(f"WebSocket send failed: {e}")
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

    async def send_queue_refresh(self, patients: list[dict]):
        """Send the full current queue to all dashboards."""
        await self.broadcast("queue_refresh", patients)

    async def send_new_patient(self, patient: dict):
        """Notify all dashboards that a new patient has been triaged."""
        await self.broadcast("new_patient", patient)
        # If Level 1, send a separate urgent alert
        if patient.get("triage_level") == 1:
            await self.broadcast("level1_alert", {
                "token_number":    patient.get("token_number"),
                "chief_complaint": patient.get("chief_complaint"),
                "department":      patient.get("department_name"),
            })

    async def send_patient_update(self, patient: dict):
        """Notify all dashboards that a patient's status changed."""
        await self.broadcast("patient_update", patient)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


# Single shared instance — imported by routers
ws_manager = WebSocketManager()
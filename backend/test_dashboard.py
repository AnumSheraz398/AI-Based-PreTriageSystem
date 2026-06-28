"""
Tests for Phase 5 — database models, WebSocket manager, service structure.
Tests run without a real PostgreSQL connection (no DB needed).
Run with: python test_dashboard.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"
results = []

def test(name, condition):
    status = PASS if condition else FAIL
    print(f"{status} | {name}")
    results.append(condition)

print("\n── Database model tests ────────────────────────────────────────────")

from db.models import PatientSession, AuditLog, TriageStatus, ConsentStatus, Base

# Table names
test("PatientSession table name is correct",   PatientSession.__tablename__ == "patient_sessions")
test("AuditLog table name is correct",         AuditLog.__tablename__ == "audit_log")

# PatientSession columns exist
ps_cols = [c.name for c in PatientSession.__table__.columns]
for col in ["id","token_number","chief_complaint","age_group","sex","duration",
            "language","consent_status","triage_level","triage_level_name",
            "confidence","safety_rule_fired","department_code","department_name",
            "wait_mins","status","escalate_now","requires_review",
            "override_level","override_reason","created_at","seen_at"]:
    test(f"PatientSession has column: {col}", col in ps_cols)

# AuditLog columns exist
al_cols = [c.name for c in AuditLog.__table__.columns]
for col in ["id","session_id","event_type","actor","details","created_at"]:
    test(f"AuditLog has column: {col}", col in al_cols)

# Enums
test("TriageStatus has pending",    TriageStatus.pending    == "pending")
test("TriageStatus has confirmed",  TriageStatus.confirmed  == "confirmed")
test("TriageStatus has overridden", TriageStatus.overridden == "overridden")
test("TriageStatus has seen",       TriageStatus.seen       == "seen")
test("ConsentStatus has granted",   ConsentStatus.granted   == "granted")
test("ConsentStatus has declined",  ConsentStatus.declined  == "declined")

# to_dict method exists
test("PatientSession has to_dict()", hasattr(PatientSession, "to_dict"))
test("AuditLog has to_dict()",       hasattr(AuditLog, "to_dict"))

print("\n── PatientSession.to_dict() tests ─────────────────────────────────")

from datetime import datetime, timezone

ps = PatientSession(
    id                 = "test-session-001",
    token_number       = "AE-001",
    chief_complaint    = "chest pain",
    age_group          = "adult",
    sex                = "male",
    duration           = "2 hours",
    language           = "en",
    triage_level       = 2,
    triage_level_name  = "Emergent",
    confidence         = 92,
    safety_rule_fired  = True,
    safety_rule_name   = "cardiac_chest_pain",
    department_code    = "AE",
    department_name    = "Emergency — A&E",
    wait_mins          = 15,
    escalate_now       = False,
    requires_review    = False,
    status             = TriageStatus.pending,
    created_at         = datetime.now(timezone.utc),
)

d = ps.to_dict()
test("to_dict returns dict",              isinstance(d, dict))
test("to_dict has id",                    d["id"] == "test-session-001")
test("to_dict has token_number",          d["token_number"] == "AE-001")
test("to_dict has triage_level",          d["triage_level"] == 2)
test("to_dict has department_code",       d["department_code"] == "AE")
test("to_dict has safety_rule_fired",     d["safety_rule_fired"] == True)
test("to_dict has waiting_since_mins",    "waiting_since_mins" in d)
test("to_dict waiting_since_mins >= 0",   d["waiting_since_mins"] >= 0)
test("to_dict red_flag_symptoms default", d["red_flag_symptoms"] == [])

print("\n── AuditLog.to_dict() tests ────────────────────────────────────────")

al = AuditLog(
    session_id = "test-session-001",
    event_type = "triage_complete",
    actor      = "ai",
    details    = {"level": 2, "confidence": 92},
    created_at = datetime.now(timezone.utc),
)
ad = al.to_dict()
test("AuditLog to_dict returns dict",        isinstance(ad, dict))
test("AuditLog to_dict has session_id",      ad["session_id"] == "test-session-001")
test("AuditLog to_dict has event_type",      ad["event_type"] == "triage_complete")
test("AuditLog to_dict has actor",           ad["actor"] == "ai")
test("AuditLog to_dict has details dict",    isinstance(ad["details"], dict))
test("AuditLog to_dict details has level",   ad["details"]["level"] == 2)

print("\n── WebSocket manager tests ─────────────────────────────────────────")

import asyncio
from db.websocket_manager import WebSocketManager

mgr = WebSocketManager()
test("WebSocket manager starts with 0 connections", mgr.connection_count == 0)

# Test disconnect of non-existent connection doesn't crash
class MockWS:
    async def accept(self): pass
    async def send_text(self, text): self.last_sent = text
    async def receive_text(self): return '{"type":"ping"}'

async def test_ws():
    ws1 = MockWS()
    ws2 = MockWS()
    mgr2 = WebSocketManager()

    await mgr2.connect(ws1)
    await mgr2.connect(ws2)
    assert mgr2.connection_count == 2, "Should have 2 connections"

    mgr2.disconnect(ws1)
    assert mgr2.connection_count == 1, "Should have 1 connection after disconnect"

    # broadcast
    await mgr2.broadcast("new_patient", {"token": "AE-001", "level": 2})
    import json
    msg = json.loads(ws2.last_sent)
    assert msg["type"] == "new_patient"
    assert msg["data"]["token"] == "AE-001"

    mgr2.disconnect(ws2)
    assert mgr2.connection_count == 0

asyncio.run(test_ws())
test("WebSocket connect/disconnect works",      True)
test("WebSocket broadcast sends correct JSON",  True)
test("WebSocket connection count is accurate",  True)

print("\n── Dashboard router structure tests ────────────────────────────────")

from routers.dashboard import router as dashboard_router

routes = {r.path: r for r in dashboard_router.routes}
test("GET  /dashboard/queue exists",        "/dashboard/queue"         in routes)
test("GET  /dashboard/stats exists",        "/dashboard/stats"         in routes)
test("POST /dashboard/override exists",     "/dashboard/override"      in routes)
test("GET  /dashboard/audit exists",        "/dashboard/audit"         in routes)
test("GET  /dashboard/audit/export exists", "/dashboard/audit/export"  in routes)

# WebSocket route
ws_routes = [r for r in dashboard_router.routes if hasattr(r, "path") and "ws" in r.path]
test("WebSocket /dashboard/ws route exists", len(ws_routes) > 0)

print("\n── Results ─────────────────────────────────────────────────────────")
total, passed = len(results), sum(results)
print(f"\n── Results: {passed}/{total} passed ───────────────────────────────────\n")
if all(results):
    print("\033[92mAll Phase 5 tests passed! Dashboard module complete.\033[0m\n")
    sys.exit(0)
else:
    print("\033[91mSome tests failed.\033[0m\n")
    sys.exit(1)
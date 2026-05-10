"""
Tests for Phase 4 — routing service.
Tests department config, token generation, and staff summary (no OpenAI calls).
Run with: python test_routing.py
"""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.routing import (
    DEPARTMENT_CONFIG, _next_token, _build_staff_summary,
    _token_counters, RouteResult
)
from services.triage_agent import TriageResult

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"
results = []

def test(name, condition):
    status = PASS if condition else FAIL
    print(f"{status} | {name}")
    results.append(condition)

def make_triage(level, confidence=85, rule_fired=False, rule_name=None):
    return TriageResult(
        session_id        = "test-session",
        level             = level,
        level_name        = {1:"Resuscitation",2:"Emergent",3:"Urgent",
                             4:"Less Urgent",5:"Non-urgent"}[level],
        confidence        = confidence,
        reasoning         = "Test reasoning for nurse.",
        patient_message   = "Test patient message.",
        patient_message_ur= "ٹیسٹ پیغام۔",
        department        = "Test department",
        safety_rule_fired = rule_fired,
        safety_rule_name  = rule_name,
        escalate_now      = level == 1,
        rag_chunks_used   = [],
        requires_review   = confidence < 70,
    )

print("\n── Department config tests ─────────────────────────────────────────")

# All 5 levels have complete config
for level in [1, 2, 3, 4, 5]:
    cfg = DEPARTMENT_CONFIG[level]
    test(f"Level {level} has department code",    bool(cfg.get("code")))
    test(f"Level {level} has English name",       bool(cfg.get("name_en")))
    test(f"Level {level} has Urdu name",          bool(cfg.get("name_ur")))
    test(f"Level {level} has English location",   bool(cfg.get("location_en")))
    test(f"Level {level} has Urdu location",      bool(cfg.get("location_ur")))
    test(f"Level {level} has wait_mins",          cfg.get("wait_mins") is not None)
    test(f"Level {level} has color",              bool(cfg.get("color")))

# Correct department assignments
test("Level 1 -> A&E",       DEPARTMENT_CONFIG[1]["code"] == "AE")
test("Level 2 -> A&E",       DEPARTMENT_CONFIG[2]["code"] == "AE")
test("Level 3 -> EOPD",      DEPARTMENT_CONFIG[3]["code"] == "EOPD")
test("Level 4 -> GOPD",      DEPARTMENT_CONFIG[4]["code"] == "GOPD")
test("Level 5 -> GOPD",      DEPARTMENT_CONFIG[5]["code"] == "GOPD")

# Wait times in correct order (most urgent = shortest wait)
test("Level 1 wait = 0 min",    DEPARTMENT_CONFIG[1]["wait_mins"] == 0)
test("Level 2 wait = 15 min",   DEPARTMENT_CONFIG[2]["wait_mins"] == 15)
test("Level 3 wait = 30 min",   DEPARTMENT_CONFIG[3]["wait_mins"] == 30)
test("Level 4 wait = 60 min",   DEPARTMENT_CONFIG[4]["wait_mins"] == 60)
test("Level 5 wait = 120 min",  DEPARTMENT_CONFIG[5]["wait_mins"] == 120)

# Colors — Level 1 should be red
test("Level 1 color is red (#FF3B3B)", DEPARTMENT_CONFIG[1]["color"] == "#FF3B3B")
test("Level 5 color is light blue",    DEPARTMENT_CONFIG[5]["color"] == "#90CAF9")

# Urdu in location strings
for level in [1, 2, 3, 4, 5]:
    ur_text = DEPARTMENT_CONFIG[level]["location_ur"]
    has_urdu = any(ord(c) > 1536 for c in ur_text)
    test(f"Level {level} Urdu location has Urdu script", has_urdu)

print("\n── Token generation tests ──────────────────────────────────────────")

# Reset counters for clean test
_token_counters.clear()

t1 = _next_token("AE")
test("First AE token is AE-001",   t1 == "AE-001")
t2 = _next_token("AE")
test("Second AE token is AE-002",  t2 == "AE-002")
t3 = _next_token("GOPD")
test("First GOPD token is GOPD-001", t3 == "GOPD-001")
t4 = _next_token("EOPD")
test("First EOPD token is EOPD-001", t4 == "EOPD-001")
t5 = _next_token("GOPD")
test("Second GOPD token is GOPD-002", t5 == "GOPD-002")

# Token format check
test("Token format has dash",       "-" in t1)
test("Token prefix matches dept",   t1.startswith("AE"))

print("\n── Staff summary tests ─────────────────────────────────────────────")

# Normal case
tr_normal = make_triage(level=3, confidence=85)
summary = _build_staff_summary(tr_normal, "EOPD-001")
test("Summary contains token",        "EOPD-001" in summary)
test("Summary contains level",        "LEVEL 3" in summary)
test("Summary contains confidence",   "85%" in summary)
test("Summary contains reasoning",    "Test reasoning" in summary)

# Safety rule fired
tr_rule = make_triage(level=2, confidence=95, rule_fired=True, rule_name="cardiac_chest_pain")
summary_rule = _build_staff_summary(tr_rule, "AE-001")
test("Summary flags safety rule",     "cardiac_chest_pain" in summary_rule)

# Low confidence
tr_low = make_triage(level=3, confidence=55)
summary_low = _build_staff_summary(tr_low, "EOPD-002")
test("Summary flags low confidence",  "LOW CONFIDENCE" in summary_low)

# Level 1 escalation
tr_l1 = make_triage(level=1, confidence=95, rule_fired=True, rule_name="severe_bleeding")
summary_l1 = _build_staff_summary(tr_l1, "AE-002")
test("Summary flags Level 1 escalation", "IMMEDIATE ESCALATION" in summary_l1)

# No false flags on normal case
test("Normal summary has no escalation flag", "ESCALATION" not in summary)
test("Normal summary has no low confidence",  "LOW CONFIDENCE" not in summary)

print("\n── Results ─────────────────────────────────────────────────────────")
total, passed = len(results), sum(results)
print(f"\n── Results: {passed}/{total} passed ───────────────────────────────────\n")
if all(results):
    print("\033[92mAll routing tests passed! Phase 4 complete.\033[0m\n")
    sys.exit(0)
else:
    print("\033[91mSome tests failed.\033[0m\n")
    sys.exit(1)
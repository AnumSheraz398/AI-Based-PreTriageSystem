"""
Tests for Phase 3 — triage agent.
Tests safety rules deterministically (no OpenAI calls needed).
Run with: python test_triage.py
"""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.intake_model import CanonicalIntake, AgeGroup, Sex, Language
from services.safety_rules import run_safety_rules

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"
results = []

def test(name, condition):
    status = PASS if condition else FAIL
    print(f"{status} | {name}")
    results.append(condition)

def make_intake(complaint, age_group=AgeGroup.adult, sex=Sex.male,
                duration="2 hours", age_exact=None, red_flags=None):
    return CanonicalIntake(
        session_id="test", chief_complaint=complaint,
        age_group=age_group, sex=sex, duration=duration,
        language=Language.english, age_exact=age_exact,
        red_flag_symptoms=red_flags, consent_given=True,
    )

print("\n── Hard safety rule tests ──────────────────────────────────────────")

# Rule 1: Cardiac — chest pain in adult
r = run_safety_rules(make_intake("chest pain radiating to left arm"))
test("Chest pain fires cardiac rule", r.fired)
test("Cardiac rule -> Level 2", r.level == 2)
test("Cardiac rule name correct", r.rule_name == "cardiac_chest_pain")

# Rule 2: Cardiac with Urdu
r = run_safety_rules(make_intake("سینے میں درد ہو رہا ہے"))
test("Urdu chest pain fires cardiac rule", r.fired)
test("Urdu cardiac -> Level 2", r.level == 2)

# Rule 3: Breathing difficulty
r = run_safety_rules(make_intake("difficulty breathing and shortness of breath"))
test("Difficulty breathing fires rule", r.fired)
test("Breathing rule -> Level 2", r.level == 2)
test("Breathing rule name correct", r.rule_name == "difficulty_breathing")

# Rule 4: Urdu breathing
r = run_safety_rules(make_intake("سانس لینے میں تکلیف"))
test("Urdu breathing fires rule", r.fired)
test("Urdu breathing -> Level 2", r.level == 2)

# Rule 5: Loss of consciousness
r = run_safety_rules(make_intake("patient fainted and is now unconscious"))
test("Unconscious fires rule", r.fired)
test("Unconscious -> Level 2", r.level == 2)
test("Unconscious rule name correct", r.rule_name == "loss_of_consciousness")

# Rule 6: Stroke
r = run_safety_rules(make_intake("sudden face drooping and arm weakness"))
test("Stroke symptoms fires rule", r.fired)
test("Stroke -> Level 2", r.level == 2)

# Rule 7: Severe bleeding -> Level 1
r = run_safety_rules(make_intake("severe bleeding from wound, blood everywhere won't stop"))
test("Severe bleeding fires rule", r.fired)
test("Severe bleeding -> Level 1", r.level == 1)
test("Bleeding rule name correct", r.rule_name == "severe_bleeding")

# Rule 8: Poisoning -> Level 1
r = run_safety_rules(make_intake("took tablet overdose, snake bite on leg"))
test("Poisoning fires rule", r.fired)
test("Poisoning -> Level 1", r.level == 1)

# Rule 9: RTA
r = run_safety_rules(make_intake("road accident, car hit me, trauma to chest"))
test("RTA fires rule", r.fired)
test("RTA -> Level 2", r.level == 2)
test("RTA rule name correct", r.rule_name == "road_traffic_accident")

# Rule 10: Child fever -> Level 3
r = run_safety_rules(make_intake("bukhar hai", age_group=AgeGroup.child, age_exact=4))
test("Child fever fires rule", r.fired)
test("Child fever -> Level 3", r.level == 3)
test("Child fever rule name correct", r.rule_name == "child_fever")

# Rule 11: Obstetric
r = run_safety_rules(make_intake("pregnant with abdominal pain", sex=Sex.female))
test("Obstetric emergency fires rule", r.fired)
test("Obstetric -> Level 2", r.level == 2)

# Rule 12: Priority — Level 1 wins over Level 2
r = run_safety_rules(make_intake("severe bleeding and chest pain"))
test("Level 1 rule (bleeding) wins over Level 2 (chest)", r.level == 1)

# Rule 13: No rule fires for routine complaint
r = run_safety_rules(make_intake("mild headache for 2 days, no other symptoms"))
test("Mild headache -> no rule fires", not r.fired)
test("No rule -> level is None", r.level is None)

# Rule 14: Red flag symptoms trigger rules
r = run_safety_rules(make_intake("I feel unwell",
    red_flags=["Chest pain", "Difficulty breathing"]))
test("Red flags in list trigger cardiac rule", r.fired)
test("Red flags -> Level 2", r.level == 2)

print("\n── TriageResult structure tests ────────────────────────────────────")

from services.triage_agent import (
    TriageResult, LEVEL_NAMES, LEVEL_DEPARTMENTS,
    LEVEL_MESSAGES_EN, LEVEL_MESSAGES_UR
)

# All levels have names
for lvl in [1,2,3,4,5]:
    test(f"Level {lvl} has name", lvl in LEVEL_NAMES)
    test(f"Level {lvl} has department", lvl in LEVEL_DEPARTMENTS)
    test(f"Level {lvl} has English message", lvl in LEVEL_MESSAGES_EN)
    test(f"Level {lvl} has Urdu message", lvl in LEVEL_MESSAGES_UR)

# Urdu messages contain Urdu script
for lvl, msg in LEVEL_MESSAGES_UR.items():
    has_urdu = any(ord(c) > 1536 for c in msg)
    test(f"Level {lvl} Urdu message has Urdu script", has_urdu)

print("\n── Results ─────────────────────────────────────────────────────────")
total, passed = len(results), sum(results)
print(f"\n── Results: {passed}/{total} passed ───────────────────────────────────\n")
if all(results):
    print("\033[92mAll triage tests passed! Safety rules working correctly.\033[0m\n")
    sys.exit(0)
else:
    print("\033[91mSome tests failed.\033[0m\n")
    sys.exit(1)
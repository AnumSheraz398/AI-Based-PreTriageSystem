"""
Hard safety rules for triage.

These rules fire BEFORE the LLM triage agent and OVERRIDE any AI output.
They are deterministic, fast, and non-negotiable.

Rules are based on:
  - CTAS 2023 mandatory escalation criteria
  - Pakistani ED context (RTA, dengue, heat stroke, obstetric)
  - SRS requirement FR-TRG-03
"""

from models.intake_model import CanonicalIntake, AgeGroup
from dataclasses import dataclass
from typing import Optional


@dataclass
class SafetyRuleResult:
    fired: bool                        # True if any rule matched
    level: Optional[int]               # Minimum level to assign (1 or 2)
    rule_name: Optional[str]           # Which rule fired
    reason: str                        # Plain English explanation
    reason_ur: str                     # Urdu explanation for patient


# ── Keyword lists ──────────────────────────────────────────────────────────────
# English + Urdu keywords that trigger each rule

CARDIAC_KEYWORDS = [
    # English
    "chest pain", "chest tightness", "chest pressure", "heart attack",
    "cardiac", "palpitation", "heart pain", "left arm pain",
    # Urdu transliterated / romanized
    "seene mein dard", "sine mein dard", "dil ka dard",
    # Urdu script
    "سینے میں درد", "سینے میں تکلیف", "دل کا درد", "بائیں بازو میں درد",
]

BREATHING_KEYWORDS = [
    "difficulty breathing", "can't breathe", "cannot breathe", "shortness of breath",
    "breathless", "breathing problem", "no breath", "suffocating",
    "saans lene mein takleef", "saans nahi aa raha",
    "سانس لینے میں تکلیف", "سانس نہیں آ رہا", "دم گھٹنا",
]

UNCONSCIOUS_KEYWORDS = [
    "unconscious", "fainted", "passed out", "loss of consciousness",
    "unresponsive", "collapsed", "not responding", "fell down unconscious",
    "behosh", "gir gaya", "hosh nahi",
    "بے ہوش", "ہوش نہیں", "گر گیا", "گر گئی",
]

STROKE_KEYWORDS = [
    "face drooping", "facial droop", "arm weakness", "speech difficulty",
    "can't speak", "slurred speech", "sudden weakness", "stroke",
    "fast symptoms", "face numb",
    "منہ کا ٹیڑھا", "ہاتھ کا کمزور", "بولنے میں تکلیف", "فالج",
]

SEVERE_BLEEDING_KEYWORDS = [
    "severe bleeding", "heavy bleeding", "uncontrolled bleeding",
    "blood everywhere", "won't stop bleeding", "haemorrhage",
    "bohat khoon", "khoon nahi ruk raha",
    "بہت زیادہ خون", "خون نہیں رک رہا",
]

OBSTETRIC_KEYWORDS = [
    "pregnant", "pregnancy", "labour", "labor", "contractions",
    "water broke", "delivery", "baby coming", "miscarriage",
    "hamila", "dardon mein",
    "حاملہ", "درد زہ", "ڈلیوری",
]

POISONING_KEYWORDS = [
    "poison", "overdose", "tablets overdose", "snake bite", "snakebite",
    "organophosphate", "insecticide", "acid", "bleach swallowed",
    "zeher", "saanp ka katna",
    "زہر", "سانپ کا کاٹنا", "زہریلی دوائی",
]

RTA_KEYWORDS = [
    "accident", "road accident", "car accident", "motorcycle accident",
    "hit by car", "rta", "vehicle accident", "trauma",
    "hadsa", "gaadi ka hadsa",
    "حادثہ", "گاڑی کا حادثہ", "ٹریفک حادثہ",
]


def _text_contains(text: str, keywords: list[str]) -> bool:
    """Case-insensitive keyword match in complaint text."""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def _get_complaint(intake: CanonicalIntake) -> str:
    """Get full complaint text including red-flag symptoms."""
    parts = [intake.chief_complaint]
    if intake.red_flag_symptoms:
        parts.extend(intake.red_flag_symptoms)
    return " ".join(parts)


# ── Rule functions ─────────────────────────────────────────────────────────────

def rule_cardiac(intake: CanonicalIntake) -> Optional[SafetyRuleResult]:
    """Chest pain in patient over 35 → Level 2 minimum."""
    complaint = _get_complaint(intake)
    age = intake.age_exact or 0

    # Check age threshold
    is_at_risk_age = (
        intake.age_group in (AgeGroup.adult, AgeGroup.elderly)
        or age >= 35
    )

    if _text_contains(complaint, CARDIAC_KEYWORDS) and is_at_risk_age:
        return SafetyRuleResult(
            fired=True, level=2,
            rule_name="cardiac_chest_pain",
            reason="Chest pain in adult/elderly patient — cardiac cause must be ruled out. Level 2 minimum.",
            reason_ur="سینے میں درد — دل کی تکلیف کا خطرہ۔ فوری توجہ ضروری ہے۔",
        )
    return None


def rule_breathing(intake: CanonicalIntake) -> Optional[SafetyRuleResult]:
    """Difficulty breathing → Level 2 minimum."""
    complaint = _get_complaint(intake)
    if _text_contains(complaint, BREATHING_KEYWORDS):
        return SafetyRuleResult(
            fired=True, level=2,
            rule_name="difficulty_breathing",
            reason="Difficulty breathing reported — respiratory emergency possible. Level 2 minimum.",
            reason_ur="سانس لینے میں تکلیف — فوری طبی توجہ ضروری ہے۔",
        )
    return None


def rule_unconscious(intake: CanonicalIntake) -> Optional[SafetyRuleResult]:
    """Any loss of consciousness → Level 2 minimum."""
    complaint = _get_complaint(intake)
    if _text_contains(complaint, UNCONSCIOUS_KEYWORDS):
        return SafetyRuleResult(
            fired=True, level=2,
            rule_name="loss_of_consciousness",
            reason="Loss of consciousness reported — serious neurological or cardiac event possible. Level 2 minimum.",
            reason_ur="بے ہوشی — دماغ یا دل کی سنگین تکلیف ہو سکتی ہے۔ فوری توجہ۔",
        )
    return None


def rule_stroke(intake: CanonicalIntake) -> Optional[SafetyRuleResult]:
    """Stroke symptoms (FAST) → Level 2 minimum."""
    complaint = _get_complaint(intake)
    if _text_contains(complaint, STROKE_KEYWORDS):
        return SafetyRuleResult(
            fired=True, level=2,
            rule_name="stroke_symptoms",
            reason="Stroke symptoms detected (FAST positive) — time-critical. Level 2 minimum.",
            reason_ur="فالج کی علامات — وقت بہت اہم ہے۔ فوری ایمرجنسی۔",
        )
    return None


def rule_severe_bleeding(intake: CanonicalIntake) -> Optional[SafetyRuleResult]:
    """Severe uncontrolled bleeding → Level 1."""
    complaint = _get_complaint(intake)
    if _text_contains(complaint, SEVERE_BLEEDING_KEYWORDS):
        return SafetyRuleResult(
            fired=True, level=1,
            rule_name="severe_bleeding",
            reason="Severe uncontrolled bleeding — immediate life threat. Level 1.",
            reason_ur="بہت زیادہ خون بہہ رہا ہے — فوری جان کا خطرہ۔",
        )
    return None


def rule_obstetric(intake: CanonicalIntake) -> Optional[SafetyRuleResult]:
    """Pregnant patient with abdominal pain or labour → Level 2 minimum."""
    complaint = _get_complaint(intake)
    has_obstetric = _text_contains(complaint, OBSTETRIC_KEYWORDS)
    has_pain = any(w in complaint.lower() for w in [
        "pain", "dard", "درد", "bleeding", "khoon", "خون"
    ])
    if has_obstetric and (has_pain or intake.age_group != AgeGroup.elderly):
        return SafetyRuleResult(
            fired=True, level=2,
            rule_name="obstetric_emergency",
            reason="Pregnant patient with pain or labour signs — obstetric emergency possible. Level 2 minimum.",
            reason_ur="حاملہ مریضہ — زچگی کی ایمرجنسی ہو سکتی ہے۔ فوری توجہ۔",
        )
    return None


def rule_poisoning(intake: CanonicalIntake) -> Optional[SafetyRuleResult]:
    """Poisoning, overdose, snake bite → Level 1."""
    complaint = _get_complaint(intake)
    if _text_contains(complaint, POISONING_KEYWORDS):
        return SafetyRuleResult(
            fired=True, level=1,
            rule_name="poisoning_overdose",
            reason="Poisoning or overdose reported — immediate life threat. Level 1.",
            reason_ur="زہر یا زیادہ دوائی — فوری جان کا خطرہ۔",
        )
    return None


def rule_rta(intake: CanonicalIntake) -> Optional[SafetyRuleResult]:
    """Road traffic accident → Level 2 minimum."""
    complaint = _get_complaint(intake)
    if _text_contains(complaint, RTA_KEYWORDS):
        return SafetyRuleResult(
            fired=True, level=2,
            rule_name="road_traffic_accident",
            reason="Road traffic accident — trauma assessment required. Level 2 minimum.",
            reason_ur="ٹریفک حادثہ — چوٹ کا معائنہ ضروری ہے۔ فوری توجہ۔",
        )
    return None


def rule_child_fever(intake: CanonicalIntake) -> Optional[SafetyRuleResult]:
    """Child under 5 with fever → Level 3 minimum."""
    complaint = _get_complaint(intake)
    has_fever = any(w in complaint.lower() for w in [
        "fever", "bukhar", "temperature", "بخار", "گرمی"
    ])
    is_young_child = intake.age_group == AgeGroup.child or (
        intake.age_exact is not None and intake.age_exact < 5
    )
    if has_fever and is_young_child:
        return SafetyRuleResult(
            fired=True, level=3,
            rule_name="child_fever",
            reason="Child with fever — febrile seizure risk. Level 3 minimum.",
            reason_ur="بچے کو بخار — دورہ پڑنے کا خطرہ۔ جلد توجہ ضروری ہے۔",
        )
    return None


# ── Main safety check function ────────────────────────────────────────────────

ALL_RULES = [
    rule_severe_bleeding,     # Level 1 rules first
    rule_poisoning,
    rule_cardiac,             # Level 2 rules
    rule_breathing,
    rule_unconscious,
    rule_stroke,
    rule_obstetric,
    rule_rta,
    rule_child_fever,         # Level 3 rules last
]


def run_safety_rules(intake: CanonicalIntake) -> SafetyRuleResult:
    """
    Run all hard safety rules against the intake.
    Returns the highest-priority (lowest level number) rule that fired.
    If no rule fires, returns fired=False.
    """
    fired_results = []

    for rule_fn in ALL_RULES:
        result = rule_fn(intake)
        if result and result.fired:
            fired_results.append(result)

    if not fired_results:
        return SafetyRuleResult(
            fired=False, level=None,
            rule_name=None,
            reason="No hard safety rules triggered.",
            reason_ur="کوئی فوری خطرہ نہیں پایا گیا۔",
        )

    # Return the most urgent (lowest level number) result
    return min(fired_results, key=lambda r: r.level)
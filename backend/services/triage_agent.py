"""
Triage agent — AI urgency scoring.
Flow:
  1. Hard safety rules first (fast, deterministic)
  2. If safety rule fired -> use that level (skip LLM)
  3. Otherwise -> call GPT-4o with patient data + RAG chunks
  4. Parse LLM response -> structured TriageResult
  5. If Level 1 -> flag for immediate escalation
"""

import os, json, logging
from openai import AsyncOpenAI
from models.intake_model import CanonicalIntake
from services.safety_rules import run_safety_rules
from rag.chroma_service import retrieve_chunks
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class TriageResult:
    session_id:          str
    level:               int
    level_name:          str
    confidence:          int
    reasoning:           str
    patient_message:     str
    patient_message_ur:  str
    department:          str
    safety_rule_fired:   bool
    safety_rule_name:    Optional[str]
    escalate_now:        bool
    rag_chunks_used:     list
    requires_review:     bool


LEVEL_NAMES = {
    1: "Resuscitation", 2: "Emergent",
    3: "Urgent", 4: "Less Urgent", 5: "Non-urgent",
}

LEVEL_DEPARTMENTS = {
    1: "Emergency — A&E (Immediate)",
    2: "Emergency — A&E",
    3: "Emergency OPD",
    4: "General OPD",
    5: "General OPD",
}

LEVEL_MESSAGES_EN = {
    1: "This is a medical emergency. Please go to the Emergency (A&E) immediately. Staff have been alerted.",
    2: "You need urgent medical attention. Please go to the Emergency department now. You will be seen within 15 minutes.",
    3: "You need to be seen soon. Please go to Emergency OPD. You will be seen within 30 minutes.",
    4: "You will be seen in General OPD. Please wait — expected wait is about 60 minutes.",
    5: "Your condition is stable. Please wait in General OPD. Expected wait is about 2 hours.",
}

LEVEL_MESSAGES_UR = {
    1: "یہ طبی ایمرجنسی ہے۔ فوری طور پر ایمرجنسی (A&E) جائیں۔ عملے کو آگاہ کر دیا گیا ہے۔",
    2: "آپ کو فوری طبی توجہ کی ضرورت ہے۔ ابھی ایمرجنسی شعبے میں جائیں۔ 15 منٹ میں دیکھا جائے گا۔",
    3: "آپ کو جلد دیکھا جانا چاہیے۔ ایمرجنسی OPD جائیں۔ 30 منٹ میں آپ کی باری آئے گی۔",
    4: "آپ کو جنرل OPD میں دیکھا جائے گا۔ براہ کرم انتظار کریں — تقریباً 60 منٹ۔",
    5: "آپ کی حالت مستحکم ہے۔ جنرل OPD میں انتظار کریں — تقریباً 2 گھنٹے۔",
}


def _build_prompt(intake: CanonicalIntake, protocol_chunks: list) -> str:
    chunks_text = "\n---\n".join(protocol_chunks) if protocol_chunks else "No protocols retrieved."
    age_line = f"- Exact age: {intake.age_exact}" if intake.age_exact else ""
    cc_line  = f"- Chronic conditions: {intake.chronic_conditions}" if intake.chronic_conditions else ""
    med_line = f"- Medications: {intake.current_medications}" if intake.current_medications else ""

    return f"""You are an expert emergency triage nurse AI for a Pakistani public hospital.
Assign an urgency level (1-5) to this patient.

LEVELS:
1=Resuscitation(0min) 2=Emergent(15min) 3=Urgent(30min) 4=LessUrgent(60min) 5=NonUrgent(120min)

RETRIEVED PROTOCOLS:
{chunks_text}

PATIENT:
- Chief complaint: {intake.chief_complaint}
- Age group: {intake.age_group.value}
- Sex: {intake.sex.value}
- Duration: {intake.duration}
{age_line}
{cc_line}
{med_line}

Return ONLY valid JSON, no markdown, no extra text:
{{"level":<1-5>,"confidence":<0-100>,"reasoning":"<2-3 sentences for nurse>","patient_message":"<1 sentence plain English>","patient_message_ur":"<1 sentence plain Urdu>"}}"""


async def _call_llm(prompt: str, intake: CanonicalIntake) -> dict:
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    user_msg = (
        f"Triage this patient: {intake.chief_complaint}. "
        f"Age: {intake.age_group.value}. Sex: {intake.sex.value}. "
        f"Duration: {intake.duration}."
    )
    response = await client.chat.completions.create(
        model="gpt-4o",
        temperature=0.1,
        max_tokens=500,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user",   "content": user_msg},
        ],
    )
    raw = response.choices[0].message.content.strip()
    logger.info(f"LLM raw: {raw[:200]}")
    # Strip markdown fences if present
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else parts[0]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


async def run_triage(intake: CanonicalIntake) -> TriageResult:
    """Full triage pipeline: safety rules -> RAG -> LLM -> TriageResult."""
    logger.info(f"Triage | session={intake.session_id} | '{intake.chief_complaint[:60]}'")

    # Step 1: Hard safety rules
    safety = run_safety_rules(intake)
    if safety.fired:
        logger.info(f"Safety rule: {safety.rule_name} -> Level {safety.level}")

    # Step 2: RAG retrieval
    rag_result = await retrieve_chunks(query=intake.chief_complaint, top_k=3)
    chunks_text = [c["text"]                          for c in rag_result.get("chunks", [])]
    chunk_ids   = [c["metadata"].get("source", "?")  for c in rag_result.get("chunks", [])]

    # Step 3: LLM or safety rule
    if safety.fired:
        level           = safety.level
        confidence      = 95
        reasoning       = safety.reason
        patient_msg_en  = LEVEL_MESSAGES_EN[level]
        patient_msg_ur  = safety.reason_ur
        rule_fired      = True
        rule_name       = safety.rule_name
    else:
        try:
            prompt   = _build_prompt(intake, chunks_text)
            data     = await _call_llm(prompt, intake)
            level    = max(1, min(5, int(data.get("level", 3))))
            confidence   = max(0, min(100, int(data.get("confidence", 70))))
            reasoning    = data.get("reasoning", "No reasoning provided.")
            patient_msg_en = data.get("patient_message",    LEVEL_MESSAGES_EN.get(level, ""))
            patient_msg_ur = data.get("patient_message_ur", LEVEL_MESSAGES_UR.get(level, ""))
        except Exception as e:
            logger.error(f"LLM failed: {e} — fallback Level 3")
            level, confidence = 3, 30
            reasoning      = f"AI triage unavailable ({e}). Defaulted to Level 3. Nurse review required."
            patient_msg_en = LEVEL_MESSAGES_EN[3]
            patient_msg_ur = LEVEL_MESSAGES_UR[3]
        rule_fired = False
        rule_name  = None

    result = TriageResult(
        session_id         = intake.session_id,
        level              = level,
        level_name         = LEVEL_NAMES[level],
        confidence         = confidence,
        reasoning          = reasoning,
        patient_message    = patient_msg_en,
        patient_message_ur = patient_msg_ur,
        department         = LEVEL_DEPARTMENTS[level],
        safety_rule_fired  = rule_fired,
        safety_rule_name   = rule_name,
        escalate_now       = level == 1,
        rag_chunks_used    = chunk_ids,
        requires_review    = confidence < 70,
    )

    logger.info(
        f"Triage done | level={level} | confidence={confidence}% | "
        f"escalate={result.escalate_now} | review={result.requires_review}"
    )
    return result
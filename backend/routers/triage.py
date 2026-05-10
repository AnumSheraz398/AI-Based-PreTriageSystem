from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from models.intake_model import CanonicalIntake, AgeGroup, Sex, Language
from services.triage_agent import run_triage
import logging

router = APIRouter(prefix="/triage", tags=["Triage Agent"])
logger = logging.getLogger(__name__)


# ── Request / Response ────────────────────────────────────────────────────────
class TriageRequest(BaseModel):
    """
    Send the CanonicalIntake directly from the intake module.
    Frontend should pass the canonical object returned by /intake/validate.
    """
    canonical: CanonicalIntake


class TriageResponse(BaseModel):
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
    # Colour for frontend display
    level_color:         str


LEVEL_COLORS = {
    1: "#FF3B3B",   # Red
    2: "#FF8C00",   # Orange
    3: "#FFD600",   # Yellow
    4: "#4CAF50",   # Green
    5: "#90CAF9",   # Light blue
}


# ── Endpoint ──────────────────────────────────────────────────────────────────
@router.post("/", response_model=TriageResponse,
             summary="Run AI triage on a validated patient intake")
async def triage(request: TriageRequest):
    """
    Run the full triage pipeline on a validated patient intake.

    **Flow:**
    1. Hard safety rules check (chest pain, breathing difficulty, unconscious, etc.)
    2. RAG retrieval — find top-3 most relevant protocol chunks
    3. GPT-4o triage decision (if no safety rule fired)
    4. Return structured result with level, reasoning, patient messages

    **Input:** Pass the `canonical` object returned by `POST /intake/validate`

    **Output:**
    - `level` 1–5 (1 = most urgent)
    - `escalate_now` true if Level 1 (staff must be alerted immediately)
    - `requires_review` true if AI confidence < 70% (nurse must verify)
    - `patient_message` + `patient_message_ur` — what to show the patient
    - `level_color` — hex color for frontend display
    """
    result = await run_triage(request.canonical)

    return TriageResponse(
        session_id          = result.session_id,
        level               = result.level,
        level_name          = result.level_name,
        confidence          = result.confidence,
        reasoning           = result.reasoning,
        patient_message     = result.patient_message,
        patient_message_ur  = result.patient_message_ur,
        department          = result.department,
        safety_rule_fired   = result.safety_rule_fired,
        safety_rule_name    = result.safety_rule_name,
        escalate_now        = result.escalate_now,
        rag_chunks_used     = result.rag_chunks_used,
        requires_review     = result.requires_review,
        level_color         = LEVEL_COLORS[result.level],
    )


@router.post("/quick", summary="Quick triage test — no CanonicalIntake wrapper needed")
async def quick_triage(
    chief_complaint: str,
    age_group: str = "adult",
    sex: str = "male",
    duration: str = "unknown",
    session_id: str = "quick-test",
):
    """
    Convenience endpoint for testing triage without building a full CanonicalIntake.
    Use this in Swagger UI to quickly test different complaints.

    Example: chief_complaint = "severe chest pain radiating to left arm, sweating"
    """
    intake = CanonicalIntake(
        session_id      = session_id,
        chief_complaint = chief_complaint,
        age_group       = AgeGroup(age_group),
        sex             = Sex(sex),
        duration        = duration,
        language        = Language.english,
        consent_given   = True,
    )
    result = await run_triage(intake)

    return {
        "level":             result.level,
        "level_name":        result.level_name,
        "confidence":        result.confidence,
        "reasoning":         result.reasoning,
        "patient_message":   result.patient_message,
        "patient_message_ur":result.patient_message_ur,
        "department":        result.department,
        "safety_rule_fired": result.safety_rule_fired,
        "safety_rule_name":  result.safety_rule_name,
        "escalate_now":      result.escalate_now,
        "requires_review":   result.requires_review,
        "level_color":       LEVEL_COLORS[result.level],
    }
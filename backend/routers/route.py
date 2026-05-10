from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from models.intake_model import CanonicalIntake
from services.triage_agent import run_triage
from services.routing import route_patient
import logging

router = APIRouter(prefix="/route", tags=["Routing + Explanation"])
logger = logging.getLogger(__name__)


class RouteRequest(BaseModel):
    """
    Send the CanonicalIntake — this endpoint runs triage + routing in one call.
    This is what the frontend calls after consent is granted.
    Single endpoint = simpler frontend integration.
    """
    canonical: CanonicalIntake


class RouteResponse(BaseModel):
    session_id:          str
    token_number:        str
    level:               int
    level_name:          str
    level_color:         str
    department_code:     str
    department_name_en:  str
    department_name_ur:  str
    location_en:         str
    location_ur:         str
    wait_mins:           int
    patient_message_en:  str
    patient_message_ur:  str
    explanation_en:      str
    explanation_ur:      str
    staff_summary:       str
    escalate_now:        bool
    requires_review:     bool
    confidence:          int
    safety_rule_fired:   bool
    safety_rule_name:    Optional[str]


@router.post("/", response_model=RouteResponse,
             summary="Full pipeline: triage + department routing + Urdu explanation")
async def route(request: RouteRequest):
    """
    The main endpoint the frontend calls after consent is granted.

    Runs the complete pipeline in one call:
    1. Hard safety rules check
    2. RAG protocol retrieval
    3. GPT-4o triage scoring
    4. Department assignment + token generation
    5. Urdu + English patient explanation

    **Input:** CanonicalIntake from /intake/validate
    **Output:** Everything needed for the kiosk result screen

    The frontend should display:
    - `token_number` — patient's queue number
    - `level_color` — background color for urgency display
    - `level_name` + `department_name_ur` — in Urdu for the patient
    - `patient_message_ur` — main message in Urdu
    - `location_ur` — where to go in the hospital
    - `wait_mins` — estimated wait
    - `escalate_now` — if true, show emergency alert immediately
    """
    # Run triage
    triage_result = await run_triage(request.canonical)

    # Run routing
    route_result = await route_patient(triage_result)

    return RouteResponse(
        session_id         = route_result.session_id,
        token_number       = route_result.token_number,
        level              = route_result.level,
        level_name         = route_result.level_name,
        level_color        = route_result.level_color,
        department_code    = route_result.department_code,
        department_name_en = route_result.department_name_en,
        department_name_ur = route_result.department_name_ur,
        location_en        = route_result.location_en,
        location_ur        = route_result.location_ur,
        wait_mins          = route_result.wait_mins,
        patient_message_en = route_result.patient_message_en,
        patient_message_ur = route_result.patient_message_ur,
        explanation_en     = route_result.explanation_en,
        explanation_ur     = route_result.explanation_ur,
        staff_summary      = route_result.staff_summary,
        escalate_now       = route_result.escalate_now,
        requires_review    = route_result.requires_review,
        confidence         = triage_result.confidence,
        safety_rule_fired  = triage_result.safety_rule_fired,
        safety_rule_name   = triage_result.safety_rule_name,
    )


@router.post("/quick", summary="Quick test — complaint text only")
async def quick_route(
    chief_complaint: str,
    age_group: str = "adult",
    sex: str = "male",
    duration: str = "2 hours",
    session_id: str = "quick-test",
):
    """
    Test the full pipeline with just a complaint string.
    Use this in Swagger UI to see the complete output quickly.

    Example complaints to try:
    - "severe chest pain and sweating" → Level 2, A&E
    - "bukhar aur ulti" → Level 3, Emergency OPD
    - "mild headache" → Level 4-5, General OPD
    - "snake bite on leg" → Level 1, A&E immediate
    """
    from models.intake_model import CanonicalIntake, AgeGroup, Sex, Language

    intake = CanonicalIntake(
        session_id      = session_id,
        chief_complaint = chief_complaint,
        age_group       = AgeGroup(age_group),
        sex             = Sex(sex),
        duration        = duration,
        language        = Language.english,
        consent_given   = True,
    )

    triage_result = await run_triage(intake)
    route_result  = await route_patient(triage_result)

    return {
        "token_number":       route_result.token_number,
        "level":              route_result.level,
        "level_name":         route_result.level_name,
        "level_color":        route_result.level_color,
        "department_en":      route_result.department_name_en,
        "department_ur":      route_result.department_name_ur,
        "location_ur":        route_result.location_ur,
        "wait_mins":          route_result.wait_mins,
        "patient_message_en": route_result.patient_message_en,
        "patient_message_ur": route_result.patient_message_ur,
        "explanation_ur":     route_result.explanation_ur,
        "escalate_now":       route_result.escalate_now,
        "confidence":         triage_result.confidence,
        "safety_rule_fired":  triage_result.safety_rule_fired,
    }
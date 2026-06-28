from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from models.intake_model import CanonicalIntake, AgeGroup, Sex, Language
from services.triage_agent import run_triage
from services.routing import route_patient
import logging

router = APIRouter(prefix="/route", tags=["Routing + Explanation"])
logger = logging.getLogger(__name__)


class RouteRequest(BaseModel):
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


LEVEL_COLORS = {
    1: "#FF3B3B", 2: "#FF8C00", 3: "#FFD600",
    4: "#4CAF50", 5: "#90CAF9",
}


@router.post("/", response_model=RouteResponse,
             summary="Full pipeline: triage + routing + Urdu explanation + save to DB")
async def route(request: RouteRequest):
    """
    Runs the complete pipeline and saves to database:
    1. Hard safety rules
    2. RAG retrieval
    3. GPT-4o triage
    4. Department routing + token
    5. Urdu explanation
    6. Save to PostgreSQL
    7. Broadcast to dashboard via WebSocket
    """
    # Step 1-5: triage + routing
    triage_result = await run_triage(request.canonical)
    route_result  = await route_patient(triage_result)

    # Step 6: save to database (non-blocking — don't fail if DB is down)
    try:
        from db.models import get_session, AsyncSessionLocal
        from db.service import save_patient_session
        from db.websocket_manager import ws_manager

        if AsyncSessionLocal:
            async with AsyncSessionLocal() as db:
                patient = await save_patient_session(
                    db,
                    route_result  = route_result.__dict__,
                    triage_result = triage_result.__dict__,
                    canonical     = request.canonical.__dict__,
                )
                # Step 7: broadcast to all connected dashboards
                await ws_manager.send_new_patient(patient.to_dict())
    except Exception as e:
        logger.warning(f"DB save failed (non-critical): {e}")

    return RouteResponse(
        session_id         = route_result.session_id,
        token_number       = route_result.token_number,
        level              = route_result.level,
        level_name         = route_result.level_name,
        level_color        = LEVEL_COLORS[route_result.level],
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
    intake = CanonicalIntake(
        session_id=session_id, chief_complaint=chief_complaint,
        age_group=AgeGroup(age_group), sex=Sex(sex),
        duration=duration, language=Language.english, consent_given=True,
    )
    triage_result = await run_triage(intake)
    route_result  = await route_patient(triage_result)
    return {
        "token_number":       route_result.token_number,
        "level":              route_result.level,
        "level_name":         route_result.level_name,
        "level_color":        LEVEL_COLORS[route_result.level],
        "department_en":      route_result.department_name_en,
        "department_ur":      route_result.department_name_ur,
        "location_ur":        route_result.location_ur,
        "wait_mins":          route_result.wait_mins,
        "patient_message_ur": route_result.patient_message_ur,
        "escalate_now":       route_result.escalate_now,
        "confidence":         triage_result.confidence,
    }
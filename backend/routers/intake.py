from fastapi import APIRouter
from models.intake_model import IntakePayload, ValidationResult
from services.validation import validate_intake

router = APIRouter(prefix="/intake", tags=["Patient Intake"])
 

@router.post("/validate", response_model=ValidationResult, summary="Validate patient intake fields")
async def validate_intake_endpoint(payload: IntakePayload):
    print(payload)
    """
    Validate a patient intake payload.

    Checks that all mandatory fields are present and correctly formed:
    - chief_complaint (at least 2 characters)
    - age_group (child / adult / elderly)
    - sex (male / female / prefer_not_to_say)
    - duration (how long the complaint has been present)

    If valid, returns a normalized CanonicalIntake model ready for the
    triage agent. If invalid, returns a list of missing fields so the
    kiosk can highlight exactly which fields need to be filled.

    **Note:** Consent is NOT part of this endpoint. Call /consent separately
    after the patient sees the consent screen.
    """
    print("🔥 Endpoint reached")  # <--- ADD THIS
    return validate_intake(payload)

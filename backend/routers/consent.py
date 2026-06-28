from fastapi import APIRouter
from pydantic import BaseModel
from models.intake_model import ConsentPayload
from datetime import datetime, timezone
import logging

router = APIRouter(prefix="/consent", tags=["Consent Gate"])
logger = logging.getLogger(__name__)

# In-memory consent log for prototype
# In production this goes to PostgreSQL
_consent_log: dict[str, dict] = {}


class ConsentResponse(BaseModel):
    session_id: str
    consent_given: bool
    route: str          # "auto" = AI processing | "manual" = nurse queue
    message: str
    message_ur: str
    timestamp: str


@router.post("", response_model=ConsentResponse, summary="Record patient consent decision")
async def record_consent(payload: ConsentPayload):
    """
    Record the patient's consent decision and determine processing route.

    This is the **consent gate** — a hard requirement before any AI
    processing of clinical data begins.

    - If consent_given = true  → patient goes to automated AI triage route
    - If consent_given = false → patient is immediately routed to nurse queue
      and NO AI processing occurs on their data

    The consent decision is timestamped and stored in the audit log.
    """
    
    print("🔥 Incoming payload:", payload.model_dump())

    timestamp = datetime.now(timezone.utc).isoformat()

    # Store in audit log
    _consent_log[payload.session_id] = {
        "session_id": payload.session_id,
        "consent_given": payload.consent_given,
        "language": payload.language,
        "timestamp": timestamp,
    }

    logger.info(
        f"Consent recorded | session={payload.session_id} | "
        f"consent={payload.consent_given} | ts={timestamp}"
    )

    if payload.consent_given:
        return ConsentResponse(
            session_id=payload.session_id,
            consent_given=True,
            route="auto",
            message="Consent granted. Proceeding to AI triage.",
            message_ur="آپ نے اجازت دی ہے۔ AI جائزہ شروع ہو رہا ہے۔",
            timestamp=timestamp,
        )
    else:
        return ConsentResponse(
            session_id=payload.session_id,
            consent_given=False,
            route="manual",
            message="Consent declined. Routing to nurse queue.",
            message_ur="آپ نے AI پروسیسنگ سے انکار کیا ہے۔ نرس آپ سے ملیں گی۔",
            timestamp=timestamp,
        )


@router.get("/log/{session_id}", summary="Get consent log entry for a session (admin only)")
async def get_consent_log(session_id: str):
    """
    Retrieve the consent log entry for a given session.
    This endpoint is for admin/audit use only — add auth middleware in production.
    """
    entry = _consent_log.get(session_id)
    if not entry:
        return {"error": "No consent record found for this session"}
    return entry

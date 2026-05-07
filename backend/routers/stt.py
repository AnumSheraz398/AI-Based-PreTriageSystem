from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from models.intake_model import STTResponse, Language
from services.whisper_stt import transcribe_audio
import uuid

router = APIRouter(prefix="/stt", tags=["Speech to Text"])
import os
print("🔑 OPENAI KEY:", os.getenv("OPENAI_API_KEY"))

@router.post("/transcribe", response_model=STTResponse, summary="Convert Urdu/English audio to text")
async def transcribe(
    audio: UploadFile = File(..., description="Audio file from kiosk microphone (wav/webm/mp3/mp4)"),
    session_id: str = Form(default_factory=lambda: str(uuid.uuid4()),
                            description="Session ID — use the one from the current kiosk session"),
    language: str = Form(default="ur", description="Hint language: 'ur' for Urdu, 'en' for English"),
):
    """
    Transcribe a patient's spoken complaint using OpenAI Whisper.

    - Accepts audio recorded on the kiosk microphone
    - Language hint 'ur' strongly biases Whisper toward Urdu recognition
    - Medical vocabulary prompt improves accuracy on symptom terms
    - Returns the full transcript ready to populate the chief_complaint field

    **Frontend usage:** record audio → POST here → put transcript in chief_complaint field
    """
    print("🔥 STT endpoint hit")
    print("📁 File:", audio.filename)
    print("🆔 Session:", session_id)
    print("🌐 Language:", language)
    if language not in ("ur", "en"):
        raise HTTPException(status_code=400, detail="Language must be 'ur' or 'en'")

    result = await transcribe_audio(
        audio_file=audio,
        hint_language=language,
    )

    return STTResponse(
        session_id=session_id,
        transcript=result["transcript"],
        language_detected=result["language_detected"],
        confidence=None,    # Whisper API does not expose per-transcript confidence
    )

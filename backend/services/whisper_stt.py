import os
import tempfile
from openai import AsyncOpenAI
from fastapi import UploadFile, HTTPException
import logging

logger = logging.getLogger(__name__)

# Supported audio formats by Whisper API
SUPPORTED_FORMATS = {
    "audio/mpeg": ".mp3",
    "audio/mp4": ".mp4",
    "audio/wav": ".wav",
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/x-m4a": ".m4a",
    "application/octet-stream": ".webm",   # fallback for browser recordings
}

# Max file size: 25MB (Whisper API limit)
MAX_FILE_SIZE_MB = 25
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


async def transcribe_audio(
    audio_file: UploadFile,
    hint_language: str = "ur",          # "ur" = Urdu, "en" = English
    prompt: str | None = None,
) -> dict:
    """
    Transcribe an audio file using OpenAI Whisper.

    Args:
        audio_file:     The uploaded audio file from the kiosk microphone
        hint_language:  ISO language code hint — "ur" strongly biases toward Urdu
        prompt:         Optional prompt to guide Whisper on medical vocabulary

    Returns:
        dict with keys: transcript, language_detected, duration_seconds
    """
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # ── Validate file type ─────────────────────────────────────────────────────
    content_type = audio_file.content_type or "application/octet-stream"
    extension = SUPPORTED_FORMATS.get(content_type)
    if not extension:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported audio format: {content_type}. "
                   f"Supported: {', '.join(SUPPORTED_FORMATS.keys())}"
        )

    # ── Read and size-check ────────────────────────────────────────────────────
    audio_bytes = await audio_file.read()
    if len(audio_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Audio file too large. Maximum size is {MAX_FILE_SIZE_MB}MB."
        )
    if len(audio_bytes) < 100:
        raise HTTPException(
            status_code=400,
            detail="Audio file is empty or too short. Please record again."
        )

    # ── Medical Urdu vocabulary prompt ────────────────────────────────────────
    # This prompt biases Whisper toward correct medical Urdu terms
    medical_prompt = prompt or (
        "مریض اپنی تکلیف بیان کر رہا ہے۔ طبی اصطلاحات: بخار، درد، سینے میں درد، "
        "سانس لینے میں تکلیف، الٹی، چکر، کمزوری، بلڈ پریشر، شوگر، دل کی دھڑکن۔ "
        "Patient describing symptoms. Medical terms: fever, pain, chest pain, "
        "difficulty breathing, vomiting, dizziness, weakness, blood pressure, diabetes."
    )

    # ── Call Whisper API ───────────────────────────────────────────────────────
    try:
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=(audio_file.filename or f"audio{extension}", f, content_type),
                language=hint_language if hint_language in ("ur", "en") else None,
                prompt=medical_prompt,
                response_format="verbose_json",   # gives us language detection + duration
            )

        transcript = response.text.strip()
        language_detected = getattr(response, "language", hint_language)
        duration = getattr(response, "duration", None)

        logger.info(
            f"STT success | lang={language_detected} | "
            f"duration={duration}s | chars={len(transcript)}"
        )

        return {
            "transcript": transcript,
            "language_detected": language_detected,
            "duration_seconds": round(duration, 1) if duration else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Whisper STT error: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Speech-to-text service error: {str(e)}"
        )
    finally:
        # Always clean up temp file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

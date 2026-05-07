from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from pathlib import Path
from routers import intake, stt, consent, rag
import logging
import os

# Load .env from the same directory as main.py — works regardless of where
# you launch uvicorn from (D:\pretriage\backend or D:\pretriage etc.)
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Hospital Pre-Triage AI — Backend API",
    description="Patient intake, STT transcription, and consent gate for the AI-powered pre-triage system.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow both kiosk-ui (5173) and staff-dashboard (5174)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",    # kiosk-ui
        "http://localhost:5174",    # staff-dashboard
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(intake.router)
app.include_router(stt.router)
app.include_router(consent.router)
app.include_router(rag.router)


# Global 422 handler — returns readable error instead of raw Pydantic objects
@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
    errors = exc.errors() if hasattr(exc, "errors") else []
    readable = []
    for e in errors:
        field = " -> ".join(str(x) for x in e.get("loc", []))
        msg = e.get("msg", "Invalid value")
        readable.append(f"{field}: {msg}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation failed",
            "detail": readable,
            "hint": "Check that all required fields are sent with correct types.",
        }
    )


@app.get("/health", tags=["System"])
async def health():
    key_ok = bool(os.getenv("OPENAI_API_KEY"))
    return {
        "status": "ok",
        "version": "0.1.0",
        "openai_key_configured": key_ok,
        "env_file_path": str(env_path),
        "env_file_exists": env_path.exists(),
        "modules": ["intake", "stt", "consent"],
    }


@app.on_event("startup")
async def startup():
    key_ok = bool(os.getenv("OPENAI_API_KEY"))
    logger.info("Hospital Pre-Triage API started")
    logger.info(f"Env file: {env_path} | exists={env_path.exists()}")
    logger.info(f"OpenAI key configured: {key_ok}")
    if not key_ok:
        logger.warning(
            "OpenAI API key NOT found. "
            f"Create {env_path} and add: OPENAI_API_KEY=sk-..."
        )
    else:
        # Auto-ingest protocols on startup if not already loaded
        try:
            from rag.chroma_service import get_collection_stats, ingest_protocols
            from rag.protocol_data import PROTOCOL_CHUNKS
            stats = get_collection_stats()
            if not stats["is_ready"]:
                logger.info("Knowledge base empty — auto-ingesting protocols...")
                result = await ingest_protocols(PROTOCOL_CHUNKS)
                logger.info(f"Auto-ingest complete: {result}")
            else:
                logger.info(f"Knowledge base ready: {stats['chunk_count']} chunks loaded")
        except Exception as e:
            logger.warning(f"Auto-ingest failed (non-critical): {e}")
    logger.info("Docs: http://localhost:8000/docs")
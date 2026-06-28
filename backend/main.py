from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from pathlib import Path
from routers import intake, stt, consent, rag, triage, route, dashboard
import logging, os

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Hospital Pre-Triage AI — Backend API",
    description="AI-powered pre-triage system for Pakistani public hospitals.",
    version="0.5.0",
    docs_url="/docs", redoc_url="/redoc",
)

app.add_middleware(CORSMiddleware,
    allow_origins=[
        "http://localhost:3000","http://localhost:5173",
        "http://localhost:5174","http://127.0.0.1:5173","http://127.0.0.1:5174",
        "https://ai-based-pretriage-system.vercel.app",
        "https://ai-based-pre-triage-system.vercel.app",
    ],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

app.include_router(intake.router)
app.include_router(stt.router)
app.include_router(consent.router)
app.include_router(rag.router)
app.include_router(triage.router)
app.include_router(route.router)
app.include_router(dashboard.router)


@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
    errors = exc.errors() if hasattr(exc, "errors") else []
    readable = [
        f"{' -> '.join(str(x) for x in e.get('loc',[]))}: {e.get('msg','Invalid')}"
        for e in errors
    ]
    return JSONResponse(status_code=422, content={
        "error": "Validation failed", "detail": readable,
        "hint": "Check all required fields are sent with correct types.",
    })


@app.get("/health", tags=["System"])
async def health():
    from rag.chroma_service import get_collection_stats
    from db.models import AsyncSessionLocal
    rag_stats = get_collection_stats()
    return {
        "status":               "ok",
        "version":              "0.5.0",
        "openai_key_configured": bool(os.getenv("OPENAI_API_KEY")),
        "rag_ready":            rag_stats["is_ready"],
        "rag_chunks":           rag_stats["chunk_count"],
        "db_connected":         AsyncSessionLocal is not None,
        "modules":              ["intake","stt","consent","rag","triage","route","dashboard"],
    }


@app.on_event("startup")
async def startup():
    key_ok = bool(os.getenv("OPENAI_API_KEY"))
    logger.info("Hospital Pre-Triage API v0.5.0 started")
    logger.info(f"OpenAI key: {key_ok}")

    # Initialize database
    try:
        from db.models import init_db
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database init failed (continuing without DB): {e}")
        logger.warning("Set DATABASE_URL in .env or install PostgreSQL to enable persistence")

    # Auto-ingest RAG protocols
    if key_ok:
        try:
            from rag.chroma_service import get_collection_stats, ingest_protocols
            from rag.protocol_data import PROTOCOL_CHUNKS
            stats = get_collection_stats()
            if not stats["is_ready"]:
                logger.info("Auto-ingesting protocols...")
                result = await ingest_protocols(PROTOCOL_CHUNKS)
                logger.info(f"Auto-ingest: {result}")
            else:
                logger.info(f"RAG ready: {stats['chunk_count']} chunks")
        except Exception as e:
            logger.warning(f"RAG auto-ingest failed: {e}")

    logger.info("Docs: http://localhost:8000/docs")
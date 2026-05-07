from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
from rag.chroma_service import ingest_protocols, retrieve_chunks, get_collection_stats
from rag.protocol_data import PROTOCOL_CHUNKS
import logging

router = APIRouter(prefix="/rag", tags=["RAG — Knowledge Base"])
logger = logging.getLogger(__name__)


# ── Request / Response models ─────────────────────────────────────────────────
class IngestRequest(BaseModel):
    force: bool = False


class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 3
    level_filter: Optional[int] = None


class RetrievedChunk(BaseModel):
    text: str
    metadata: dict
    similarity: float


class RetrieveResponse(BaseModel):
    status: str
    query: str
    chunks: list[RetrievedChunk]
    total_in_db: int


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post("/ingest", summary="Load triage protocols into ChromaDB")
async def ingest(request: IngestRequest = IngestRequest()):
    """
    Embed all protocol chunks and store them in the local ChromaDB vector database.

    - Run this ONCE after setting up the backend for the first time.
    - Set force=true to re-ingest from scratch (e.g. after updating protocols).
    - Safe to call multiple times — skips if data already exists (unless force=true).

    This calls the OpenAI embeddings API (text-embedding-3-small).
    Cost: ~$0.002 for the full protocol set (very cheap).
    """
    logger.info(f"RAG ingest requested | force={request.force}")
    result = await ingest_protocols(PROTOCOL_CHUNKS, force=request.force)
    return result


@router.post("/retrieve", response_model=RetrieveResponse,
             summary="Find top-K relevant protocol chunks for a patient complaint")
async def retrieve(request: RetrieveRequest):
    """
    Given a patient's chief complaint (in Urdu or English), retrieve the
    most relevant triage protocol sections from ChromaDB.

    This is what the triage agent will call in Phase 3 before making its decision.

    - query: the patient's complaint text (from CanonicalIntake.chief_complaint)
    - top_k: how many chunks to return (default 3 — optimal for triage context)
    - level_filter: optional — restrict to a specific triage level (1-5)

    Returns chunks ranked by semantic similarity (highest similarity first).
    """
    if not request.query.strip():
        return RetrieveResponse(
            status="error",
            query=request.query,
            chunks=[],
            total_in_db=0,
        )

    result = await retrieve_chunks(
        query=request.query,
        top_k=request.top_k,
        level_filter=request.level_filter,
    )

    chunks = [
        RetrievedChunk(
            text=c["text"],
            metadata=c["metadata"],
            similarity=c["similarity"],
        )
        for c in result.get("chunks", [])
    ]

    return RetrieveResponse(
        status=result["status"],
        query=result["query"],
        chunks=chunks,
        total_in_db=result.get("total_in_db", 0),
    )


@router.get("/status", summary="Check if knowledge base is loaded and ready")
async def rag_status():
    """
    Quick check — is the ChromaDB collection populated and ready?

    Call this on startup to verify the knowledge base is loaded.
    If is_ready=false, call POST /rag/ingest first.
    """
    return get_collection_stats()
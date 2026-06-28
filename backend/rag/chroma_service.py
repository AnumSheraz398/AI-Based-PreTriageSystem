"""
RAG service — ChromaDB ingestion and retrieval.

Two responsibilities:
  1. ingest_protocols()  — one-time: embed all protocol chunks and store in ChromaDB
  2. retrieve_chunks()   — per-patient: embed complaint, find top-k similar chunks
"""

import os
import logging
from typing import Optional
from openai import AsyncOpenAI
import chromadb
from chromadb.config import Settings
from pathlib import Path

logger = logging.getLogger(__name__)

# ── ChromaDB setup ─────────────────────────────────────────────────────────────
# Store the database in a persistent folder next to the backend code
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"
COLLECTION_NAME = "triage_protocols"
EMBEDDING_MODEL = "text-embedding-3-small"   # cheap, fast, good quality


def _get_client() -> chromadb.PersistentClient:
    """Return a persistent ChromaDB client, creating the directory if needed."""
    CHROMA_DIR.mkdir(exist_ok=True)
    return chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )

def _get_collection(client: chromadb.PersistentClient):
    """Get or create the triage protocols collection."""
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},   # cosine similarity for medical text
    )


# ── Embedding helper ───────────────────────────────────────────────────────────
async def _embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of texts using OpenAI text-embedding-3-small.
    Returns list of embedding vectors (one per text).
    """
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


# ── Ingestion pipeline ─────────────────────────────────────────────────────────
async def ingest_protocols(chunks: list[dict], force: bool = False) -> dict:
    """
    Embed all protocol chunks and store them in ChromaDB.

    Args:
        chunks: List of dicts with keys: id, text, metadata
        force:  If True, delete existing collection and re-ingest from scratch
                If False, skip if collection already has data

    Returns:
        dict with ingestion stats
    """
    client = _get_client()

    if force:
        try:
            client.delete_collection(COLLECTION_NAME)
            logger.info(f"Deleted existing collection '{COLLECTION_NAME}'")
        except Exception:
            pass

    collection = _get_collection(client)

    # Check if already ingested
    existing_count = collection.count()
    if existing_count > 0 and not force:
        logger.info(f"Collection already has {existing_count} chunks. Skipping ingestion.")
        return {
            "status": "skipped",
            "reason": "already_ingested",
            "chunk_count": existing_count,
        }

    logger.info(f"Ingesting {len(chunks)} protocol chunks into ChromaDB...")

    # Embed all texts in one batch (cheaper API call)
    texts = [c["text"] for c in chunks]
    ids   = [c["id"]   for c in chunks]
    metas = [c["metadata"] for c in chunks]

    # Convert any None values in metadata (ChromaDB doesn't accept None)
    cleaned_metas = []
    for m in metas:
        cleaned_metas.append({
            k: (str(v) if v is not None else "null")
            for k, v in m.items()
        })

    embeddings = await _embed_texts(texts)

    # Store in ChromaDB
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=cleaned_metas,
    )

    count = collection.count()
    logger.info(f"Ingestion complete. {count} chunks stored in ChromaDB.")

    return {
        "status": "success",
        "chunk_count": count,
        "collection": COLLECTION_NAME,
        "embedding_model": EMBEDDING_MODEL,
        "db_path": str(CHROMA_DIR),
    }


# ── Retrieval pipeline ─────────────────────────────────────────────────────────
async def retrieve_chunks(
    query: str,
    top_k: int = 3,
    level_filter: Optional[int] = None,
) -> dict:
    """
    Find the top-k most relevant protocol chunks for a patient complaint.

    Args:
        query:        Patient's chief complaint (plain text, Urdu or English)
        top_k:        Number of chunks to return (default 3)
        level_filter: Optional — only return chunks for a specific triage level

    Returns:
        dict with retrieved chunks and similarity scores
    """
    client = _get_client()
    collection = _get_collection(client)

    chunk_count = collection.count()
    if chunk_count == 0:
        logger.warning("ChromaDB collection is empty. Run /rag/ingest first.")
        return {
            "status": "error",
            "error": "knowledge_base_empty",
            "message": "No protocols loaded. Call POST /rag/ingest first.",
            "chunks": [],
        }

    # Embed the patient query
    query_embedding = (await _embed_texts([query]))[0]

    # Build optional metadata filter
    where_filter = None
    if level_filter is not None:
        where_filter = {"level": str(level_filter)}

    # Query ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, chunk_count),
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    # Format results
    chunks = []
    documents  = results["documents"][0]
    metadatas  = results["metadatas"][0]
    distances  = results["distances"][0]

    for doc, meta, dist in zip(documents, metadatas, distances):
        similarity = round(1 - dist, 4)   # cosine distance → similarity score
        chunks.append({
            "text":       doc,
            "metadata":   meta,
            "similarity": similarity,
        })

    logger.info(
        f"RAG retrieve | query='{query[:60]}...' | "
        f"top_k={top_k} | returned={len(chunks)} chunks"
    )

    return {
        "status": "success",
        "query":  query,
        "chunks": chunks,
        "total_in_db": chunk_count,
    }


# ── Utility ───────────────────────────────────────────────────────────────────
def get_collection_stats() -> dict:
    """Return stats about the current ChromaDB collection (sync, no embedding needed)."""
    try:
        client = _get_client()
        collection = _get_collection(client)
        count = collection.count()
        return {
            "collection":  COLLECTION_NAME,
            "chunk_count": count,
            "db_path":     str(CHROMA_DIR),
            "is_ready":    count > 0,
        }
    except Exception as e:
        return {
            "collection":  COLLECTION_NAME,
            "chunk_count": 0,
            "db_path":     str(CHROMA_DIR),
            "is_ready":    False,
            "error":       str(e),
        }
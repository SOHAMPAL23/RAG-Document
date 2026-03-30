"""
Storage Layer — Local JSON + FAISS
====================================
Provides all data persistence functions using a local JSON file (chunks_db.json)
and delegates vector search to the FAISS index managed in rag.py.
Firebase code has been removed — everything runs locally.
"""

import os
import json
import threading
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DB")

# ------------------------------------------------------------------ paths
LOCAL_DB_FILE = os.path.join(os.path.dirname(__file__), "chunks_db.json")
_db_lock = threading.Lock()


# =====================================================================
#  Low-level JSON helpers
# =====================================================================

def _load_db() -> Dict:
    with _db_lock:
        if not os.path.exists(LOCAL_DB_FILE):
            return {"documents": [], "chunks": [], "counter": 0}
        try:
            with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"documents": [], "chunks": [], "counter": 0}


def _save_db(data: Dict):
    with _db_lock:
        with open(LOCAL_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)


# =====================================================================
#  Initialisation
# =====================================================================

def init_db():
    """Ensure the DB file exists."""
    if not os.path.exists(LOCAL_DB_FILE):
        _save_db({"documents": [], "chunks": [], "counter": 0})
    logger.info("Database initialised (local JSON: %s).", LOCAL_DB_FILE)


# =====================================================================
#  Documents
# =====================================================================

def store_document(filename: str) -> int:
    """Store document metadata. Returns a numeric doc_id."""
    db = _load_db()
    doc_id = db.get("counter", 0) + 1
    db["counter"] = doc_id
    db.setdefault("documents", []).append({
        "id": doc_id,
        "filename": filename,
        "upload_time": datetime.now().isoformat(),
    })
    _save_db(db)
    logger.info("Stored document '%s' → id=%d.", filename, doc_id)
    return doc_id


# =====================================================================
#  Chunks
# =====================================================================

def store_chunks_batch(
    doc_id: int,
    chunks: List[Dict],
    embeddings: List[List[float]],
):
    """
    Persist chunks and their embeddings to the local JSON file.
    `chunks` is a list of dicts with keys: text, chunk_index, page_estimate.
    `embeddings` is a parallel list of float vectors.
    """
    db = _load_db()
    for i, chunk in enumerate(chunks):
        db["chunks"].append({
            "chunk_id": f"chunk_{len(db['chunks']):05d}",
            "document_id": doc_id,
            "chunk_index": chunk["chunk_index"],
            "text": chunk["text"],
            "page_estimate": chunk.get("page_estimate", 0),
            "embedding": embeddings[i][:10],  # store first 10 dims as sample (full vectors in FAISS)
            "embedding_full_dim": len(embeddings[i]),
            "created_at": datetime.now().isoformat(),
        })
    _save_db(db)
    logger.info("Stored %d chunks locally.", len(chunks))


# Make store_document and store_chunks_batch awaitable for rag.py
async def store_document_async(filename: str) -> int:
    return store_document(filename)


async def store_chunks_batch_async(doc_id, chunks, embeddings):
    return store_chunks_batch(doc_id, chunks, embeddings)


# =====================================================================
#  Read helpers
# =====================================================================

def get_all_chunks() -> List[Dict]:
    """Return all chunks sorted by chunk_index."""
    db = _load_db()
    chunks = db.get("chunks", [])
    for c in chunks:
        c["id"] = c.get("chunk_id", "")
    return sorted(chunks, key=lambda x: x.get("chunk_index", 0))


def get_chunks_paginated(limit: int = 20, offset: int = 0) -> List[Dict]:
    all_chunks = get_all_chunks()
    return all_chunks[offset: offset + limit]


def get_chunk_count() -> int:
    db = _load_db()
    return len(db.get("chunks", []))


def get_chunk_by_id(chunk_id: str) -> Optional[Dict]:
    db = _load_db()
    for c in db.get("chunks", []):
        if c.get("chunk_id") == chunk_id:
            c["id"] = c["chunk_id"]
            return c
    return None


def get_sample_chunks_for_debug(limit: int = 3) -> List[Dict]:
    """Return a few sample chunks with truncated text and embedding preview."""
    chunks = get_chunks_paginated(limit=limit)
    samples = []
    for chunk in chunks:
        samples.append({
            "id": chunk.get("chunk_id", ""),
            "text_preview": chunk.get("text", "")[:200],
            "page_estimate": chunk.get("page_estimate", 0),
            "embedding_sample": chunk.get("embedding", [])[:5],
            "embedding_dim": chunk.get("embedding_full_dim", 0),
        })
    return samples


# =====================================================================
#  Search  (delegates to FAISS via rag module)
# =====================================================================

async def search_similar_chunks(query_embedding: List[float], top_k: int = 5) -> List[Dict]:
    """
    Vector similarity search using FAISS (called from rag.retrieve_and_generate).
    This is kept for API compat but the main query path uses rag.search_faiss() directly.
    """
    import rag as rag_module
    import numpy as np
    qvec = np.array(query_embedding, dtype="float32")
    results = rag_module.search_faiss(qvec, top_k=top_k)

    all_chunks = get_all_chunks()
    chunk_map = {c.get("chunk_index", i): c for i, c in enumerate(all_chunks)}

    output = []
    for idx, score in results:
        chunk = chunk_map.get(idx, {})
        output.append({
            "id": chunk.get("chunk_id", ""),
            "text": chunk.get("text", ""),
            "text_content": chunk.get("text", ""),
            "similarity": score,
            "page_estimate": chunk.get("page_estimate", 0),
            "document_id": chunk.get("document_id", 0),
        })
    return output


# =====================================================================
#  Reset
# =====================================================================

def delete_all_chunks():
    """Wipe all chunks and documents."""
    _save_db({"documents": [], "chunks": [], "counter": 0})
    # Also delete FAISS index
    faiss_path = os.path.join(os.path.dirname(__file__), "faiss_index", "index.faiss")
    if os.path.exists(faiss_path):
        os.remove(faiss_path)
    logger.info("Database and FAISS index cleared.")

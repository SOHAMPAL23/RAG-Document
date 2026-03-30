"""
RAG Engine — Stock Market & Investment Analysis
================================================
- RecursiveCharacterTextSplitter (chunk_size=500, overlap=50)
- Local embeddings via sentence-transformers (all-MiniLM-L6-v2)
- FAISS vector store for similarity search
- Batch processing with delays & exponential-backoff retries
- Gemini LLM for answer generation
"""

# ── Prevent transformers from importing TensorFlow (avoids protobuf conflict) ──
import os
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["USE_TF"] = "0"

import fitz  # PyMuPDF
import numpy as np
import faiss
import time
import json
import logging
import asyncio
from typing import List, Tuple, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# ------------------------------------------------------------------ logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("RAG")

# ------------------------------------------------------------------ paths
FAISS_DIR = os.path.join(os.path.dirname(__file__), "faiss_index")
CHUNKS_DB = os.path.join(os.path.dirname(__file__), "chunks_db.json")

# ------------------------------------------------------------------ model
_embedding_model: Optional[SentenceTransformer] = None
EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 output dimension

# ------------------------------------------------------------------ FAISS
_faiss_index: Optional[faiss.IndexFlatIP] = None  # Inner-Product (cosine after normalisation)


# =====================================================================
#  Embedding model
# =====================================================================

def get_embedding_model() -> SentenceTransformer:
    """Load or return the cached sentence-transformers model."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading sentence-transformers model: all-MiniLM-L6-v2 …")
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Model loaded successfully (dim=%d).", _embedding_model.get_sentence_embedding_dimension())
    return _embedding_model


# =====================================================================
#  PDF text extraction
# =====================================================================

def extract_text_from_pdf(filepath: str) -> Tuple[str, int]:
    """Extract all text from a PDF. Returns (full_text, page_count)."""
    logger.info("Extracting text from PDF: %s", filepath)
    doc = fitz.open(filepath)
    pages_text: List[str] = []
    for page in doc:
        pages_text.append(page.get_text())
    doc.close()
    full_text = "\n".join(pages_text)
    logger.info("Extracted %d characters from %d pages.", len(full_text), len(pages_text))
    return full_text, len(pages_text)


# =====================================================================
#  Smart chunking  (RecursiveCharacterTextSplitter)
# =====================================================================

def create_chunks(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
    """
    Split text into semantically-aware chunks using RecursiveCharacterTextSplitter.
    Returns list of dicts: {text, chunk_index, page_estimate}.
    """
    logger.info("Chunking text (chunk_size=%d, overlap=%d) …", chunk_size, chunk_overlap)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    raw_chunks = splitter.split_text(text)

    chunks = []
    for i, chunk_text in enumerate(raw_chunks):
        chunks.append({
            "text": chunk_text.strip(),
            "chunk_index": i,
            "page_estimate": max(1, int((i / max(len(raw_chunks), 1)) * 100)),  # rough %
        })

    logger.info("Created %d chunks.", len(chunks))
    return chunks


# =====================================================================
#  Retry decorator with exponential back-off
# =====================================================================

def retry_with_backoff(fn, max_retries: int = 3, base_delay: float = 2.0):
    """Decorator-style caller: retries `fn()` with exponential back-off."""
    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "Attempt %d/%d failed (%s). Retrying in %.1fs …",
                attempt, max_retries, exc, delay,
            )
            if attempt == max_retries:
                logger.error("All %d retries exhausted.", max_retries)
                raise
            time.sleep(delay)


# =====================================================================
#  Batch embedding with delays
# =====================================================================

def generate_embeddings_batched(
    texts: List[str],
    batch_size: int = 20,
    inter_batch_delay: float = 1.5,
) -> np.ndarray:
    """
    Embed `texts` in batches of `batch_size`.
    Sleeps `inter_batch_delay` seconds between batches to stay safe.
    Returns (N, dim) numpy array, L2-normalised for cosine similarity via IP.
    """
    model = get_embedding_model()
    total = len(texts)
    num_batches = (total + batch_size - 1) // batch_size
    logger.info("Generating embeddings: %d texts in %d batches (batch_size=%d) …", total, num_batches, batch_size)

    all_embeddings: List[np.ndarray] = []

    for b in range(num_batches):
        start = b * batch_size
        end = min(start + batch_size, total)
        batch_texts = texts[start:end]

        def _encode():
            return model.encode(batch_texts, convert_to_numpy=True, show_progress_bar=False)

        embeddings = retry_with_backoff(_encode)
        all_embeddings.append(embeddings)
        logger.info("  Batch %d/%d done (%d texts).", b + 1, num_batches, len(batch_texts))

        if b < num_batches - 1:
            time.sleep(inter_batch_delay)

    result = np.vstack(all_embeddings).astype("float32")
    # L2-normalise so inner-product == cosine similarity
    faiss.normalize_L2(result)
    logger.info("All embeddings generated. Shape: %s", result.shape)
    return result


# =====================================================================
#  FAISS index management
# =====================================================================

def _index_path() -> str:
    return os.path.join(FAISS_DIR, "index.faiss")


def build_faiss_index(embeddings: np.ndarray) -> faiss.IndexFlatIP:
    """Build a new FAISS IndexFlatIP from embeddings."""
    global _faiss_index
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    _faiss_index = index
    logger.info("FAISS index built with %d vectors (dim=%d).", index.ntotal, dim)
    return index


def save_faiss_index(index: Optional[faiss.IndexFlatIP] = None):
    """Persist FAISS index to disk."""
    idx = index or _faiss_index
    if idx is None:
        logger.warning("No FAISS index to save.")
        return
    os.makedirs(FAISS_DIR, exist_ok=True)
    faiss.write_index(idx, _index_path())
    logger.info("FAISS index saved to %s (%d vectors).", _index_path(), idx.ntotal)


def load_faiss_index() -> Optional[faiss.IndexFlatIP]:
    """Load FAISS index from disk if it exists."""
    global _faiss_index
    path = _index_path()
    if os.path.exists(path):
        _faiss_index = faiss.read_index(path)
        logger.info("FAISS index loaded from %s (%d vectors).", path, _faiss_index.ntotal)
        return _faiss_index
    logger.info("No FAISS index found on disk.")
    return None


def get_faiss_index() -> Optional[faiss.IndexFlatIP]:
    global _faiss_index
    if _faiss_index is None:
        load_faiss_index()
    return _faiss_index


# =====================================================================
#  Full PDF processing pipeline
# =====================================================================

async def process_pdf(filepath: str, filename: str, progress_callback=None) -> int:
    """
    End-to-end pipeline:
      1. Extract text from PDF
      2. Chunk with RecursiveCharacterTextSplitter
      3. Batch-embed with delays & retries
      4. Build & save FAISS index
      5. Persist chunks + embeddings to JSON
    Returns document ID.
    """
    import firebase_client as db  # local import to avoid circular

    logger.info("═══ Starting PDF processing pipeline ═══")
    if progress_callback:
        progress_callback("Extracting text from PDF …", 0.1)

    # 1. Extract text
    full_text, page_count = extract_text_from_pdf(filepath)

    if progress_callback:
        progress_callback(f"Extracted {len(full_text)} chars from {page_count} pages. Chunking …", 0.2)

    # 2. Chunk
    chunks = create_chunks(full_text)

    if progress_callback:
        progress_callback(f"Created {len(chunks)} chunks. Generating embeddings …", 0.35)

    # 3. Embed
    chunk_texts = [c["text"] for c in chunks]
    embeddings = generate_embeddings_batched(chunk_texts, batch_size=20, inter_batch_delay=1.5)

    if progress_callback:
        progress_callback("Building FAISS index …", 0.7)

    # 4. Build & save FAISS index
    index = build_faiss_index(embeddings)
    save_faiss_index(index)

    if progress_callback:
        progress_callback("Storing chunks to database …", 0.85)

    # 5. Store in local DB
    doc_id = db.store_document(filename)
    embeddings_list = embeddings.tolist()
    db.store_chunks_batch(doc_id, chunks, embeddings_list)

    if progress_callback:
        progress_callback("Processing complete! ✅", 1.0)

    logger.info("═══ PDF processing complete — %d chunks stored ═══", len(chunks))
    return doc_id


# =====================================================================
#  Query pipeline — retrieve & generate
# =====================================================================

def search_faiss(query_embedding: np.ndarray, top_k: int = 5) -> List[Tuple[int, float]]:
    """Search FAISS index. Returns list of (chunk_index, score)."""
    index = get_faiss_index()
    if index is None or index.ntotal == 0:
        logger.warning("FAISS index is empty or missing.")
        return []

    # Normalise query vector
    qvec = query_embedding.reshape(1, -1).astype("float32")
    faiss.normalize_L2(qvec)

    scores, indices = index.search(qvec, top_k)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx >= 0:
            results.append((int(idx), float(score)))
    return results


async def retrieve_and_generate(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Full query pipeline:
      1. Embed query with the same model
      2. FAISS similarity search → top_k chunks
      3. Build context prompt
      4. Call Gemini LLM
      5. Return answer + sources
    """
    import firebase_client as db

    logger.info("═══ Query pipeline: '%s' ═══", query)

    # 1. Embed query
    model = get_embedding_model()
    query_vec = model.encode([query], convert_to_numpy=True)[0]

    # 2. FAISS search
    faiss_results = search_faiss(query_vec, top_k=top_k)

    if not faiss_results:
        return {
            "answer": "No relevant documents found. Please upload a PDF first.",
            "sources": [],
            "retrieved_chunks": [],
        }

    # 3. Fetch chunk texts from DB
    all_chunks = db.get_all_chunks()
    chunk_map = {c.get("chunk_index", i): c for i, c in enumerate(all_chunks)}

    retrieved = []
    for idx, score in faiss_results:
        chunk = chunk_map.get(idx, {})
        retrieved.append({
            "chunk_index": idx,
            "score": round(score, 4),
            "text": chunk.get("text", ""),
            "page_estimate": chunk.get("page_estimate", 0),
        })

    logger.info("Retrieved %d chunks (scores: %s).",
                len(retrieved), [r["score"] for r in retrieved])

    # 4. Build context
    context_blocks = []
    for i, r in enumerate(retrieved):
        context_blocks.append(
            f"[Source {i+1}] (Similarity: {r['score']:.4f}):\n{r['text']}"
        )
    context = "\n\n---\n\n".join(context_blocks)

    prompt = f"""You are an expert investment analysis assistant.
Answer the user's question based STRICTLY on the provided context.
If the answer is not in the context, say "I don't have enough information from the uploaded documents to answer this."
Do NOT hallucinate. Provide a clear, structured answer in markdown.

Context:
{context}

Question:
{query}

Answer:
"""

    # 5. Call Gemini
    answer_text = _call_gemini(prompt)

    return {
        "answer": answer_text,
        "sources": [
            {"id": r["chunk_index"], "score": r["score"], "text": r["text"]}
            for r in retrieved
        ],
        "retrieved_chunks": retrieved,
    }

def _call_gemini(prompt: str) -> str:
    """Try Gemini LLM, fall back to local answer synthesis on any error."""
    api_key = os.getenv("GEMINI_API_KEY")

    # ── Try Gemini first ──
    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model_llm = genai.GenerativeModel("gemini-2.0-flash")

            def _generate():
                return model_llm.generate_content(prompt)

            response = retry_with_backoff(_generate, max_retries=2, base_delay=3.0)
            logger.info("Gemini LLM answer generated successfully.")
            return response.text
        except Exception as e:
            logger.warning("Gemini LLM failed (%s). Using local synthesis.", e)

    # ── Local answer synthesis (no API needed) ──
    return _synthesize_local_answer(prompt)


def _synthesize_local_answer(prompt: str) -> str:
    """
    Generate a structured answer from retrieved context WITHOUT an LLM.
    Extracts context and question from the prompt, then formats key passages.
    """
    try:
        # Parse out context and question from the prompt
        context_section = prompt.split("Context:")[1].split("Question:")[0].strip()
        question = prompt.split("Question:")[1].split("Answer:")[0].strip()
    except (IndexError, ValueError):
        return "Unable to parse the query context."

    # Split into individual source blocks
    sources = context_section.split("---")
    source_texts = []
    for src in sources:
        src = src.strip()
        if not src:
            continue
        # Remove the [Source N] header line
        lines = src.split("\n", 1)
        text = lines[1].strip() if len(lines) > 1 else lines[0].strip()
        if text:
            source_texts.append(text)

    if not source_texts:
        return "No relevant information found in the uploaded documents."

    # Build a clean, structured answer
    answer_parts = []
    answer_parts.append(f"## Answer: {question}\n")
    answer_parts.append("Based on the uploaded investment documents, here are the most relevant findings:\n")

    for i, text in enumerate(source_texts[:5], 1):
        # Clean up the text — take meaningful sentences
        sentences = [s.strip() for s in text.replace("\n", " ").split(". ") if len(s.strip()) > 20]
        if sentences:
            clean_text = ". ".join(sentences[:4])
            if not clean_text.endswith("."):
                clean_text += "."
            answer_parts.append(f"**Key Insight {i}:**\n> {clean_text}\n")

    answer_parts.append("\n---\n*📖 Answer synthesized locally from retrieved document chunks.*")

    return "\n".join(answer_parts)


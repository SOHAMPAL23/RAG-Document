"""
FastAPI Backend — RAG Investment Analysis
==========================================
Endpoints for PDF upload, querying, chunk inspection, and system status.
"""

# ── Prevent transformers from importing TensorFlow (avoids protobuf conflict) ──
import os
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["USE_TF"] = "0"
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import firebase_client as db
import rag
import os
import shutil
from dotenv import load_dotenv
import logging

# ------------------------------------------------------------------ setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("API")

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

app = FastAPI(title="RAG Investment API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_PROGRESS = {"status": "idle", "message": "", "progress": 0.0}


# ------------------------------------------------------------------ lifecycle

@app.on_event("startup")
async def startup_event():
    logger.info("Starting RAG Investment API …")
    db.init_db()
    rag.get_embedding_model()
    rag.load_faiss_index()
    logger.info("Startup complete.")


# ------------------------------------------------------------------ endpoints

@app.get("/health")
async def health():
    return {"status": "ok", "message": "Server is running"}


@app.get("/status")
async def status():
    index = rag.get_faiss_index()
    return {
        "status": "ok",
        "db_stats": {
            "chunks_count": db.get_chunk_count(),
            "faiss_vectors": index.ntotal if index else 0,
        },
    }


@app.post("/upload")
async def upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    global UPLOAD_PROGRESS
    try:
        logger.info("Upload started: %s", file.filename)
        UPLOAD_PROGRESS = {"status": "uploading", "message": f"Saving {file.filename} …", "progress": 0.05}

        os.makedirs("tmp", exist_ok=True)
        filepath = f"tmp/{file.filename}"
        with open(filepath, "wb") as f:
            shutil.copyfileobj(file.file, f)

        UPLOAD_PROGRESS = {"status": "processing", "message": "Processing PDF …", "progress": 0.1}

        async def _process(fp, fn):
            global UPLOAD_PROGRESS
            try:
                def _progress_cb(msg, pct):
                    global UPLOAD_PROGRESS
                    UPLOAD_PROGRESS = {"status": "processing", "message": msg, "progress": pct}

                await rag.process_pdf(fp, fn, progress_callback=_progress_cb)
                UPLOAD_PROGRESS = {"status": "completed", "message": "Ready to query! ✅", "progress": 1.0}
            except Exception as e:
                logger.error("Processing error: %s", e)
                UPLOAD_PROGRESS = {"status": "error", "message": str(e), "progress": 0}

        background_tasks.add_task(_process, filepath, file.filename)
        return {"message": "Upload started", "filename": file.filename}

    except Exception as e:
        logger.error("Upload error: %s", e)
        UPLOAD_PROGRESS = {"status": "error", "message": str(e), "progress": 0}
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/upload/progress")
async def get_progress():
    return UPLOAD_PROGRESS


@app.get("/chunks")
async def get_chunks(limit: int = 20, offset: int = 0):
    chunks = db.get_chunks_paginated(limit, offset)
    total = db.get_chunk_count()

    return {
        "chunks": [
            {
                "id": c.get("chunk_id", c.get("id", i)),
                "document_id": c.get("document_id", 0),
                "text_content": c.get("text", ""),
                "embedding": c.get("embedding", []),
                "page_estimate": c.get("page_estimate", 0),
            }
            for i, c in enumerate(chunks)
        ],
        "total": total,
    }


@app.get("/debug")
async def debug():
    samples = db.get_sample_chunks_for_debug(limit=3)
    model = rag.get_embedding_model()
    return {
        "status": "debug",
        "model": "all-MiniLM-L6-v2",
        "embedding_dimension": model.get_sentence_embedding_dimension(),
        "total_chunks": db.get_chunk_count(),
        "sample_chunks": samples,
    }


class QueryRequest(BaseModel):
    query: str


@app.post("/query")
async def query(req: QueryRequest):
    try:
        logger.info("Query: %s", req.query)
        result = await rag.retrieve_and_generate(req.query)
        return result
    except Exception as e:
        logger.error("Query error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/reset")
async def reset():
    db.delete_all_chunks()
    logger.info("Database reset.")
    return {"message": "Database reset successful"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

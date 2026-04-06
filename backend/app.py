"""
Streamlit UI — RAG Investment Analysis
========================================
Premium dark-themed interface for:
  • PDF upload with real-time progress
  • Query interface with retrieved-chunk display
  • Chunk & embedding inspector
  • System status dashboard

Run:  streamlit run app.py
"""

# ── Prevent transformers from importing TensorFlow (avoids protobuf conflict) ──
import os
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["USE_TF"] = "0"

import streamlit as st
import sys
import time
import json
import shutil
import asyncio
import logging
from pathlib import Path

# Ensure backend modules are importable
sys.path.insert(0, os.path.dirname(__file__))

import rag
import firebase_client as db
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logger = logging.getLogger("StreamlitUI")

# =====================================================================
#  Page config & custom CSS
# =====================================================================

st.set_page_config(
    page_title="RAG Invest — Stock Market & Investment Analysis",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    /* ---- Global ---- */
    .stApp {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
        color: #e0e0e0;
    }
    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] {
        background: #12122a;
        border-right: 1px solid #2a2a4a;
    }
    /* ---- Cards ---- */
    .glass-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        backdrop-filter: blur(12px);
    }
    .glass-card h4 { margin-top: 0; color: #a78bfa; }
    /* ---- Source cards ---- */
    .source-card {
        background: rgba(167,139,250,0.06);
        border-left: 3px solid #a78bfa;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }
    .source-card .score {
        display: inline-block;
        background: #a78bfa;
        color: #0f0f1a;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 0.8rem;
    }
    /* ---- Chunk table ---- */
    .chunk-row {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
    }
    /* ---- Header ---- */
    .hero-title {
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(90deg, #a78bfa, #6dd5ed);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .hero-sub {
        color: #888;
        font-size: 1rem;
        margin-top: 0;
    }
    /* ---- Metrics ---- */
    div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 0.8rem;
    }
    /* ---- Buttons ---- */
    .stButton > button {
        background: linear-gradient(135deg, #7c3aed, #a78bfa) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.6rem 2rem !important;
        font-weight: 600 !important;
        transition: transform 0.15s !important;
    }
    .stButton > button:hover {
        transform: scale(1.03) !important;
    }
    /* ---- Embedding preview ---- */
    .embedding-box {
        background: #0d0d1a;
        border: 1px solid #2a2a4a;
        border-radius: 8px;
        padding: 0.8rem;
        font-family: 'Courier New', monospace;
        font-size: 0.78rem;
        overflow-x: auto;
        color: #6dd5ed;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# =====================================================================
#  Session state defaults
# =====================================================================

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "processing" not in st.session_state:
    st.session_state.processing = False


# =====================================================================
#  Helper: run async from sync Streamlit
# =====================================================================

def run_async(coro):
    """Run an async coroutine from synchronous Streamlit."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# =====================================================================
#  Initialise models & index on first run
# =====================================================================

@st.cache_resource(show_spinner=False)
def init_system():
    """Load embedding model & FAISS index once."""
    db.init_db()
    rag.get_embedding_model()
    rag.load_faiss_index()
    return True

with st.spinner("🔄 Loading embedding model & FAISS index …"):
    init_system()


# =====================================================================
#  SIDEBAR — Upload & System Info
# =====================================================================

with st.sidebar:
    st.markdown('<p class="hero-title">📈 RAG Invest</p>', unsafe_allow_html=True)
    st.markdown('<p class="hero-sub">Stock Market & Investment Analysis</p>', unsafe_allow_html=True)
    st.divider()

    # ---- System stats ----
    chunk_count = db.get_chunk_count()
    index = rag.get_faiss_index()
    faiss_count = index.ntotal if index else 0

    c1, c2 = st.columns(2)
    c1.metric("Chunks", f"{chunk_count:,}")
    c2.metric("FAISS Vectors", f"{faiss_count:,}")

    st.divider()

    # ---- PDF Upload ----
    st.subheader("📄 Upload PDF")
    uploaded_file = st.file_uploader(
        "Drop your investment PDF here",
        type=["pdf"],
        label_visibility="collapsed",
    )

    if uploaded_file and not st.session_state.processing:
        if st.button("🚀 Process PDF", use_container_width=True):
            st.session_state.processing = True

            # Save file
            os.makedirs("tmp", exist_ok=True)
            filepath = f"tmp/{uploaded_file.name}"
            with open(filepath, "wb") as f:
                f.write(uploaded_file.getbuffer())

            progress_bar = st.progress(0.0, text="Starting …")
            status_text = st.empty()

            def progress_cb(msg, pct):
                progress_bar.progress(min(pct, 1.0), text=msg)
                status_text.caption(msg)

            try:
                run_async(rag.process_pdf(filepath, uploaded_file.name, progress_callback=progress_cb))
                st.success(f"✅ Processed **{uploaded_file.name}** — {db.get_chunk_count()} chunks stored!")
            except Exception as e:
                st.error(f"❌ Error: {e}")
            finally:
                st.session_state.processing = False
                st.rerun()

    st.divider()

    # ---- Reset ----
    if st.button("🗑️ Reset Database", use_container_width=True, type="secondary"):
        db.delete_all_chunks()
        st.success("Database cleared.")
        st.rerun()


# =====================================================================
#  MAIN AREA — Tabs
# =====================================================================

tab_query, tab_inspector, tab_debug = st.tabs(["💬 Query", "🔍 Chunk Inspector", "🛠️ Debug"])

# =====================================================================
#  TAB 1 — Query Interface
# =====================================================================

with tab_query:
    st.markdown("### Ask about your investment documents")
    st.caption("The system retrieves the most relevant chunks and generates a grounded answer using Gemini.")

    # Suggested queries
    st.markdown("**Try these queries:**")
    suggestions = [
        "how to deal with brokerage houses?",
        "what is theory of diversification?",
        "how to become intelligent investor?",
        "how to do business valuation?",
        "what is putting all eggs in one basket analogy?",
    ]
    cols = st.columns(len(suggestions))
    for i, (col, q) in enumerate(zip(cols, suggestions)):
        with col:
            if st.button(q, key=f"sug_{i}", use_container_width=True):
                st.session_state["prefill_query"] = q

    # Query input
    query_text = st.text_input(
        "Your question:",
        value=st.session_state.pop("prefill_query", ""),
        placeholder="e.g. What is the margin of safety?",
    )

    if st.button("🔎 Search & Answer", disabled=(not query_text), use_container_width=True):
        if db.get_chunk_count() == 0:
            st.warning("⚠️ No documents uploaded yet. Please upload a PDF first.")
        else:
            with st.spinner("Retrieving chunks & generating answer …"):
                result = run_async(rag.retrieve_and_generate(query_text))

            # ---- Retrieved chunks ----
            retrieved = result.get("retrieved_chunks", result.get("sources", []))
            if retrieved:
                st.markdown("#### 📚 Retrieved Chunks")
                for i, chunk in enumerate(retrieved):
                    score = chunk.get("score", chunk.get("similarity", 0))
                    text = chunk.get("text", "")
                    st.markdown(
                        f"""<div class="source-card">
                            <span class="score">Score: {score:.4f}</span>
                            <p style="margin-top:0.5rem">{text[:500]}{'…' if len(text)>500 else ''}</p>
                        </div>""",
                        unsafe_allow_html=True,
                    )

            # ---- Answer ----
            st.markdown("#### 💡 Answer")
            st.markdown(
                f'<div class="glass-card">{result.get("answer", "No answer generated.")}</div>',
                unsafe_allow_html=True,
            )

            # Save to history
            st.session_state.chat_history.append({
                "query": query_text,
                "answer": result.get("answer", ""),
                "sources_count": len(retrieved),
            })

    # ---- Chat history ----
    if st.session_state.chat_history:
        st.divider()
        st.markdown("#### 📝 Query History")
        for i, entry in enumerate(reversed(st.session_state.chat_history)):
            with st.expander(f"Q: {entry['query']}  ({entry['sources_count']} sources)", expanded=False):
                st.markdown(entry["answer"])


# =====================================================================
#  TAB 2 — Chunk & Embedding Inspector
# =====================================================================

with tab_inspector:
    st.markdown("### Chunk & Embedding Inspector")
    total = db.get_chunk_count()

    if total == 0:
        st.info("No chunks in database. Upload a PDF to get started.")
    else:
        st.caption(f"**{total:,}** chunks stored  •  Showing embedding samples for first 2 chunks")

        # ---- Embedding samples ----
        st.markdown("#### 🧬 Embedding Samples (first 2 chunks)")
        samples = db.get_chunks_paginated(limit=2)
        for i, chunk in enumerate(samples):
            emb = chunk.get("embedding", [])
            dim = chunk.get("embedding_full_dim", len(emb))
            with st.container():
                st.markdown(f'<div class="glass-card"><h4>Chunk #{i+1}</h4>', unsafe_allow_html=True)
                st.markdown(f"**Text preview:** {chunk.get('text', '')[:200]}…")
                st.markdown(f"**Embedding dim:** {dim}")
                emb_str = ", ".join(f"{v:.6f}" for v in emb[:10])
                st.markdown(
                    f'<div class="embedding-box">[{emb_str}, …]</div></div>',
                    unsafe_allow_html=True,
                )

        st.divider()

        # ---- Paginated chunk list ----
        st.markdown("#### 📋 All Chunks")
        page_size = 10
        page = st.number_input("Page", min_value=1, max_value=max(1, (total + page_size - 1) // page_size), value=1)
        offset = (page - 1) * page_size
        chunks = db.get_chunks_paginated(limit=page_size, offset=offset)

        for c in chunks:
            idx = c.get("chunk_index", "?")
            text = c.get("text", "")
            st.markdown(
                f"""<div class="chunk-row">
                    <strong>Chunk {idx}</strong> &nbsp;|&nbsp; Page est. {c.get('page_estimate', '?')}
                    <br><span style="color:#aaa">{text[:300]}{'…' if len(text)>300 else ''}</span>
                </div>""",
                unsafe_allow_html=True,
            )

        st.caption(f"Page {page} of {max(1, (total + page_size - 1) // page_size)}")


# =====================================================================
#  TAB 3 — Debug
# =====================================================================

with tab_debug:
    st.markdown("### System Debug Info")
    model = rag.get_embedding_model()

    c1, c2, c3 = st.columns(3)
    c1.metric("Embedding Model", "all-MiniLM-L6-v2")
    c2.metric("Embedding Dim", model.get_sentence_embedding_dimension())
    c3.metric("Total Chunks", db.get_chunk_count())

    idx = rag.get_faiss_index()
    st.metric("FAISS Index Vectors", idx.ntotal if idx else 0)

    st.divider()

    st.markdown("#### Sample Chunks")
    samples = db.get_sample_chunks_for_debug(limit=3)
    if samples:
        for s in samples:
            st.json(s)
    else:
        st.info("No chunks available.")

    st.divider()
    st.markdown("#### Environment")
    st.json({
        "GEMINI_API_KEY": "***" + os.getenv("GEMINI_API_KEY", "")[-4:] if os.getenv("GEMINI_API_KEY") else "NOT SET",
        "FAISS_DIR": rag.FAISS_DIR,
        "CHUNKS_DB": rag.CHUNKS_DB,
        "FAISS_INDEX_EXISTS": os.path.exists(rag._index_path()),
    })

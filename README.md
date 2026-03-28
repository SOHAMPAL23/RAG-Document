# RAG Investment System

A complete, production-grade Retrieval-Augmented Generation (RAG) system for investment analysis.

## Features
- **Frontend**: React 18, Vite, Tailwind CSS with a modern, dark professional UI.
- **Backend**: Python 3.11, FastAPI, Asyncpg.
- **Database**: NeonDB PostgreSQL with pgvector (768 dimensions).
- **AI/LLM**: Google Gemini 1.5 Flash for generation, text-embedding-004 for embeddings.
- **Document Processing**: PyMuPDF for parsing, sliding window chunking (500 words, 50 overlap).
- **Core capabilities**: PDF upload, progress tracking, vector inspection, and conversational query interface with source citations.

## Prerequisites
- Python 3.11+
- Node.js 18+
- NeonDB Account
- Google Gemini API Key

## Setup Instructions

### 1. Database (NeonDB) Setup
1. Create a new project in NeonDB.
2. The backend will automatically initialize the `pgvector` extension and create the required `documents` and `chunks` tables upon startup. You just need the connection URL.

### 2. Backend Setup
1. Navigate to the `backend` folder:
   ```bash
   cd backend
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables in `backend/.env` (use `.env.example` as a template):
   ```env
   NEON_DB_URL=
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
4. Run the API server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

### 3. Frontend Setup
1. Navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```

## Verification Steps
1. Open the UI at `http://localhost:5173`.
2. Ensure the backend is running at `http://localhost:8000`.
3. Drag and drop an investment PDF to the **Upload Knowledge** panel.
4. Watch the status change to "Ready to query!".
5. In the **pgvector DB Inspector** (right panel), you will see the stored chunks and part of their 768-dimensional embeddings. Click to expand.
6. In the **Assistant** chat (center panel), click one of the suggested chips (e.g. "how to become intelligent investor?").
7. The application will answer your question and provide citations for the context chunks it used, complete with similarity scores from pgvector!

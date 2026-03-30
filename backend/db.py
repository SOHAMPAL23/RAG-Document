import asyncpg
from pgvector.asyncpg import register_vector
import os

pool = None

async def init_pool():
    global pool
    print("Initializing Database Connection Pool...")
    
    async def init(conn):
        await register_vector(conn)
        
    db_url = os.getenv("NEON_DB_URL")
    if not db_url:
        raise ValueError("NEON_DB_URL environment variable is not set")
        
    # Ensure extension exists first using a single connection
    temp_conn = await asyncpg.connect(db_url)
    await temp_conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    await temp_conn.close()
        
    pool = await asyncpg.create_pool(db_url, init=init)
    
    async with pool.acquire() as conn:
        print("Ensuring tables exist...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                filename TEXT NOT NULL,
                upload_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id SERIAL PRIMARY KEY,
                document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                text_content TEXT NOT NULL,
                embedding vector(3072)
            )
        """)
    print("Database initialized.")

async def close_pool():
    if pool:
        print("Closing database pool...")
        await pool.close()

async def store_document(filename: str) -> int:
    async with pool.acquire() as conn:
        doc_id = await conn.fetchval(
            "INSERT INTO documents (filename) VALUES ($1) RETURNING id", 
            filename
        )
        print(f"Stored document '{filename}' with ID {doc_id}")
        return doc_id

async def store_chunks(document_id: int, texts: list[str], embeddings: list[list[float]]):
    print(f"Storing {len(texts)} chunks to NeonDB for document ID {document_id}...")
    async with pool.acquire() as conn:
        records = [(document_id, text, emb) for text, emb in zip(texts, embeddings)]
        await conn.executemany(
            "INSERT INTO chunks (document_id, text_content, embedding) VALUES ($1, $2, $3)",
            records
        )
    print("Chunks and embeddings stored successfully.")

async def get_chunks_count() -> int:
    async with pool.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM chunks")
        return count or 0

async def get_chunks(limit: int = 20, offset: int = 0) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, document_id, text_content, embedding 
            FROM chunks 
            ORDER BY id ASC 
            LIMIT $1 OFFSET $2
        """, limit, offset)
        return [dict(row) for row in rows]

async def search_similar_chunks(embedding: list[float], top_k: int = 5) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, text_content, embedding <=> $1 AS distance
            FROM chunks
            ORDER BY distance ASC
            LIMIT $2
        """, embedding, top_k)
        return [dict(row) for row in rows]

async def reset_db():
    print("Resetting Database (truncating tables)...")
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE documents CASCADE")
    print("Database reset complete.")

async def get_stats() -> dict:
    async with pool.acquire() as conn:
        docs = await conn.fetchval("SELECT COUNT(*) FROM documents")
        chunks = await conn.fetchval("SELECT COUNT(*) FROM chunks")
        return {"documents_count": docs, "chunks_count": chunks}

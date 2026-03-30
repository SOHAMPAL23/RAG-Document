import asyncio
import os
import asyncpg
from dotenv import load_dotenv

async def drop():
    load_dotenv()
    db_url = os.getenv("NEON_DB_URL")
    conn = await asyncpg.connect(db_url)
    await conn.execute("DROP TABLE IF EXISTS chunks CASCADE")
    await conn.execute("DROP TABLE IF EXISTS documents CASCADE")
    print("Tables dropped successfully.")
    await conn.close()
    
asyncio.run(drop())

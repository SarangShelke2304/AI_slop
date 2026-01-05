
import asyncio
import asyncpg
from urllib.parse import urlparse
from pathlib import Path
from src.config import settings
from src.utils.logger import logger

async def init_db():
    logger.info("Initializing database...")
    
    # Parse URL properly (removing asyncpg prefix if present for raw connection if needed)
    # But asyncpg.connect takes the DSN directly.
    # We just need to handle the %40 encoding if it was manually fixed in .env (it was).
    
    try:
        # Read schema file
        schema_path = Path("database_schema.sql")
        if not schema_path.exists():
            logger.error("database_schema.sql not found!")
            return

        with open(schema_path, "r", encoding="utf-8") as f:
            sql_script = f.read()

        # Connect to DB
        # Note: settings.DATABASE_URL starts with postgresql://
        # asyncpg handles this standard format.
        logger.info(f"Connecting to {settings.DATABASE_URL.split('@')[-1]}") # Log safe part
        
        conn = await asyncpg.connect(settings.DATABASE_URL)
        
        try:
            logger.info("Executing schema script...")
            # Execute the entire script
            await conn.execute(sql_script)
            logger.info("Database initialized successfully!")
            
        except Exception as e:
            logger.error(f"Failed to execute schema: {e}")
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(init_db())

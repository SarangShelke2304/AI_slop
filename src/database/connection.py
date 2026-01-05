
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings
from src.utils.logger import logger

# Convert postgres:// to postgresql+asyncpg:// for SQLAlchemy async engine
def get_async_db_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url

DATABASE_URL = get_async_db_url(settings.DATABASE_URL)

try:
    engine = create_async_engine(
        DATABASE_URL,
        echo=settings.LOG_LEVEL == "DEBUG",
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
    )
    
    async_session_factory = async_sessionmaker(
        engine, 
        autocommit=False, 
        autoflush=False, 
        expire_on_commit=False
    )
    logger.info("Database engine configured")

except Exception as e:
    logger.error(f"Failed to configure database engine: {e}")
    # We don't raise here to allow app to start, but DB ops will fail
    engine = None
    async_session_factory = None

@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions.
    Usage:
        async with get_db_session() as session:
            result = await session.execute(...)
    """
    if async_session_factory is None:
        raise RuntimeError("Database engine not initialized")
        
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

async def check_db_connection() -> bool:
    """Check if database is reachable."""
    try:
        if not engine:
            return False
        async with engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False

"""Async database engine and session dependency.

One engine per process (it owns the connection pool, like a Mongoose
connection). Each request gets its own short-lived AsyncSession via the
get_db dependency — FastAPI's Depends() plays the role Express middleware
plays, but the dependency can yield, so teardown (closing the session)
happens automatically after the response.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

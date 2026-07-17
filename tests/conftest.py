"""Test fixtures.

Tests run against a real PostgreSQL database (medilab_test), not mocks —
the booking flow's row-locking behavior only exists on a real database.
Each test gets a freshly created schema (drop_all/create_all), and the
app's get_db dependency is overridden to point at the test engine — the
FastAPI equivalent of injecting a test double.
"""
import asyncio
import sys

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.database import get_db
from app.main import app
from app.models import Base

# psycopg's async mode needs a selector event loop; Windows defaults to the
# Proactor loop. Irrelevant inside the Linux Docker image.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/medilab_test"

# NullPool: every operation gets a fresh connection, so connections never
# outlive a test's event loop.
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def fresh_schema():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
async def client():
    async def override_get_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def auth_headers(client):
    await client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "secret-pass-123", "full_name": "Test User"},
    )
    resp = await client.post(
        "/auth/login", json={"email": "user@example.com", "password": "secret-pass-123"}
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}

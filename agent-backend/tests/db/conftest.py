"""MySQL integration fixtures limited to the disposable CI service.

The old fixture read ``configs/application.yml`` and left rows in a shared
database. These tests now require one exact loopback DSN, synthetic credentials,
and disabled external integrations. The runner destroys the service and its
data when the job ends.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

PYTEST_USERNAME = "__pytest__"
PYTEST_TITLE_PREFIX = "[pytest] "

# Public, synthetic credentials for the single-use MySQL service in business-ci.yml.
CI_MYSQL_URL = "mysql+aiomysql://ci_runner:test-ci-only-1234@127.0.0.1:3306/ir_agent_ci"
_DISABLED_EXTERNAL_FLAGS = (
    "NACOS_ENABLED",
    "IR_FEISHU_ENABLED",
    "IR_SPOT_ENABLED",
    "IR_SPOT_DAILY_UPDATE_ENABLED",
)


def validated_ci_mysql_url() -> str:
    """Fail closed before opening any connection or creating any tables."""
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("DB integration tests require the disposable GitHub Actions runner")
    if os.environ.get("IR_TEST_MYSQL_URL") != CI_MYSQL_URL:
        raise RuntimeError("IR_TEST_MYSQL_URL must be the dedicated loopback CI database")
    if os.environ.get("IR_DB_URL") != CI_MYSQL_URL:
        raise RuntimeError("IR_DB_URL must match the dedicated loopback CI database")
    for name in _DISABLED_EXTERNAL_FLAGS:
        if os.environ.get(name, "").lower() != "false":
            raise RuntimeError(f"{name} must be false for DB integration tests")
    return CI_MYSQL_URL


@pytest.fixture
async def db_engine():
    """Check the checked-in SQL schema before yielding a disposable DB engine."""
    engine = create_async_engine(validated_ci_mysql_url(), poolclass=NullPool, future=True)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1 FROM ir_conversation LIMIT 0"))
            await connection.execute(text("SELECT 1 FROM ir_spot_station LIMIT 0"))
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncSession:
    """Commit semantics remain observable across sessions in the disposable DB."""
    maker = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session

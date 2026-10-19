"""MySQL integration fixtures limited to the disposable CI service.

The old fixture read ``configs/application.yml`` and left rows in a shared
database. These tests now require one exact loopback DSN, synthetic credentials,
and disabled external integrations. The runner destroys the service and its
data when the job ends.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.infrastructure.database.base import Base
from app.modules.calculation.infrastructure.persistence import orm as _calculation_orm  # noqa: F401
from app.modules.index_map.infrastructure.persistence import orm as _index_map_orm  # noqa: F401
from app.modules.policy_market.infrastructure.persistence import orm as _policy_market_orm  # noqa: F401
from app.modules.tie_line_map.infrastructure.persistence import orm as _tie_line_map_orm  # noqa: F401
from app.modules.trial_quota.infrastructure.persistence import orm as _trial_quota_orm  # noqa: F401

PYTEST_USERNAME = "__pytest__"
PYTEST_TITLE_PREFIX = "[pytest] "

# Public, synthetic credentials for the single-use MySQL service in business-ci.yml.
CI_MYSQL_URL = "mysql+aiomysql://ci_runner:ci-only-password@127.0.0.1:3306/ir_agent_ci"
_DISABLED_EXTERNAL_FLAGS = (
    "NACOS_ENABLED",
    "IR_FEISHU_ENABLED",
    "IR_SPOT_ENABLED",
    "IR_SPOT_DAILY_UPDATE_ENABLED",
)
_schema_ready = False


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
    """Create schema only inside the disposable database; dispose each engine."""
    global _schema_ready
    engine = create_async_engine(validated_ci_mysql_url(), poolclass=NullPool, future=True)
    try:
        if not _schema_ready:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            _schema_ready = True
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncSession:
    """Commit semantics remain observable across sessions in the disposable DB."""
    maker = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session

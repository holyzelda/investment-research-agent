"""DB 测试专用夹具：直连测试库 ir_agent（internal-3-60.example.invalid），真实插入、留痕不清理。

与纯逻辑单测分离：
- 纯逻辑测试走根 `tests/conftest.py`，`IR_DB_URL` 被覆盖为内存 sqlite，不碰库。
- 本目录测试连**真实测试库**，用 application.yml 里的 MySQL 串（不受 IR_DB_URL 影响）。

约定（便于你在库里筛/清测试痕迹）：
- 会话归属 `username='__pytest__'`，`title` 带 `[pytest]` 前缀。
- 清理示意（父表最后删）：
    DELETE t FROM ir_calculation_task t JOIN ir_conversation c ON t.conversation_id=c.id WHERE c.username='__pytest__';
    DELETE FROM ir_conversation WHERE username='__pytest__';
"""
from __future__ import annotations

import os

import yaml
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config.settings import CONFIG_DIR

# 测试留痕标记
PYTEST_USERNAME = "__pytest__"
PYTEST_TITLE_PREFIX = "[pytest] "


def _mysql_url() -> str:
    """从 application.yml 读测试库 MySQL 串（绕开 IR_DB_URL 的 sqlite 覆盖）。"""
    yml_path = os.path.join(CONFIG_DIR, "application.yml")
    with open(yml_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    url = (cfg.get("database") or {}).get("url")
    if not url or not url.startswith("mysql"):
        pytest.skip(f"application.yml 未配置 MySQL 测试库，跳过 DB 测试：{url!r}")
    return url


@pytest.fixture
async def db_engine():
    """函数级引擎：NullPool + 用后 dispose，避免连接在事件循环关闭后被 GC 报错。"""
    engine = create_async_engine(_mysql_url(), poolclass=NullPool, future=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncSession:
    """每个测试一个 session；提交后不回滚（留痕）。"""
    maker = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session

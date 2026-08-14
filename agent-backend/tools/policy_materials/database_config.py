"""政策材料任务通过统一 Settings 获取数据库配置。"""

import asyncio
import sys
from pathlib import Path

from sqlalchemy.engine import make_url


BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def database_config_from_url(database_url: str) -> dict[str, object]:
    """将 Settings 中的 SQLAlchemy MySQL URL 转为 PyMySQL 参数。"""
    if not isinstance(database_url, str) or not database_url.strip():
        raise RuntimeError("Settings.database.url 不能为空。")
    try:
        url = make_url(database_url.strip())
    except Exception as exc:
        raise RuntimeError(f"database.url 格式无效：{exc}") from exc
    if url.get_backend_name() != "mysql":
        raise RuntimeError("database.url 必须是 MySQL 连接串。")
    missing = [
        name
        for name, value in {
            "host": url.host,
            "username": url.username,
            "password": url.password,
            "database": url.database,
        }.items()
        if value in (None, "")
    ]
    if missing:
        raise RuntimeError(f"database.url 缺少必要字段：{', '.join(missing)}")

    return {
        "host": url.host,
        "port": url.port or 3306,
        "user": url.username,
        "password": url.password,
        "database": url.database,
        "charset": url.query.get("charset", "utf8mb4"),
        "connect_timeout": 15,
        "read_timeout": 30,
        "write_timeout": 30,
        "autocommit": False,
    }


async def _load_database_config() -> dict[str, object]:
    from app.core.config.settings import get_settings
    from app.infrastructure.nacos.client import cleanup_nacos, init_nacos_config

    try:
        await init_nacos_config(register_service=False)
        return database_config_from_url(get_settings().database.url)
    finally:
        await cleanup_nacos()


def load_database_config() -> dict[str, object]:
    """加载 Nacos 远端配置后，从统一 Settings 返回数据库连接参数。"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_load_database_config())
    raise RuntimeError("load_database_config 不能在运行中的异步事件循环内调用。")

"""联络线地图 HTTP 接口（只读）。

- GET /ir/tie-lines        列表 + 静态统计 + 筛选项（地图渲染主数据）
- GET /ir/tie-lines/{id}   单条线路完整静态详情（右侧详情面板）

联络线为公共基础数据：仍走统一 DB 会话依赖，但不做用户归属过滤。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ok
from app.infrastructure.database.session import get_db_session
from app.modules.tie_line_map.application.tie_line_service import TieLineService
from app.modules.tie_line_map.interface.serializers import (
    serialize_line_detail,
    serialize_lines,
)

router = APIRouter(prefix="/ir/tie-lines", tags=["tie-line-map"])
_service = TieLineService()


@router.get("")
async def list_tie_lines(session: AsyncSession = Depends(get_db_session)):
    lines = await _service.list_lines(session)
    return ok(serialize_lines(lines))


@router.get("/{line_id}")
async def get_tie_line(line_id: int, session: AsyncSession = Depends(get_db_session)):
    line = await _service.get_line(session, line_id=line_id)
    return ok(serialize_line_detail(line))

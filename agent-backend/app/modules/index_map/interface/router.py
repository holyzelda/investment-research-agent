"""全国指数地图 HTTP 查询接口。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationException
from app.core.response import ok
from app.infrastructure.database.session import get_db_session
from app.modules.index_map.application.index_map_service import IndexMapService
from app.modules.index_map.interface.serializers import (
    serialize_overview,
    serialize_periods,
    serialize_province_detail,
)

router = APIRouter(prefix="/ir/index-map", tags=["index-map"])
_service = IndexMapService()


def _require_period(value: str | None) -> str:
    period = (value or "").strip()
    if not period:
        raise ValidationException("period 不能为空")
    return period


@router.get("/periods")
async def list_periods(session: AsyncSession = Depends(get_db_session)):
    return ok(serialize_periods(await _service.list_periods(session)))


@router.get("/overview")
async def get_overview(
    period: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
):
    return ok(serialize_overview(await _service.get_overview(session, period=_require_period(period))))


@router.get("/provinces/{province_code}")
async def get_province_detail(
    province_code: str,
    period: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
):
    code = province_code.strip()
    if not code:
        raise ValidationException("provinceCode 不能为空")
    detail = await _service.get_province_detail(
        session, period=_require_period(period), province_code=code
    )
    return ok(serialize_province_detail(detail))

"""测算台账 HTTP 端点：当前用户已完成测算的查询与省份选项。"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationException
from app.core.response import ok
from app.infrastructure.database.session import get_db_session
from app.modules.calculation.application.calculation_ledger_service import CalculationLedgerService
from app.modules.platform_access.domain.models import CurrentUser
from app.modules.platform_access.interface.deps import get_current_user

router = APIRouter(prefix="/ir/calc/ledger", tags=["calculation-ledger"])
_service = CalculationLedgerService()


@router.get("/provinces")
async def list_ledger_provinces(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """筛选项：当前用户已完成测算中实际出现过的省份。"""
    return ok({"items": await _service.list_provinces(session, user_id=user.user_id)})


@router.get("")
async def list_ledger_records(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    keyword: Optional[str] = Query(None, max_length=255, description="按会话名称模糊搜索"),
    province: Optional[list[str]] = Query(None, description="省份多选，重复传参"),
    start_date: Optional[date] = Query(None, description="测算时间起（含当天）"),
    end_date: Optional[date] = Query(None, description="测算时间止（含当天）"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    """已完成测算列表：按测算时间倒序分页，报告状态随行返回。"""
    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValidationException("测算时间范围无效：开始日期晚于结束日期")
    return ok(await _service.list_records(
        session,
        user_id=user.user_id,
        keyword=keyword,
        provinces=province,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    ))

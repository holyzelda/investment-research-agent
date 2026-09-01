"""测算台账 HTTP 端点：可见范围内已完成测算的查询、省份选项与发起人选项。

可见范围每请求实时向用户管理中心确认（get_user_scope），不接受前端上报的 isAdmin
或用户 id：管理员筛选参数只能在实时可见成员内收敛，越权 id 直接丢弃。
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationException
from app.core.response import ok
from app.infrastructure.database.session import get_db_session
from app.modules.calculation.application.calculation_ledger_service import CalculationLedgerService
from app.modules.platform_access.domain.models import UserScope
from app.modules.platform_access.interface.deps import get_user_scope

router = APIRouter(prefix="/ir/calc/ledger", tags=["calculation-ledger"])
_service = CalculationLedgerService()


def _parse_initiators(raw: Optional[str]) -> Optional[list[str]]:
    """发起人多选为单个逗号分隔参数；未传或清空表示全部可见用户。"""
    if raw is None:
        return None
    return [item.strip() for item in raw.split(",") if item.strip()] or None


@router.get("/users")
async def list_ledger_users(scope: UserScope = Depends(get_user_scope)):
    """台账可见的发起人选项与当前用户是否为管理员。

    普通用户 isAdmin=false、users 只含本人；前端据此决定是否展示发起人筛选与列。
    """
    return ok({
        "isAdmin": scope.is_admin,
        "users": [
            {"userId": user.user_id, "nickName": user.nick_name}
            for user in scope.users
        ],
    })


@router.get("/provinces")
async def list_ledger_provinces(
    scope: UserScope = Depends(get_user_scope),
    session: AsyncSession = Depends(get_db_session),
):
    """筛选项：可见范围内已完成测算中实际出现过的省份。"""
    return ok({"items": await _service.list_provinces(session, scope=scope)})


@router.get("")
async def list_ledger_records(
    scope: UserScope = Depends(get_user_scope),
    session: AsyncSession = Depends(get_db_session),
    keyword: Optional[str] = Query(None, max_length=255, description="按会话名称或发起人昵称模糊搜索"),
    province: Optional[list[str]] = Query(None, description="省份多选，重复传参"),
    initiator_user_ids: Optional[str] = Query(
        None, max_length=1024, description="发起人多选，逗号分隔；仅管理员生效"),
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
        scope=scope,
        initiator_user_ids=_parse_initiators(initiator_user_ids),
        keyword=keyword,
        provinces=province,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    ))

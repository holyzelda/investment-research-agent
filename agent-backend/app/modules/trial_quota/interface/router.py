"""Authenticated endpoint used only to display today's trial quota."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ok
from app.infrastructure.database.session import get_db_session
from app.modules.platform_access.domain.models import CurrentUser
from app.modules.platform_access.interface.deps import get_current_user
from app.modules.trial_quota.application.trial_quota_service import TrialQuotaService
from app.modules.trial_quota.application.trial_role_service import TrialRoleService
from app.modules.trial_quota.interface.deps import (
    get_trial_quota_service,
    get_trial_role_service,
)

router = APIRouter(prefix="/ir/trial", tags=["trial-quota"])


@router.get("/quota")
async def get_trial_quota(
    user: CurrentUser = Depends(get_current_user),
    role_service: TrialRoleService = Depends(get_trial_role_service),
    quota_service: TrialQuotaService = Depends(get_trial_quota_service),
    session: AsyncSession = Depends(get_db_session),
):
    if not await role_service.is_trial(user.user_id):
        return ok({"isTrial": False})
    status = await quota_service.get_today_status(session, user.user_id)
    return ok({"isTrial": True, **status})

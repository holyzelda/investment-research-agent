"""Trial-account resolution backed by organization/users."""
from __future__ import annotations

from app.core.config.settings import get_settings
from app.core.constants import HttpStatus
from app.core.exceptions import BusinessException
from app.modules.platform_access.infrastructure.user_center_client import UserCenterClient


class TrialRoleUnavailable(BusinessException):
    """The upstream user service did not provide a trustworthy answer."""

    def __init__(self):
        super().__init__("试用权限校验失败，请稍后重试", code=HttpStatus.SERVICE_UNAVAILABLE)


def _user_id(record: object) -> str | None:
    if not isinstance(record, dict):
        return None
    value = record.get("userId")
    if value is None or isinstance(value, bool):
        return None
    value = str(value).strip()
    return value or None


def _role_key(role: object) -> str | None:
    if isinstance(role, str):
        return role.strip() or None
    if not isinstance(role, dict):
        return None
    value = role.get("roleKey")
    if isinstance(value, dict):
        value = value.get("value")
    if value is None:
        value = role.get("value")
    if value is None or isinstance(value, bool):
        return None
    value = str(value).strip()
    return value or None


class TrialRoleService:
    def __init__(self, client: UserCenterClient | None = None):
        self._client = client or UserCenterClient(get_settings().user_center)

    async def is_trial(self, user_id: str) -> bool:
        records = await self._client.fetch_organization_users(user_id)
        if records is None:
            raise TrialRoleUnavailable()
        current = next((record for record in records if _user_id(record) == str(user_id)), None)
        if current is None:
            raise TrialRoleUnavailable()
        roles = current.get("roles") if isinstance(current, dict) else None
        if not isinstance(roles, list):
            raise TrialRoleUnavailable()
        return any(
            (key or "").lower().endswith("freetrial")
            for role in roles
            for key in [_role_key(role)]
        )

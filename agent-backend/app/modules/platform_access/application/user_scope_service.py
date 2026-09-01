"""可见范围解析：把用户管理中心的组织成员与角色，翻译成台账等查询的可见用户集合。

管理员判定只看当前用户自己那条记录的 roles：任一 roleKey 小写含 admin 即管理员，
roles 为空即普通用户。不按 roleName、昵称或返回条数推断。
管理员可见范围仅取 status="0" 的在用成员；停用成员一律不可见。
任何解析不出当前用户记录的情况都按普通用户降级，昵称回退请求身份里的 username。
"""
from __future__ import annotations

from typing import Optional

from app.core.config.settings import get_settings
from app.modules.platform_access.domain.models import (
    ADMIN_ROLE_KEY_KEYWORD,
    CurrentUser,
    OrganizationUser,
    UserScope,
)
from app.modules.platform_access.infrastructure.user_center_client import UserCenterClient

ACTIVE_STATUS = "0"


def _user_id_of(record: dict) -> Optional[str]:
    if not isinstance(record, dict):
        return None
    raw = record.get("userId")
    if raw is None or isinstance(raw, bool):
        return None
    user_id = str(raw).strip()
    return user_id or None


def _is_admin(record: dict) -> bool:
    roles = record.get("roles")
    if not isinstance(roles, list):
        return False
    return any(
        ADMIN_ROLE_KEY_KEYWORD in str(role.get("roleKey") or "").lower()
        for role in roles
        if isinstance(role, dict)
    )


class UserScopeService:
    def __init__(self, client: UserCenterClient | None = None):
        self._client = client or UserCenterClient(get_settings().user_center)

    async def resolve(self, user: CurrentUser) -> UserScope:
        records = await self._client.fetch_organization_users(user.user_id)
        current = next(
            (r for r in records or [] if _user_id_of(r) == str(user.user_id)), None
        )
        if current is None or not _is_admin(current):
            return self._self_only(user, current)
        users = [
            OrganizationUser(user_id=user_id, nick_name=str(record.get("nickName") or "").strip())
            for record in records
            if (user_id := _user_id_of(record)) and record.get("status") == ACTIVE_STATUS
        ]
        deduped = list({user.user_id: user for user in users}.values())
        if not any(u.user_id == str(user.user_id) for u in deduped):
            # 管理员自己被上游标为停用时不再是有效身份，按普通用户降级而不是放空范围。
            return self._self_only(user, current)
        return UserScope(current_user_id=str(user.user_id), is_admin=True, users=tuple(deduped))

    @staticmethod
    def _self_only(user: CurrentUser, record: Optional[dict]) -> UserScope:
        nick_name = str((record or {}).get("nickName") or "").strip() or user.username
        return UserScope(
            current_user_id=str(user.user_id),
            is_admin=False,
            users=(OrganizationUser(user_id=str(user.user_id), nick_name=nick_name),),
        )

"""平台接入上下文 · 领域模型（无框架依赖）。"""
from dataclasses import dataclass
from typing import Iterable

# 用户管理中心的角色标识含该关键字即视为管理员（roleKey 大小写不敏感，如 bjjzadmin）。
ADMIN_ROLE_KEY_KEYWORD = "admin"


@dataclass(frozen=True)
class CurrentUser:
    """当前用户：由平台身份中间件从固定 Header 解析后放入 request.state。"""

    user_id: str
    username: str


@dataclass(frozen=True)
class OrganizationUser:
    """用户管理中心返回的一名在用（status=0）组织成员。"""

    user_id: str
    nick_name: str


@dataclass(frozen=True)
class UserScope:
    """当前用户在按人归属查询中的可见范围（每请求实时判定，不缓存）。

    普通用户和降级场景下 users 只含本人；管理员含本组织全部在用成员。
    """

    current_user_id: str
    is_admin: bool
    users: tuple[OrganizationUser, ...]

    @property
    def user_ids(self) -> list[str]:
        return [user.user_id for user in self.users]

    def nick_name_of(self, user_id: str) -> str | None:
        return next((u.nick_name for u in self.users if u.user_id == user_id), None)

    def visible_ids(self, requested: Iterable[str] | None) -> list[str]:
        """按请求的发起人筛选收敛可见范围。

        普通用户忽略筛选，永远只有本人；管理员未传筛选时是全部可见成员，
        传了则与可见成员求交（越权 id 直接丢弃，交集为空即查不到任何记录）。
        """
        if not self.is_admin:
            return [self.current_user_id]
        selected = list(dict.fromkeys(requested or []))
        if not selected:
            return self.user_ids
        visible = set(self.user_ids)
        return [user_id for user_id in selected if user_id in visible]

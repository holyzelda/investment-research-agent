"""可见范围解析：管理员判定、在用成员过滤与上游异常降级。

管理员只按当前用户自己那条记录的 roleKey 判定；任何解析不出当前用户的情况一律
降级为"只看自己"，绝不因上游异常放大可见范围，也绝不让用户看不到自己的台账。
"""
from __future__ import annotations

import httpx
import pytest

from app.core.config.settings import UserCenterConfig
from app.modules.platform_access.application.user_scope_service import UserScopeService
from app.modules.platform_access.domain.models import CurrentUser
from app.modules.platform_access.infrastructure.user_center_client import UserCenterClient

USER = CurrentUser(user_id="119", username="bjjzA")

ADMIN_RECORD = {
    "userId": 119, "nickName": "北京金租管理员", "status": "0",
    "roles": [{"roleId": 120, "roleName": "北京金租管理员", "roleKey": "bjjzadmin"}],
}
MEMBER_RECORD = {"userId": 120, "nickName": "北京金租普通账号", "status": "0", "roles": []}
DISABLED_RECORD = {"userId": 124, "nickName": "已停用员工", "status": "1", "roles": []}


def _client(handler) -> UserCenterClient:
    return UserCenterClient(
        UserCenterConfig(base_url="http://user-center.test"),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


def _responder(payload, status_code=200):
    def handler(request: httpx.Request) -> httpx.Response:
        handler.request = request
        return httpx.Response(status_code, json=payload)

    return handler


async def test_admin_scope_only_includes_active_organization_members():
    handler = _responder({
        "code": 200, "msg": "操作成功",
        "data": [ADMIN_RECORD, MEMBER_RECORD, DISABLED_RECORD],
    })

    scope = await UserScopeService(_client(handler)).resolve(USER)

    assert scope.is_admin is True
    assert scope.user_ids == ["119", "120"]
    assert scope.nick_name_of("120") == "北京金租普通账号"
    assert handler.request.url.params["userId"] == "119"


async def test_empty_roles_is_an_ordinary_user_limited_to_self():
    handler = _responder({"code": 200, "data": [{**MEMBER_RECORD, "userId": 119}]})

    scope = await UserScopeService(_client(handler)).resolve(USER)

    assert scope.is_admin is False
    assert scope.user_ids == ["119"]


async def test_role_key_matches_admin_case_insensitively():
    handler = _responder({"code": 200, "data": [
        {**ADMIN_RECORD, "roles": [{"roleKey": "BJJZAdmin"}]}, MEMBER_RECORD,
    ]})

    scope = await UserScopeService(_client(handler)).resolve(USER)

    assert scope.is_admin is True


async def test_role_name_alone_does_not_grant_admin():
    handler = _responder({"code": 200, "data": [
        {**ADMIN_RECORD, "roles": [{"roleName": "北京金租管理员", "roleKey": "bjjzuser"}]},
        MEMBER_RECORD,
    ]})

    scope = await UserScopeService(_client(handler)).resolve(USER)

    assert scope.is_admin is False
    assert scope.user_ids == ["119"]


@pytest.mark.parametrize("payload, status_code", [
    ({"code": 500, "msg": "服务异常", "data": None}, 200),
    ({"code": 200, "data": {"userId": 119}}, 200),
    ({"code": 200, "data": [MEMBER_RECORD]}, 200),  # 返回里没有当前用户
    ({"code": 200, "data": [ADMIN_RECORD]}, 502),
])
async def test_upstream_anomalies_degrade_to_self_only(payload, status_code):
    handler = _responder(payload, status_code)

    scope = await UserScopeService(_client(handler)).resolve(USER)

    assert scope.is_admin is False
    assert scope.user_ids == ["119"]
    assert scope.nick_name_of("119") == "bjjzA"


async def test_connection_failure_degrades_to_self_only():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    scope = await UserScopeService(_client(handler)).resolve(USER)

    assert scope.is_admin is False
    assert scope.user_ids == ["119"]
    assert scope.nick_name_of("119") == "bjjzA"


async def test_unconfigured_base_url_skips_the_call_entirely():
    scope = await UserScopeService(
        UserCenterClient(UserCenterConfig(base_url=""))
    ).resolve(USER)

    assert scope.is_admin is False
    assert scope.user_ids == ["119"]


async def test_admin_marked_disabled_upstream_falls_back_to_self_only():
    handler = _responder({"code": 200, "data": [
        {**ADMIN_RECORD, "status": "1"}, MEMBER_RECORD,
    ]})

    scope = await UserScopeService(_client(handler)).resolve(USER)

    assert scope.is_admin is False
    assert scope.user_ids == ["119"]

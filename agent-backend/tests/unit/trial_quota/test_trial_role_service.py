"""试用账号角色解析：通过 organization/users 的 roleKey 判定。"""
from __future__ import annotations

import httpx
import pytest

from app.core.config.settings import UserCenterConfig
from app.core.constants import HttpStatus
from app.modules.platform_access.infrastructure.user_center_client import UserCenterClient
from app.modules.trial_quota.application.trial_role_service import (
    TrialRoleService,
    TrialRoleUnavailable,
)

USER_ID = "119"


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


def _record(user_id=USER_ID, roles=None):
    return {"userId": user_id, "nickName": "试用用户", "status": "0", "roles": roles or []}


async def _is_trial(handler, user_id=USER_ID) -> bool:
    return await TrialRoleService(_client(handler)).is_trial(user_id)


async def test_role_key_string_suffix_matches_case_insensitively():
    handler = _responder({"code": 200, "msg": "操作成功", "data": [
        _record(roles=[{"roleId": 1, "roleName": "甘肃试用", "roleKey": "gansuFreeTrial"}]),
    ]})

    assert await _is_trial(handler) is True


async def test_role_key_object_value_suffix_matches():
    handler = _responder({"code": 200, "data": [
        _record(roles=[{"roleKey": {"value": "ningxiafreetrial"}}]),
    ]})

    assert await _is_trial(handler) is True


async def test_role_value_fallback_when_role_key_missing():
    handler = _responder({"code": 200, "data": [
        _record(roles=[{"value": "beijingFreeTrial"}]),
    ]})

    assert await _is_trial(handler) is True


async def test_suffix_is_required_not_substring():
    handler = _responder({"code": 200, "data": [
        _record(roles=[{"roleKey": "bjjzfreetrialadmin"}]),
    ]})

    assert await _is_trial(handler) is False


async def test_plain_admin_role_is_not_trial():
    handler = _responder({"code": 200, "data": [
        _record(roles=[{"roleKey": "bjjzadmin"}]),
    ]})

    assert await _is_trial(handler) is False


async def test_empty_roles_is_not_trial():
    handler = _responder({"code": 200, "data": [_record(roles=[])]})

    assert await _is_trial(handler) is False


async def test_only_current_users_roles_are_considered():
    handler = _responder({"code": 200, "data": [
        {"userId": "other", "roles": [{"roleKey": "otherfreetrial"}]},
        _record(roles=[{"roleKey": "ordinary"}]),
    ]})

    assert await _is_trial(handler) is False


async def test_non_list_roles_raise_503():
    """角色列表结构异常属于上游不可信，按 503 处理而不是判定普通账号。"""
    handler = _responder({"code": 200, "data": [_record(roles="freetrial")]})

    with pytest.raises(TrialRoleUnavailable):
        await _is_trial(handler)


@pytest.mark.parametrize("roles", [
    [{"roleKey": ""}],
    [{"roleKey": None}],
    [{"roleKey": True}],
    [{"value": ""}],
])
async def test_malformed_role_entries_are_never_trial(roles):
    handler = _responder({"code": 200, "data": [_record(roles=roles)]})

    assert await _is_trial(handler) is False


async def test_missing_current_user_raises_503():
    handler = _responder({"code": 200, "data": [
        {"userId": "other", "roles": [{"roleKey": "otherfreetrial"}]},
    ]})

    with pytest.raises(TrialRoleUnavailable) as excinfo:
        await _is_trial(handler)
    assert excinfo.value.code == HttpStatus.SERVICE_UNAVAILABLE


@pytest.mark.parametrize("payload,status_code", [
    ({"code": 500, "msg": "服务异常", "data": None}, 200),
    ({"code": 200, "data": {"userId": USER_ID}}, 200),
    ({"code": 200, "data": None}, 200),
    ({"code": 200, "data": []}, 200),
    ({"code": 401, "msg": "未认证", "data": None}, 401),
])
async def test_upstream_anomalies_raise_503(payload, status_code):
    handler = _responder(payload, status_code)

    with pytest.raises(TrialRoleUnavailable):
        await _is_trial(handler)


async def test_connection_failure_raises_503():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(TrialRoleUnavailable):
        await _is_trial(handler)


async def test_unconfigured_base_url_raises_503():
    service = TrialRoleService(UserCenterClient(UserCenterConfig(base_url="")))

    with pytest.raises(TrialRoleUnavailable):
        await service.is_trial(USER_ID)

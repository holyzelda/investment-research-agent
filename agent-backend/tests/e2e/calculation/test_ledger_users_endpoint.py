"""e2e：台账发起人选项接口的响应壳与管理员/普通用户形态。

可见范围由 get_user_scope 实时解析，测试用依赖覆盖替换掉真实的用户管理中心调用。
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.platform_access.domain.models import OrganizationUser, UserScope
from app.modules.platform_access.interface.deps import get_user_scope

HEADERS = {"userId": "119", "username": "bjjzA"}


def _override(scope: UserScope):
    app.dependency_overrides[get_user_scope] = lambda: scope


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.pop(get_user_scope, None)


async def _get_users():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get("/ir/calc/ledger/users", headers=HEADERS)


@pytest.mark.asyncio
async def test_admin_gets_organization_options_in_the_shared_response_shell():
    _override(UserScope(
        current_user_id="119", is_admin=True,
        users=(
            OrganizationUser(user_id="119", nick_name="北京金租管理员"),
            OrganizationUser(user_id="120", nick_name="北京金租普通账号"),
        ),
    ))

    resp = await _get_users()

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["data"] == {
        "isAdmin": True,
        "users": [
            {"userId": "119", "nickName": "北京金租管理员"},
            {"userId": "120", "nickName": "北京金租普通账号"},
        ],
    }


@pytest.mark.asyncio
async def test_ordinary_user_only_sees_self():
    _override(UserScope(
        current_user_id="120", is_admin=False,
        users=(OrganizationUser(user_id="120", nick_name="北京金租普通账号"),),
    ))

    resp = await _get_users()

    assert resp.json()["data"] == {
        "isAdmin": False,
        "users": [{"userId": "120", "nickName": "北京金租普通账号"}],
    }


@pytest.mark.asyncio
async def test_requires_platform_identity():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/ir/calc/ledger/users")

    assert resp.status_code == 401

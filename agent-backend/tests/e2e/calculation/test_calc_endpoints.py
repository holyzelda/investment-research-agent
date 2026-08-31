"""e2e（Batch 2）：参数字典与试组装端点。"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.calculation.infrastructure.henan_spot_import import CITY_TO_REGION


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"userId": "calculation-pytest", "username": "__pytest__"},
    ) as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_param_dict_endpoint(client):
    resp = await client.get("/ir/calc/param-dict")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["total"] == 68


@pytest.mark.asyncio
async def test_param_dict_display_only(client):
    resp = await client.get("/ir/calc/param-dict", params={"display_only": True})
    body = resp.json()
    # F=1 展示项应少于全量
    assert body["data"]["total"] == 59


@pytest.mark.asyncio
async def test_param_dict_with_province_returns_switches(client):
    """Batch5：?province= 附带该省表2市场开关，供收益类统一显隐（现货同样受开关约束）。"""
    resp = await client.get("/ir/calc/param-dict", params={"province": "甘肃"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["switches"]["switch_spot"] == 1
    assert data["switches"]["switch_mid_long"] == 0
    assert data["switches"]["switch_lease"] == 0


@pytest.mark.asyncio
async def test_param_dict_without_province_has_no_switches(client):
    resp = await client.get("/ir/calc/param-dict")
    assert "switches" not in resp.json()["data"]


def _city_spec(body: dict) -> dict:
    return next(p for p in body["data"]["parameters"] if p["id"] == "city")


@pytest.mark.asyncio
@pytest.mark.parametrize("province", ["河南", "河南省", " 河南 "])
async def test_param_dict_henan_city_is_selectable(client, province):
    """河南按地级市定位项目，字典须给出可下拉可搜索的城市候选。"""
    resp = await client.get("/ir/calc/param-dict", params={"province": province})
    assert resp.status_code == 200
    spec = _city_spec(resp.json())
    assert spec["control"] == "select"
    assert {o["value"] for o in spec["options"]} == set(CITY_TO_REGION)
    assert all(o["label"] == o["value"] for o in spec["options"])


@pytest.mark.asyncio
@pytest.mark.parametrize("params", [{"province": "甘肃"}, {}])
async def test_param_dict_city_options_only_for_henan(client, params):
    resp = await client.get("/ir/calc/param-dict", params=params)
    spec = _city_spec(resp.json())
    assert spec["control"] != "select"
    assert not spec.get("options")



@pytest.mark.asyncio
async def test_assemble_preview_gansu(client):
    resp = await client.post("/ir/calc/assemble-preview", json={
        "province": "甘肃", "capacity_mwh": 800, "power_mw": 200,
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["apiInput"]["province"] == "甘肃"
    assert data["switches"]["switch_spot"] == 1
    assert data["switches"]["switch_mid_long"] == 0
    # 中长期开关=0，明细不写入
    assert "mid_long_energy_revenue_first_year_tax" not in data["apiInput"]


@pytest.mark.asyncio
async def test_assemble_preview_rejects_non_positive_power(client):
    """Batch5：功率/容量必须为正，否则现货 K 折算会除零；应校验拒绝而非 500。"""
    resp = await client.post("/ir/calc/assemble-preview", json={
        "province": "甘肃", "capacity_mwh": 800, "power_mw": 0,
    })
    assert resp.status_code == 400


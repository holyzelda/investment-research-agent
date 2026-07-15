"""e2e（Batch 2）：参数字典与试组装端点。"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_param_dict_endpoint(client):
    resp = await client.get("/ir/calc/param-dict")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["total"] == 51


@pytest.mark.asyncio
async def test_param_dict_display_only(client):
    resp = await client.get("/ir/calc/param-dict", params={"display_only": True})
    body = resp.json()
    # F=1 展示项应少于全量
    assert body["data"]["total"] == 42


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
async def test_run_returns_three_modules(client):
    resp = await client.post("/ir/calc/run", json={
        "province": "甘肃", "capacity_mwh": 800, "power_mw": 200, "node_name": "兰州东",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["basicInfo"]["province"] == "甘肃"
    assert data["basicInfo"]["nodeName"] == "兰州东"
    assert data["financial"]["projectIrr"] == 8.5
    assert data["advanced"]["donut"]["totalRevenue"] == 8600.0
    assert data["advanced"]["donut"]["interventionRevenue"] == 200.0
    assert len(data["advanced"]["lines"]["mainBusinessCost"]) == 15

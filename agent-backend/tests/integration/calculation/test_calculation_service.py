"""测算服务 · 集成测试（Mock 主链路：组装→飞书Mock→映射结果）。"""
import pytest

from app.modules.calculation.application.factory import build_calculation_service
from app.modules.calculation.domain.models import ProjectBasics
from app.modules.calculation.infrastructure.feishu_sample import SAMPLE_API_OUTPUT


async def _run(province="甘肃", cap=800, pwr=200, node=None):
    svc = build_calculation_service()
    return await svc.run(
        ProjectBasics(province=province, capacity_mwh=cap, power_mw=pwr, node_name=node)
    )


@pytest.mark.asyncio
async def test_run_produces_three_modules():
    r = await _run()
    assert r.basic_info.province == "甘肃"
    assert r.financial.project_irr == SAMPLE_API_OUTPUT["project_irr"]
    assert r.financial.capital_irr == SAMPLE_API_OUTPUT["capital_irr"]
    assert r.financial.average_revenue == SAMPLE_API_OUTPUT["average_revenue"]
    assert r.advanced.donut.total_revenue == SAMPLE_API_OUTPUT["first_year_total_revenue"]
    assert r.advanced.debt_service_coverage.cashflow_ratio == SAMPLE_API_OUTPUT[
        "cashflow_debt_service_coverage_ratio"
    ]


@pytest.mark.asyncio
async def test_feishu_gateway_received_assembled_input():
    """验证 assemble 的入参确实被写入飞书网关（写读闭环）。"""
    svc = build_calculation_service()
    await svc.run(ProjectBasics(province="甘肃", capacity_mwh=800, power_mw=200))
    payload = svc._feishu.last_payload()
    assert payload is not None
    assert payload["province"] == "甘肃"
    assert payload["switch_spot"] == 1
    assert "project_irr" not in payload


@pytest.mark.asyncio
async def test_node_flows_through():
    r = await _run(node="兰州东")
    assert r.basic_info.node_name == "兰州东"


@pytest.mark.asyncio
async def test_unknown_province_warns_but_still_runs():
    r = await _run(province="火星省")
    assert any("火星省" in w for w in r.warnings)
    assert r.financial.project_irr is not None

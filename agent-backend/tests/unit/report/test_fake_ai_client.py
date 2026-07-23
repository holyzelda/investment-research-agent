"""确定性报告 AI 适配器的公开契约。"""
import pytest

from app.modules.report.infrastructure.fake_ai_client import FakeReportAiClient


RULE = {"key": "sensitivity", "title": "压力情景偿债覆盖倍数分析"}
CONTEXT = {"project": {"province": "甘肃"}}


@pytest.mark.asyncio
async def test_returns_deterministic_text_from_frozen_context():
    client = FakeReportAiClient()

    text = await client.generate_section(RULE, CONTEXT)

    assert text == "甘肃压力情景偿债覆盖倍数分析已基于本次冻结测算数据生成。"
    assert client.calls["sensitivity"] == 1


@pytest.mark.asyncio
async def test_fails_the_configured_number_of_attempts_then_succeeds():
    client = FakeReportAiClient(failures={"sensitivity": 2})

    with pytest.raises(RuntimeError, match="模拟 sensitivity 生成失败"):
        await client.generate_section(RULE, CONTEXT)
    with pytest.raises(RuntimeError, match="模拟 sensitivity 生成失败"):
        await client.generate_section(RULE, CONTEXT)

    text = await client.generate_section(RULE, CONTEXT)

    assert text.startswith("甘肃")
    assert client.calls["sensitivity"] == 3

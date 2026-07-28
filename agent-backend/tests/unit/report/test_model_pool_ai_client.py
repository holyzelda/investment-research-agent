import asyncio

import pytest

from app.core.config.settings import MiddlePlatformConfig
from app.modules.middle_platform.application.token_cache import MiddlePlatformTokenCache
from app.modules.middle_platform.infrastructure.http_client import PlatformAccessToken
from app.modules.report.infrastructure.model_pool_ai_client import ModelPoolReportAiClient


RULE = {
    "key": "debt_service_coverage",
    "title": "偿债能力",
    "prompt": "仅根据冻结资料生成正文。",
    "maxWords": 200,
    "forbiddenMetrics": [],
}


class BlockingMiddlePlatformClient:
    def __init__(self):
        self.issue_calls = 0
        self.model_calls = 0
        self.issue_started = asyncio.Event()
        self.release_issue = asyncio.Event()
        self.fail_issue = False

    async def issue_token(self, *, user_id, user_name):
        self.issue_calls += 1
        self.issue_started.set()
        await self.release_issue.wait()
        if self.fail_issue:
            raise RuntimeError("鉴权不可用")
        return PlatformAccessToken(value="shared-token", expires_in=3600)

    async def chat_report_model(self, *, access_token, payload):
        self.model_calls += 1
        assert access_token == "shared-token"
        return "冻结正文"


async def _five_calls(client):
    return await asyncio.gather(*[
        client.generate_section(RULE, {"index": index}, user_id="u1", username="用户")
        for index in range(5)
    ])


async def _five_failed_calls(client):
    return await asyncio.gather(*[
        client.generate_section(RULE, {}, user_id="u1", username="用户")
        for _ in range(5)
    ], return_exceptions=True)


@pytest.mark.asyncio
async def test_concurrent_sections_issue_one_token_and_call_model_five_times():
    http_client = BlockingMiddlePlatformClient()
    client = ModelPoolReportAiClient(
        MiddlePlatformConfig(),
        client=http_client,
        token_cache=MiddlePlatformTokenCache(),
    )

    pending = asyncio.create_task(_five_calls(client))
    await asyncio.wait_for(http_client.issue_started.wait(), timeout=1)
    await asyncio.sleep(0)
    assert http_client.issue_calls == 1
    http_client.release_issue.set()

    assert await pending == ["冻结正文"] * 5
    assert http_client.issue_calls == 1
    assert http_client.model_calls == 5


@pytest.mark.asyncio
async def test_cached_token_skips_token_issue():
    cache = MiddlePlatformTokenCache()
    cache.put(("ir_agent", "u1"), "shared-token", 3600)
    http_client = BlockingMiddlePlatformClient()
    client = ModelPoolReportAiClient(
        MiddlePlatformConfig(), client=http_client, token_cache=cache
    )

    assert await _five_calls(client) == ["冻结正文"] * 5
    assert http_client.issue_calls == 0
    assert http_client.model_calls == 5


@pytest.mark.asyncio
async def test_concurrent_sections_share_token_issue_failure_once():
    http_client = BlockingMiddlePlatformClient()
    http_client.fail_issue = True
    client = ModelPoolReportAiClient(
        MiddlePlatformConfig(),
        client=http_client,
        token_cache=MiddlePlatformTokenCache(),
    )

    pending = asyncio.create_task(_five_failed_calls(client))
    await asyncio.wait_for(http_client.issue_started.wait(), timeout=1)
    await asyncio.sleep(0)
    assert http_client.issue_calls == 1
    http_client.release_issue.set()

    results = await pending
    assert http_client.issue_calls == 1
    assert http_client.model_calls == 0
    assert all(isinstance(result, RuntimeError) for result in results)

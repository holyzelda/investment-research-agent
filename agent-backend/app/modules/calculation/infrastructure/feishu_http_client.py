"""calculation 基础设施 · 飞书电子表格网关（真实实现，方案A）。

实现同一 `FeishuGateway` 端口，对接飞书开放平台（自建应用）：
- 鉴权：tenant_access_token（缓存 + 失效自动刷新）。
- 复制：Drive v1 files/{token}/copy 从模板复制新副本到目标文件夹（异步接口，返回体即给新 token）。
- 寻址：Sheets v3 spreadsheets/{token}/sheets/query 拿 sheet_id（v2 metainfo 已不推荐）。
- 写入：Sheets v2 values_batch_update，按参数字典的 `api_cell` 定位 API_INPUT / API_META 单元格。
- 读取：Sheets v2 values_batch_get，读 API_META（status/request_id）与 API_OUTPUT（各 output 参数）。
- 错误：飞书 body `code!=0` 与 HTTP 状态映射到 domain 的 Retryable/NonRetryableCalcError；
  token 失效自动刷新一次；原始 httpx 网络异常上抛，由 retry_policy.classify_error 归类。

副本单元格地址源自 `param_dict.json` 的 `api_cell`（业务冻结中，挂账 #5/#7）；
凭据/模板/文件夹/API_META 单元格来自 FeishuConfig（Nacos/env，挂账 #2）。
enabled=false 时系统用 MockFeishuGateway（默认），本类不参与。
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Optional

import httpx

from app.core.config.settings import FeishuConfig
from app.modules.calculation.domain.execution import (
    NonRetryableCalcError,
    RetryableCalcError,
)
from app.modules.calculation.domain.param_dictionary import ParamDictionary
from app.modules.calculation.domain.ports import FeishuGateway

# 飞书业务错误码分类（PoC 联调后按真实返回校准）
_TOKEN_CODES = {99991661, 99991663, 99991664, 99991668}   # token 失效/过期 → 刷新重试
_RATE_LIMIT_CODES = {99991400}                             # 频控 → 可重试
_RETRYABLE_CODES = {1061045}                               # drive copy 内部可重试错误
_PROCESSING_CODES = {601124041}                            # 副本 ContentMeta 处理中（copy 异步）→ 退避重试
_PERMISSION_CODES = {1310213, 1310214, 1310217}           # 无权限/表格不存在 → 不可重试


class _TokenExpired(Exception):
    """内部信号：token 失效，触发一次刷新重试。"""


# 读值渲染方式：必须计算公式后返回值，否则默认返回公式文本本身（如 status/output 桥接公式）。
# UnformattedValue = 计算但不格式化：数值回数值、字符串回字符串，最利于下游解析。
_VALUE_RENDER = "UnformattedValue"


class _ContentProcessing(Exception):
    """内部信号：副本内容仍在处理中（copy 异步），触发退避后重试同一请求。"""


def _first_cell(values) -> Optional[object]:
    """取 values_batch_get 单元格区的首格值（values 为二维数组）。"""
    if values and values[0]:
        return values[0][0]
    return None


class HttpFeishuGateway(FeishuGateway):
    def __init__(
        self,
        config: FeishuConfig,
        param_dict: ParamDictionary,
        client: Optional[httpx.AsyncClient] = None,
        processing_retries: int = 5,
        processing_backoff: float = 2.0,
    ):
        self._cfg = config
        self._dict = param_dict
        self._client = client or httpx.AsyncClient(base_url=config.base_url, timeout=30.0)
        self._token: Optional[str] = None
        self._token_exp: float = 0.0
        self._sheet_ids: dict[str, dict[str, str]] = {}   # doc_token -> {sheet 标题: sheetId}
        # copy 异步：副本 ContentMeta 处理中（601124041）时退避重试的次数与间隔
        self._processing_retries = processing_retries
        self._processing_backoff = processing_backoff

    # ---- 鉴权 ----
    async def _tenant_token(self) -> str:
        now = asyncio.get_event_loop().time()
        if self._token and now < self._token_exp:
            return self._token
        r = await self._client.post(
            "/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self._cfg.app_id, "app_secret": self._cfg.app_secret},
        )
        body = self._check(r)
        self._token = body["tenant_access_token"]
        # 提前 60s 视为过期，避免临界失败
        self._token_exp = now + max(0, int(body.get("expire", 7200)) - 60)
        return self._token

    async def _authed(self, method: str, url: str, **kw) -> dict:
        """带鉴权请求。副本刚复制时 ContentMeta 仍在处理(601124041) → 退避重试同一请求；
        退避耗尽仍在处理则抛 Retryable，交外层重试策略（正式 /tasks 流程）继续兜。"""
        for attempt in range(self._processing_retries + 1):
            try:
                return await self._authed_once(method, url, **kw)
            except _ContentProcessing:
                if attempt >= self._processing_retries:
                    raise RetryableCalcError(
                        "飞书副本内容仍在处理(ContentMeta is processing)，稍后重试",
                        code="feishu_601124041")
                await asyncio.sleep(self._processing_backoff)

    async def _authed_once(self, method: str, url: str, **kw) -> dict:
        """带 Bearer 的单次请求；token 失效自动刷新一次后重试。"""
        token = await self._tenant_token()
        headers = {**kw.pop("headers", {}), "Authorization": f"Bearer {token}"}
        try:
            return self._check(await self._client.request(method, url, headers=headers, **kw))
        except _TokenExpired:
            self._token = None
            headers["Authorization"] = f"Bearer {await self._tenant_token()}"
            try:
                return self._check(await self._client.request(method, url, headers=headers, **kw))
            except _TokenExpired:
                raise NonRetryableCalcError(
                    "飞书 token 刷新后仍失效，请检查应用凭据", code="feishu_token_invalid"
                )

    def _check(self, r: httpx.Response) -> dict:
        """HTTP 状态 + 飞书 body code 映射到错误分类；成功返回 body。"""
        sc = r.status_code
        if sc >= 500:
            raise RetryableCalcError(f"飞书服务端错误 HTTP {sc}", code=f"feishu_http_{sc}")
        if sc == 429:
            raise RetryableCalcError("飞书限流 HTTP 429", code="feishu_rate_limited")
        if sc in (401, 403):
            raise NonRetryableCalcError("飞书鉴权/权限失败", code=f"feishu_http_{sc}")
        if sc == 404:
            raise NonRetryableCalcError("飞书资源/模板不存在", code="feishu_not_found")
        body = r.json()
        code = body.get("code", 0)
        if code == 0:
            return body
        if code in _TOKEN_CODES:
            raise _TokenExpired()
        if code in _PROCESSING_CODES:
            raise _ContentProcessing()
        if code in _RATE_LIMIT_CODES or code in _RETRYABLE_CODES:
            raise RetryableCalcError(f"飞书可重试错误 {code}：{body.get('msg')}", code=f"feishu_{code}")
        if code in _PERMISSION_CODES:
            raise NonRetryableCalcError(f"飞书无权限：{body.get('msg')}", code=f"feishu_{code}")
        # 未知飞书错误：不盲目重试
        raise NonRetryableCalcError(f"飞书错误 {code}：{body.get('msg')}", code=f"feishu_{code}")

    # ---- 单元格寻址（值读写走 Sheets v2，按 <sheetId>!cell 寻址）----
    def _ss(self, doc_token: str) -> str:
        return f"/open-apis/sheets/v2/spreadsheets/{doc_token}"

    async def _sheet_id(self, doc_token: str, title: str) -> str:
        """标题→sheet_id。用 v3『获取工作表』sheets/query（v2 metainfo 已不推荐）。

        副本从同一模板复制、sheet_id 稳定，故按 doc_token 缓存一次即可。
        注意：v3 返回字段是下划线 sheet_id（非 v2 的 camelCase sheetId）。
        """
        ids = self._sheet_ids.get(doc_token)
        if ids is None:
            body = await self._authed(
                "GET", f"/open-apis/sheets/v3/spreadsheets/{doc_token}/sheets/query")
            ids = {s["title"]: s["sheet_id"] for s in body["data"]["sheets"]}
            self._sheet_ids[doc_token] = ids
        return ids[title]

    async def _range(self, doc_token: str, api_cell: str) -> str:
        """'API_INPUT!B2' -> '<sheetId>!B2:B2'。

        飞书 range 需 <起>:<止> 形式，单格也要写成 B2:B2（裸 B2 会被 values_batch_update 拒绝）；
        已是区间（如 C2:Q2 序列）则原样。
        """
        title, cell = api_cell.split("!", 1)
        if ":" not in cell:
            cell = f"{cell}:{cell}"
        return f"{await self._sheet_id(doc_token, title)}!{cell}"

    # ---- FeishuGateway 端口实现 ----
    async def copy_template(self, template_token: str, name: Optional[str] = None) -> str:
        name = name or f"{self._cfg.copy_name_prefix}-{uuid.uuid4().hex[:8]}"
        body = await self._authed(
            "POST", f"/open-apis/drive/v1/files/{template_token}/copy",
            json={"name": name, "type": "sheet", "folder_token": self._cfg.target_folder_token},
        )
        return body["data"]["file"]["token"]

    async def write_input(self, doc_token: str, payload: dict) -> None:
        value_ranges = []
        for pid, val in payload.items():
            if pid == "operation_years":
                continue
            spec = self._dict.get(pid)
            if spec is None or not spec.api_cell:
                continue  # 非接口区参数（如仅展示）不写飞书
            value_ranges.append({"range": await self._range(doc_token, spec.api_cell), "values": [[val]]})
        if value_ranges:
            await self._authed(
                "POST", f"{self._ss(doc_token)}/values_batch_update",
                json={"valueRanges": value_ranges},
            )

    async def write_meta(self, doc_token: str, meta: dict) -> None:
        cells = {
            self._cfg.meta_request_id_cell: meta.get("request_id"),
            self._cfg.meta_param_hash_cell: meta.get("param_hash"),
        }
        value_ranges = [
            {"range": await self._range(doc_token, cell), "values": [[val]]}
            for cell, val in cells.items() if cell
        ]
        if value_ranges:
            await self._authed(
                "POST", f"{self._ss(doc_token)}/values_batch_update",
                json={"valueRanges": value_ranges},
            )

    async def read_meta(self, doc_token: str) -> dict:
        ranges = [
            await self._range(doc_token, self._cfg.meta_status_cell),
            await self._range(doc_token, self._cfg.meta_request_id_cell),
        ]
        body = await self._authed(
            "GET", f"{self._ss(doc_token)}/values_batch_get",
            params={"ranges": ",".join(ranges), "valueRenderOption": _VALUE_RENDER})
        vals = [_first_cell(vr.get("values")) for vr in body["data"]["valueRanges"]]
        raw_status, request_id = (vals + [None, None])[:2]
        # 归一化：与业务约定的"算完"取值一致才置 done，否则原样（引擎据 status==done 决定是否读 output）
        status = "done" if str(raw_status).strip() == self._cfg.meta_done_value else raw_status
        return {"status": status, "request_id": request_id}

    async def read_output(self, doc_token: str) -> dict:
        specs = [s for s in self._dict.outputs() if s.api_cell]
        if not specs:
            return {}
        ranges = [await self._range(doc_token, s.api_cell) for s in specs]
        body = await self._authed(
            "GET", f"{self._ss(doc_token)}/values_batch_get",
            params={"ranges": ",".join(ranges), "valueRenderOption": _VALUE_RENDER})
        vrs = body["data"]["valueRanges"]
        result: dict = {}
        for spec, vr in zip(specs, vrs):
            values = vr.get("values") or []
            _, cell = spec.api_cell.split("!", 1)
            if ":" in cell:   # 区间（如 15 年序列）→ 展平为列表
                result[spec.id] = [v for row in values for v in row]
            else:
                result[spec.id] = _first_cell(values)
        return result

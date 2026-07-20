"""飞书接口区最小连通性 PoC —— 手动执行（不属于 pytest）。

用途：凭据/接口区就位后，验证"复制→写入→等算→读取"整条真实链路是否打通，
并逐步打印每一步返回，方便定位是哪一步（权限/单元格/公式/回写）没就绪。

前置（见与本文件同批交付的说明 / PRD 挂账 #2/#5/#7）：
  - 飞书自建应用已建、已加为「模板表格」和「目标文件夹」协作者；
  - 底稿已新建 API_INPUT / API_OUTPUT / API_META 三张接口 sheet，单元格对齐 param_dict.json 的 api_cell；
  - 桥接公式已把接口区↔模型连上，且 API_META 会回写 request_id 并在算完时把 status 置为 meta_done_value。

用法（在 agent-backend 目录下）：
  1) 配 configs/application.yml 的 feishu 段（enabled: true 等），或用环境变量 IR_FEISHU_*；
     凭据建议用环境变量 / Nacos，勿写进文件。
  2) 运行：  .venv\\Scripts\\python.exe tools\\feishu_poc.py
  结果同时打印到终端并写入 tools/_feishu_poc_out.txt。
"""
import asyncio
import json
import os
import sys
import uuid

# 让 `import app.*` 可用（repo 根 = 本文件上级目录 agent-backend）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config.settings import get_settings
from app.modules.calculation.application.factory import build_param_assembler
from app.modules.calculation.application.task_service import _param_hash, build_copy_name
from app.modules.calculation.domain.models import ProjectBasics
from app.modules.calculation.infrastructure.feishu_http_client import HttpFeishuGateway
from app.modules.calculation.infrastructure.param_dict_repo import JsonParamDictRepository

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_feishu_poc_out.txt")
_lines: list[str] = []


def log(msg: str) -> None:
    print(msg)
    _lines.append(str(msg))


def _flush() -> None:
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(_lines) + "\n")


async def main() -> None:
    s = get_settings()
    fc = s.feishu

    # 基础凭据（拿 token 的前提）
    if not (fc.enabled and fc.app_id and fc.app_secret):
        log("❌ 基础配置未就位：需 feishu.enabled=true 且 app_id/app_secret 已填。")
        log(f"   enabled={fc.enabled}  app_id={'set' if fc.app_id else 'MISSING'}  "
            f"app_secret={'set' if fc.app_secret else 'MISSING'}")
        _flush()
        return

    # ⓪ 表2《各省收益结构》真读（只需 revenue_structure_token；可先于底稿单独验证）
    if fc.revenue_structure_token:
        try:
            from app.modules.calculation.infrastructure.revenue_structure_reader import (
                FeishuRevenueStructureReader,
            )
            reader = FeishuRevenueStructureReader(config=fc)
            for prov in ("蒙东", "宁夏", "蒙西"):
                p = reader.get_profile(prov)
                if p is None:
                    log(f"⓪ 表2 {prov}: 不在表2")
                else:
                    log(f"⓪ 表2 {prov}: 现货={p.spot} 容量={p.capacity} 补贴={p.subsidy}"
                        f"调频={p.frequency}  调频两挡={p.frequency_tier.t2}/{p.frequency_tier.t4}"
                        f"中长期={p.mid_long} 中长期两档={p.mid_long_tier.t2}/{p.mid_long_tier.t4} "
                        f"干预补偿={p.intervention} 干预补偿两档={p.intervention_tier.t2}/{p.intervention_tier.t4} "
                        f"租赁单价={p.lease_unit_price} 收/返过网费={p.collect_grid_fee}/{p.return_grid_fee}")
            log(f"⓪ 表2 读取 OK → 已缓存省份数={len(reader._table())}")
        except Exception as e:  # noqa: BLE001
            log(f"⓪ 表2 读取失败：{type(e).__name__}: {e}  （查 revenue_structure_token / sheet名 / 权限）")
    else:
        log("⓪ 表2 跳过：revenue_structure_token 未填")

    # ①-④ 底稿全链路需要模板与文件夹
    if not (fc.template_token_15_years and fc.target_folder_token):
        log("①-④ 底稿全链路跳过：template_token_15_years / target_folder_token 未填（表2 部分已可单独验证）")
        _flush()
        return

    pd = JsonParamDictRepository().load()
    gw = HttpFeishuGateway(config=fc, param_dict=pd)
    request_id = uuid.uuid4().hex

    # 用真实组装器产出一份 api_input（最贴近生产写入；如首轮想更小可自行替换为最小 payload）
    basics = ProjectBasics(province="宁夏", capacity_mwh=800, power_mw=200, node_name="")
    assembled = build_param_assembler().assemble(basics)
    api_input = assembled.api_input
    param_hash = _param_hash(api_input)
    copy_name = build_copy_name(basics)
    log(f"request_id={request_id}  api_input 参数数={len(api_input)}  副本名={copy_name}  base_url={fc.base_url}")

    try:
        # ① 复制副本
        try:
            doc = await gw.copy_template(fc.template_token_15_years, copy_name)
            log(f"① copy_template OK → doc_token={doc}  name={copy_name}")
        except Exception as e:  # noqa: BLE001
            log(f"① copy_template 失败：{type(e).__name__}: {e}  （查应用是否为模板/文件夹协作者、scope）")
            return

        # ② 写入 API_INPUT + API_META
        try:
            await gw.write_input(doc, api_input)
            await gw.write_meta(doc, {"request_id": request_id, "param_hash": param_hash, "template_version": None})
            log("② write_input + write_meta OK")
        except Exception as e:  # noqa: BLE001
            log(f"② 写入失败：{type(e).__name__}: {e}  （查接口区 sheet/单元格是否与 param_dict.api_cell 一致）")
            return

        # ③ 轮询 API_META 直到 status=done（用 settings.calc 阈值）
        loop = asyncio.get_event_loop()
        start = loop.time()
        meta: dict = {}
        try:
            while True:
                meta = await gw.read_meta(doc)
                log(f"   read_meta → status={meta.get('status')!r}  request_id={meta.get('request_id')!r}")
                if meta.get("status") == "done":
                    break
                if loop.time() - start >= s.calc.poll_timeout_seconds:
                    log(f"③ 等算超时（{s.calc.poll_timeout_seconds}s 内 status 未变 done）  （查回写/公式，挂账 #2）")
                    break
                await asyncio.sleep(s.calc.poll_interval_seconds)
        except Exception as e:  # noqa: BLE001
            log(f"③ read_meta 失败：{type(e).__name__}: {e}")
            return

        if meta.get("request_id") != request_id:
            log(f"⚠ request_id 回写不一致：期望 {request_id}，实得 {meta.get('request_id')!r}（查 API_META 回写公式）")

        # ④ 读取 API_OUTPUT
        try:
            out = await gw.read_output(doc)
            log(f"④ read_output OK → {json.dumps(out, ensure_ascii=False)[:800]}")
        except Exception as e:  # noqa: BLE001
            log(f"④ read_output 失败：{type(e).__name__}: {e}")
            return

        log("✅ PoC 全链路结束")
    finally:
        await gw._client.aclose()
        _flush()


if __name__ == "__main__":
    asyncio.run(main())

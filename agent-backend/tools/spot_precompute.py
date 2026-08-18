"""现货电价多循环 DP 预计算脚本（可直接从 IDE 运行）。

continuous 保留持续数据源的原有回填路径；uploaded 用于主库文件节点，
按每个节点自己的最后完整日确定滚动窗口。
"""
import os
import sys
import time
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.modules.calculation.infrastructure.spot_precompute import (
    run_precompute,
    run_uploaded_node_precompute,
)

# ================= 模式配置区 =================
MODE = "uploaded"  # "uploaded"（文件节点）或 "continuous"（持续数据源）

# 文件节点模式：默认只预览，不写数据库
# dry_run=True 不创建进程池、不写预计算表和站点表。
# FORCE_RECOMPUTE = True
#   含义：
#   - True：窗口内所有完整数据日都重新计算并写入。
#     - 即使 ir_spot_daily_optimal_node 中已经有对应日期，也会覆盖原结果。
#     - 适合首次导入，以及修正或重新上传历史电价后使用。
#   - False：只计算尚未存在预计算结果的日期。
#     - 已有日期会跳过。
#     - 适合只补算缺失数据，计算量较小。
# DRY_RUN = True
#   含义：
#   - True：dry-run 预览模式。
#     - 查询 MySQL 中的上传节点数据。
#     - 输出每个节点的最后完整日、计算窗口、完整数据日数量和预计处理数量。
#     - 不创建进程池。
#     - 不写入 ir_spot_daily_optimal_node。
#     - 不更新 ir_spot_station。
#   - False：正式执行模式。
#     - 执行 DP 计算。
#     - 写入或覆盖 ir_spot_daily_optimal_node。
#     - 更新 ir_spot_station.last_seen。
UPLOADED_PROVINCE = "山西"
UPLOADED_STATIONS = ["*"]
UPLOADED_WORKERS = 10
FORCE_RECOMPUTE = False
DRY_RUN = False

# 持续数据源模式：保留原有人工回填配置
RUN_DATE = date(2026, 7, 30)  # 回填窗口右端（不含）
NODE_STATIONS = ["*"]
NODE_PROVINCE = "蒙西"
WORKERS = 10
CLEANUP_OLD = True
# ==============================================


def _run_uploaded() -> None:
    stats = run_uploaded_node_precompute(
        province=UPLOADED_PROVINCE,
        stations=UPLOADED_STATIONS,
        workers=UPLOADED_WORKERS,
        force=FORCE_RECOMPUTE,
        dry_run=DRY_RUN,
    )
    for station in stats["stations"]:
        if station["status"] == "no_complete_day":
            print(f"{station['station_name']}: 无完整 96 点数据日，跳过", flush=True)
            continue
        action = "预计写入" if DRY_RUN else "实际写入"
        print(
            f"{station['station_name']}: last={station['last_valid_date']} "
            f"window=[{station['start']},{station['end_exclusive']}) "
            f"完整日={station['complete_days']} 已有={station['existing_days']} "
            f"{action}={station['to_write']} status={station['status']}",
            flush=True,
        )
    action = "预计写入" if DRY_RUN else "实际写入"
    day_count = (
        sum(station.get("to_write", 0) for station in stats["stations"])
        if DRY_RUN
        else stats["node_days_written"]
    )
    print(
        f"文件节点完成：省份={stats['province']} 节点={stats['station_count']} "
        f"{action}={day_count} 天",
        flush=True,
    )


def _run_continuous() -> None:
    stats = run_precompute(
        run_date=RUN_DATE,
        node_stations=NODE_STATIONS,
        node_province=NODE_PROVINCE,
        workers=WORKERS,
        cleanup_old=CLEANUP_OLD,
    )
    print(
        f"持续数据源完成：省级新写 {stats['province_days_written']} 天，"
        f"节点新写 {stats['node_days_written']} 天",
        flush=True,
    )


def main() -> None:
    started = time.perf_counter()
    if MODE == "uploaded":
        _run_uploaded()
    elif MODE == "continuous":
        _run_continuous()
    else:
        raise ValueError(f"不支持的 MODE: {MODE!r}")
    print(f"总耗时 {time.perf_counter() - started:.1f}s", flush=True)


if __name__ == "__main__":
    main()

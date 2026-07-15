"""现货电价·多循环 DP 预计算 · 回填/日更脚本（手动执行，非 pytest）。

核心逻辑由 app.modules.calculation.infrastructure.spot_precompute.run_precompute 提供；
本脚本仅保留顶部配置区，方便人工全量回填或补算。
"""
import os
import sys
import time
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.modules.calculation.infrastructure.spot_precompute import run_precompute

# ================= 参数配置区 =================
RUN_DATE = date(2026, 7, 14)       # 回填窗口右端(不含)；滚动一年 = [RUN_DATE-1年, RUN_DATE)
NODE_STATIONS = ["祥泰站"]               # ["*"]=全部节点站点；[]=不回填节点
NODE_PROVINCE = "蒙西"                 # 节点归属省份（现统一蒙西）
WORKERS = 10                         # 进程池并发（本机 12 核时留 2 核）
CLEANUP_OLD = True                   # 删除滚动窗口外旧数据
# ==============================================


def main() -> None:
    started = time.perf_counter()
    stats = run_precompute(
        run_date=RUN_DATE,
        node_stations=NODE_STATIONS,
        node_province=NODE_PROVINCE,
        workers=WORKERS,
        cleanup_old=CLEANUP_OLD,
    )
    print(
        f"完成。省级新写 {stats['province_days_written']} 天，"
        f"节点新写 {stats['node_days_written']} 天。"
        f"总耗时 {time.perf_counter() - started:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()

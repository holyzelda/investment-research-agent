"""河南现货分区实时电价导入脚本（逐日文件，可直接从 IDE 运行）。

新数据源：``河南2601至06分区实时电价`` 目录，每个自然日一个 Excel。
每个逐日文件（如 ``2026-01-01日（实际）实时出清电价.xlsx``）含 24 个时刻点 × 5 条曲线：
4 个区域（豫中东/豫南/豫西/豫北）+ 省级“用户侧综合出清价”。
本脚本把两类数据都写入主库 ``ir_spot_price``：
- 区域 → ``area=区域名, station_name=区域名``
- 省级用户侧综合出清价 → ``area=河南, station_name=统一结算点``

修改 ``HENAN_DIRECTORY`` 到实际目录后直接运行 ``main()``；默认 dry-run，不写数据库。
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.modules.calculation.infrastructure.henan_spot_import import (  # noqa: E402
    import_henan_directory,
)

# 逐日分区实时电价目录；更换数据文件只需指向新目录（文件名带 2026-xx-xx 日期）。
HENAN_DIRECTORY = Path(r"D:/0_工作/2026/投研智能体/现货电价计算skill/河南电价/河南2601至06分区实时电价")
PRICE_TYPE = 1
WRITE_DATABASE = True


def main() -> None:
    started = time.perf_counter()
    report = import_henan_directory(
        HENAN_DIRECTORY,
        price_type=PRICE_TYPE,
        dry_run=not WRITE_DATABASE,
    )
    for error in report.errors:
        print(f"文件失败：{error}", flush=True)
    action = "正式写库" if WRITE_DATABASE else "dry-run（未写库）"
    print(
        f"河南分区实时电价导入完成：{action}，文件={report.files_seen}，"
        f"失败={report.files_failed}，原始行={report.rows_seen}，"
        f"有效曲线={report.valid_city_days}，无效={report.invalid_city_days}，"
        f"写入={report.written_rows}，耗时={time.perf_counter() - started:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
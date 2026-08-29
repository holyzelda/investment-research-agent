"""河南现货 Excel 导入脚本（可直接从 IDE 运行）。"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.modules.calculation.infrastructure.henan_spot_import import (  # noqa: E402
    import_henan_directory,
)

# 修改这里后直接运行 main()；默认 dry-run，不写数据库。
HENAN_DIRECTORY = Path(r"D:/0_工作/2026/投研智能体/现货电价计算skill/河南电价")
PROVINCE_FILE = HENAN_DIRECTORY / "1-7月河南省日前电价统一结算点电价.xlsx"
# 区域名是业务配置：文件名可以更换，但必须同步修改这里的区域名。
REGION_FILES = [
    (HENAN_DIRECTORY / "1-7月豫北电价.xlsx", "豫北"),
    # (HENAN_DIRECTORY / "1-7月豫西电价.xlsx", "豫西"),
    # (HENAN_DIRECTORY / "1-7月豫中东电价.xlsx", "豫中东"),
    # (HENAN_DIRECTORY / "1-7月豫南电价.xlsx", "豫南"),
]
PRICE_TYPE = 1
WRITE_DATABASE = True


def main() -> None:
    started = time.perf_counter()
    report = import_henan_directory(
        HENAN_DIRECTORY,
        province_file=PROVINCE_FILE,
        region_files=REGION_FILES,
        price_type=PRICE_TYPE,
        dry_run=not WRITE_DATABASE,
    )
    for error in report.errors:
        print(f"文件失败：{error}", flush=True)
    action = "正式写库" if WRITE_DATABASE else "dry-run（未写库）"
    print(
        f"河南 Excel 导入完成：{action}，文件={report.files_seen}，"
        f"失败={report.files_failed}，原始行={report.rows_seen}，"
        f"有效日={report.valid_city_days}，无效日={report.invalid_city_days}，"
        f"写入={report.written_rows}，耗时={time.perf_counter() - started:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()

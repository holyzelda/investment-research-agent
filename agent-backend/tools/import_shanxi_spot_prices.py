"""山西实时节点边际电价 Excel 导入工具。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.modules.calculation.infrastructure.shanxi_spot_import import (  # noqa: E402
    import_shanxi_directory,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="导入山西实时节点边际电价 Excel")
    parser.add_argument("directory", type=Path, help="年度目录，按月份子目录组织")
    parser.add_argument("--file", dest="files", action="append", type=Path,
                        help="只导入指定文件，可重复指定")
    parser.add_argument("--month", type=int, choices=range(1, 13),
                        help="只导入指定月份目录")
    parser.add_argument("--year", type=int, help="年度；未指定时从目录路径推断")
    parser.add_argument("--price-type", type=int, default=1)
    parser.add_argument("--write", action="store_true", help="正式写库；默认仅 dry-run")
    return parser


def main() -> None:
    args = _parser().parse_args()
    files = args.files
    if files is None and args.month is not None:
        files = sorted((args.directory / str(args.month)).glob("*.xlsx"))
        if not files:
            files = sorted((args.directory / f"{args.month:02d}").glob("*.xlsx"))
    report = import_shanxi_directory(
        args.directory,
        files=files,
        price_type=args.price_type,
        dry_run=not args.write,
        year=args.year,
    )
    for error in report.errors:
        print(f"文件失败：{error}", flush=True)
    print("山西导入完成：" + ", ".join(
        f"{key}={value}" for key, value in report.as_dict().items()
        if key not in {
            "errors",
            "skipped_node_days",
            "duplicate_node_day_details",
            "low_complete_day_details",
        }
    ), flush=True)
    if report.skipped_node_days:
        print(f"跳过节点日={len(report.skipped_node_days)}", flush=True)
    for detail in report.duplicate_node_day_details[:20]:
        print(f"同价母线去重：{detail}", flush=True)
    for detail in report.low_complete_day_details[:20]:
        print(f"低完整日节点清理：{detail}", flush=True)


if __name__ == "__main__":
    main()

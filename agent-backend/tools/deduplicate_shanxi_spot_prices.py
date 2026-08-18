"""清理已入库的山西冗余及低完整日节点。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.modules.calculation.infrastructure.shanxi_spot_import import (  # noqa: E402
    deduplicate_shanxi_spot_prices,
    remove_low_complete_day_shanxi_stations,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="清理山西冗余及低完整日节点")
    parser.add_argument("--price-type", type=int, default=1)
    parser.add_argument(
        "--write",
        action="store_true",
        help="正式删除；默认只预览拟删除记录",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    report = deduplicate_shanxi_spot_prices(
        price_type=args.price_type,
        dry_run=not args.write,
    )
    low_days = remove_low_complete_day_shanxi_stations(
        price_type=args.price_type,
        max_complete_days=30,
        dry_run=not args.write,
    )
    mode = "正式删除" if args.write else "预览"
    print(f"山西母线全覆盖去重{mode}：" + ", ".join(
        f"{key}={value}" for key, value in report.as_dict().items()
        if key != "examples"
    ), flush=True)
    for example in report.examples:
        print(f"母线示例：{example}", flush=True)
    print(f"山西低完整日节点清理{mode}：" + ", ".join(
        f"{key}={value}" for key, value in low_days.as_dict().items()
        if key != "examples"
    ), flush=True)
    for example in low_days.examples:
        print(f"低完整日节点：{example}", flush=True)


if __name__ == "__main__":
    main()

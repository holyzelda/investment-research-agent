"""河南现货双价格预计算脚本（逐日分区实时价，可直接从 IDE 运行）。

新契约：充电侧固定读取主库 ``河南/统一结算点``（逐日分区文件的“用户侧综合出清价”列），
放电侧读取各区域实时价曲线。两侧同日均为完整 96 点时，使用同一条双价格 DP 路径写入
``ir_spot_daily_optimal_henan``（省级条目充、放电均为统一结算点）。修改本文件顶部配置后直接运行 ``main()``。
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date
from decimal import Decimal, InvalidOperation
import os
import sys
import time
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config.settings import get_settings  # noqa: E402
from app.modules.calculation.domain.spot_pricing import (  # noqa: E402
    PRECOMPUTE_K_VALUES,
    day_optimal_by_k,
)
from app.modules.calculation.infrastructure.henan_spot_import import (  # noqa: E402
    _REGIONS,
)
from app.modules.calculation.infrastructure.spot_price_repo import (  # noqa: E402
    GRID_LABELS,
)


# ================= 河南预计算配置 =================
REGIONS = list(_REGIONS)
PRICE_TYPE = 1
WORKERS = 1
FORCE_RECOMPUTE = False
DRY_RUN = False
# 每次写入的日期批次；不是 K 值批次。
WRITE_BATCH_DAYS = 25
# =================================================


_CHARGE_AREA = "河南"
_CHARGE_STATION = "统一结算点"
_RESULT_TABLE = "ir_spot_daily_optimal_henan"


def _to_decimal(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, AttributeError):
        return None
    return result if result.is_finite() else None


def _parse_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _fetch_daily_prices(
    conn,
    *,
    area: str,
    station_name: str,
    price_type: int,
) -> dict[date, list[Decimal]]:
    """读取主库宽表，只返回恰好 96 点且全部可解析的日期。"""
    columns = ", ".join(f"`{label}`" for label in GRID_LABELS)
    rows = conn.execute(
        text(
            f"SELECT `date`, {columns} FROM ir_spot_price "
            "WHERE area=:area AND station_name=:station AND price_type=:pt "
            "ORDER BY `date`"
        ),
        {"area": area, "station": station_name, "pt": price_type},
    )
    daily: dict[date, list[Decimal]] = {}
    for row in rows:
        business_date = _parse_date(row[0])
        if business_date is None or business_date in daily:
            continue
        prices = [_to_decimal(value) for value in row[1:]]
        if len(prices) == len(GRID_LABELS) and all(price is not None for price in prices):
            daily[business_date] = prices  # type: ignore[assignment]
    return daily


def _compute_day(args):
    day_iso, charge_prices, discharge_prices = args
    result = day_optimal_by_k(
        [Decimal(value) for value in charge_prices],
        k_values=PRECOMPUTE_K_VALUES,
        discharge_prices=[Decimal(value) for value in discharge_prices],
    )
    return day_iso, {k: (str(cs), str(ds), slots) for k, (cs, ds, slots) in result.items()}


def _done_dates(conn, region: str) -> set[date]:
    rows = conn.execute(
        text(
            f"SELECT DISTINCT business_date FROM {_RESULT_TABLE} "
            "WHERE province=:province AND region=:region"
        ),
        {"province": "河南", "region": region},
    )
    return {parsed for row in rows if (parsed := _parse_date(row[0])) is not None}


def _upsert_days(conn, region: str, results: list[tuple[str, dict]]) -> None:
    if not results:
        return
    if conn.dialect.name == "sqlite":
        statement = text(
            f"INSERT INTO {_RESULT_TABLE} "
            "(province, region, business_date, k, charge_sum, discharge_sum, slot_count) "
            "VALUES (:province, :region, :day, :k, :cs, :ds, :slots) "
            "ON CONFLICT (province, region, business_date, k) DO UPDATE SET "
            "charge_sum=excluded.charge_sum, discharge_sum=excluded.discharge_sum, "
            "slot_count=excluded.slot_count"
        )
    else:
        statement = text(
            f"INSERT INTO {_RESULT_TABLE} "
            "(province, region, business_date, k, charge_sum, discharge_sum, slot_count) "
            "VALUES (:province, :region, :day, :k, :cs, :ds, :slots) "
            "ON DUPLICATE KEY UPDATE charge_sum=VALUES(charge_sum), "
            "discharge_sum=VALUES(discharge_sum), slot_count=VALUES(slot_count)"
        )
    params = []
    for day_iso, by_k in results:
        for k, (charge_sum, discharge_sum, slots) in by_k.items():
            params.append({
                "province": "河南",
                "region": region,
                "day": day_iso,
                "k": k,
                "cs": charge_sum,
                "ds": discharge_sum,
                "slots": slots,
            })
    conn.execute(statement, params)


def _engine() -> Engine:
    settings = get_settings()
    dsn = settings.database.url.replace("+aiomysql", "+pymysql")
    return create_engine(dsn, pool_pre_ping=True)


def _process_region(
    engine: Engine,
    region: str,
    *,
    discharge_region: str | None = None,
    price_type: int,
    workers: int,
    force: bool,
    dry_run: bool,
    write_batch_days: int,
) -> dict:
    with engine.connect() as conn:
        charge = _fetch_daily_prices(
            conn, area=_CHARGE_AREA, station_name=_CHARGE_STATION, price_type=price_type
        )
        discharge = _fetch_daily_prices(
            conn,
            area=_CHARGE_AREA if discharge_region is None else discharge_region,
            station_name=_CHARGE_STATION if discharge_region is None else discharge_region,
            price_type=price_type,
        )
        common_days = sorted(charge.keys() & discharge.keys())
        done = _done_dates(conn, region)

    todo_days = common_days if force else [day for day in common_days if day not in done]
    summary = {
        "region": region,
        "complete_days": len(common_days),
        "existing_days": len(done & set(common_days)),
        "to_write": len(todo_days),
        "written_days": 0,
        "status": "dry_run" if dry_run else "pending",
    }
    if dry_run or not todo_days:
        summary["status"] = "dry_run" if dry_run else "up_to_date"
        return summary

    jobs = [
        (
            day.isoformat(),
            [str(value) for value in charge[day]],
            [str(value) for value in discharge[day]],
        )
        for day in todo_days
    ]
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_compute_day, job) for job in jobs]
            result_iter = (future.result() for future in as_completed(futures))
            _write_results(engine, region, result_iter, write_batch_days, summary)
    else:
        _write_results(engine, region, (_compute_day(job) for job in jobs), write_batch_days, summary)

    summary["status"] = "written" if summary["written_days"] else "up_to_date"
    return summary


def _write_results(engine, region, result_iter, write_batch_days, summary) -> None:
    buffer = []
    for result in result_iter:
        buffer.append(result)
        if len(buffer) >= write_batch_days:
            with engine.begin() as conn:
                _upsert_days(conn, region, buffer)
            summary["written_days"] += len(buffer)
            buffer.clear()
    if buffer:
        with engine.begin() as conn:
            _upsert_days(conn, region, buffer)
        summary["written_days"] += len(buffer)


def run_henan_precompute(
    *,
    regions: list[str],
    price_type: int = 1,
    workers: int = 1,
    force: bool = False,
    dry_run: bool = True,
    write_batch_days: int = WRITE_BATCH_DAYS,
    ir_engine: Engine | None = None,
) -> dict:
    """运行河南区域双价格预计算；仅访问主库价格表和河南结果表。"""
    if not regions:
        raise ValueError("regions 不能为空")
    if workers < 1:
        raise ValueError("workers 必须大于 0")
    if write_batch_days < 1:
        raise ValueError("write_batch_days 必须大于 0")
    engine = ir_engine or _engine()
    if not inspect(engine).has_table(_RESULT_TABLE):
        raise RuntimeError(f"结果表不存在，请先执行河南结果表 DDL：{_RESULT_TABLE}")
    scopes = ["省级", *regions]
    summaries = []
    for region in scopes:
        if region != "省级" and region not in _REGIONS:
            raise ValueError(f"不支持的河南区域：{region}")
        try:
            # 省级条目充、放电均为统一结算点（现有双价格 DP 的退化输入）。
            summary = _process_region(
                engine,
                region,
                discharge_region=None if region == "省级" else region,
                price_type=price_type,
                workers=workers,
                force=force,
                dry_run=dry_run,
                write_batch_days=write_batch_days,
            )
        except Exception as exc:  # noqa: BLE001
            summary = {
                "region": region,
                "complete_days": 0,
                "existing_days": 0,
                "to_write": 0,
                "written_days": 0,
                "status": "failed",
                "error": f"{type(exc).__name__}: {str(exc)[:200]}",
            }
        summaries.append(summary)

    return {
        "province": "河南",
        "regions": summaries,
        "region_count": len(regions),
        "scope_count": len(summaries),
        "total_written_days": sum(item["written_days"] for item in summaries),
    }


def main() -> None:
    started = time.perf_counter()
    stats = run_henan_precompute(
        regions=REGIONS,
        price_type=PRICE_TYPE,
        workers=WORKERS,
        force=FORCE_RECOMPUTE,
        dry_run=DRY_RUN,
        write_batch_days=WRITE_BATCH_DAYS,
    )
    action = "预计处理" if DRY_RUN else "实际写入"
    province_summary = stats["regions"][0]
    print(
        f"河南省级双价格：完整日={province_summary['complete_days']}，"
        f"已有日={province_summary['existing_days']}，待计算={province_summary['to_write']}，"
        f"{action}={province_summary['written_days']}，状态={province_summary['status']}",
        flush=True,
    )
    for item in stats["regions"][1:]:
        suffix = f"，错误={item['error']}" if item.get("error") else ""
        print(
            f"{item['region']}：共同完整日={item['complete_days']}，"
            f"已有日={item['existing_days']}，待计算={item['to_write']}，"
            f"{action}={item['written_days']}，状态={item['status']}"
            f"{suffix}",
            flush=True,
        )
    print(
        f"河南双价格预计算完成：省级={province_summary['written_days']}天，"
        f"区域={stats['region_count']}，{action}={stats['total_written_days']}天，"
        f"耗时={time.perf_counter() - started:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()

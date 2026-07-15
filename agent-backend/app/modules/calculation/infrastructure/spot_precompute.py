"""现货电价多循环 DP 预计算（供手动脚本与应用内日更调度共用）。

把 (区域/站点, 日期, K) 的当日最优结果写入 ir_agent 预计算表；逐 identifier
一次事务提交，已写日期自动跳过，支持中断续跑和滚动一年清理。
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, text

from app.core.config.settings import get_settings
from app.modules.calculation.domain.spot_pricing import day_optimal_by_k
from app.modules.calculation.infrastructure.spot_price_repo import (
    NodeSpotRepository,
    ProvinceSpotRepository,
)


PROVINCE_PRECOMPUTE_SPECS = (
    ("安徽", "日前", "安徽"), ("山东", "日前", "山东"),
    ("山西", "日前", "山西"), ("广东", "日前", "广东"),
    ("浙江", "日前", "浙江"), ("湖北", "日前", "湖北"),
    ("甘肃", "日前", "甘肃"), ("蒙西-全网", "实时", "蒙西"),
    ("陕西", "日前", "陕西"), ("河北南网", "日前", "河北南网"),
    ("福建", "日前", "福建"), ("辽宁", "日前", "辽宁"),
    ("云南", "日前", "云南"), ("广西", "日前", "广西"),
    ("海南", "日前", "海南"), ("贵州", "日前", "贵州"),
    ("黑龙江", "日前", "黑龙江"), ("吉林", "日前", "吉林"),
    ("新疆", "日前", "新疆"), ("江苏-全网", "日前", "江苏"),
    ("宁夏", "日前", "宁夏"), ("江西", "日前", "江西"),
    ("河南", "日前", "河南"), ("蒙东", "日前", "蒙东"),
    ("湖南", "日前", "湖南"), ("重庆", "日前", "重庆"),
    ("青海", "日前", "青海"), ("上海", "日前", "上海"),
    ("四川", "日前", "四川"),
)


def log(msg):
    print(msg, flush=True)


def _window(run_date):
    try:
        start = run_date.replace(year=run_date.year - 1)
    except ValueError:
        start = run_date.replace(year=run_date.year - 1, day=28)
    return start, run_date


def _compute_day(args):
    """子进程 worker（纯 CPU，无 DB）。"""
    day_iso, prices_str = args
    prices = [Decimal(p) for p in prices_str]
    by_k = day_optimal_by_k(prices)
    return day_iso, {k: (str(cs), str(ds), slots) for k, (cs, ds, slots) in by_k.items()}


def _done_dates(conn, table, scope_id, start, end):
    where = " AND ".join(f"{key}=:{key}" for key in scope_id)
    rows = conn.execute(text(
        f"SELECT DISTINCT business_date FROM {table} "
        f"WHERE {where} AND business_date>=:s AND business_date<:e"),
        {**scope_id, "s": start, "e": end})
    return {row[0] if isinstance(row[0], date) else date.fromisoformat(str(row[0])) for row in rows}


def _upsert_day(conn, table, scope_id, day_iso, by_k):
    id_cols = list(scope_id.keys())
    cols = ", ".join(id_cols) + ", business_date, k, charge_sum, discharge_sum, slot_count"
    vals = ", ".join(f":{column}" for column in id_cols) + ", :d, :k, :cs, :ds, :sl"
    if conn.dialect.name == "sqlite":
        conflict_cols = ", ".join(id_cols + ["k", "business_date"])
        upsert = (
            f"INSERT INTO {table} ({cols}) VALUES ({vals}) "
            f"ON CONFLICT ({conflict_cols}) DO UPDATE SET "
            "charge_sum=excluded.charge_sum, discharge_sum=excluded.discharge_sum, "
            "slot_count=excluded.slot_count"
        )
    else:
        upsert = (
            f"INSERT INTO {table} ({cols}) VALUES ({vals}) ON DUPLICATE KEY UPDATE "
            "charge_sum=VALUES(charge_sum), discharge_sum=VALUES(discharge_sum), "
            "slot_count=VALUES(slot_count)"
        )
    for k, (charge_sum, discharge_sum, slot_count) in by_k.items():
        conn.execute(text(upsert), {
            **scope_id, "d": day_iso, "k": k,
            "cs": str(charge_sum), "ds": str(discharge_sum), "sl": slot_count,
        })


def _process_identifier(ex, ir, repo, identifier, start, end, table, scope_id, mode=None):
    """取一个 identifier 的完整日，计算未完成日并一次事务写入，返回写入日数。"""
    with ir.connect() as conn:
        done = _done_dates(conn, table, scope_id, start, end)
    try:
        daily = (
            repo.fetch_daily_prices(identifier, mode, start, end)
            if mode is not None
            else repo.fetch_daily_prices(identifier, start, end)
        )
    except Exception as exc:  # noqa: BLE001
        log(f"  跳过 {identifier}: {type(exc).__name__}: {str(exc)[:60]}")
        return 0

    todo = {day: prices for day, prices in daily.items() if day not in done}
    if not todo:
        log(f"  {identifier}: 全部已回填（{len(done)}天），跳过")
        return 0
    if ex is None:
        results = [
            _compute_day((day.isoformat(), [str(price) for price in prices]))
            for day, prices in todo.items()
        ]
    else:
        futures = [
            ex.submit(_compute_day, (day.isoformat(), [str(price) for price in prices]))
            for day, prices in todo.items()
        ]
        results = [future.result() for future in as_completed(futures)]

    with ir.begin() as conn:
        for day_iso, by_k_str in results:
            by_k = {
                k: (Decimal(charge_sum), Decimal(discharge_sum), slot_count)
                for k, (charge_sum, discharge_sum, slot_count) in by_k_str.items()
            }
            _upsert_day(conn, table, scope_id, day_iso, by_k)
    log(f"  {identifier}: 新写 {len(results)} 天（已有 {len(done)} 天）")
    return len(results)


def run_precompute(
    run_date: date,
    node_stations: list[str],
    node_province: str = "蒙西",
    workers: int = 10,
    cleanup_old: bool = True,
    province_repo=None,
    node_repo=None,
    ir_engine=None,
) -> dict:
    """回填或日更预计算，返回本次省级/节点级写入的日期数。"""
    settings = get_settings()
    spot = settings.spot_price
    ir = ir_engine or create_engine(
        settings.database.url.replace("+aiomysql", "+pymysql"), pool_pre_ping=True)
    start, end = _window(run_date)
    log(f"窗口=[{start},{end})  workers={workers}")

    province_repo = province_repo or ProvinceSpotRepository(
        spot.province_dsn, spot.province_table, spot.province_market)
    node_repo = node_repo or NodeSpotRepository(spot.node_dsn, spot.node_table, spot.node_price_type)
    province_written = 0
    node_written = 0
    executor = ProcessPoolExecutor(max_workers=workers) if workers > 1 else None

    try:
        log(f"省级区域 {len(PROVINCE_PRECOMPUTE_SPECS)} 个")
        for area, mode, province in PROVINCE_PRECOMPUTE_SPECS:
            province_written += _process_identifier(
                executor, ir, province_repo, area, start, end,
                "ir_spot_daily_optimal_province", {"province": province}, mode=mode)

        stations = node_stations
        if stations == ["*"]:
            with node_repo._eng().connect() as conn:
                stations = [row[0] for row in conn.execute(text(
                    f"SELECT DISTINCT station_name FROM {spot.node_table} WHERE price_type=:pt"),
                    {"pt": spot.node_price_type})]
        log(f"节点站点 {len(stations)} 个")
        for station in stations:
            node_written += _process_identifier(
                executor, ir, node_repo, station, start, end,
                "ir_spot_daily_optimal_node",
                {"province": node_province, "station_name": station})
            with ir.begin() as conn:
                conn.execute(text(
                    "INSERT INTO ir_spot_station (province, station_name, last_seen) "
                    "VALUES (:p,:s,:d) ON DUPLICATE KEY UPDATE last_seen=VALUES(last_seen)"),
                    {"p": node_province, "s": station, "d": (end - timedelta(days=1)).isoformat()})
    finally:
        if executor is not None:
            executor.shutdown(wait=True)

    if cleanup_old:
        with ir.begin() as conn:
            for table in ("ir_spot_daily_optimal_province", "ir_spot_daily_optimal_node"):
                result = conn.execute(
                    text(f"DELETE FROM {table} WHERE business_date < :s"), {"s": start})
                log(f"清理 {table} 旧数据 {result.rowcount} 行")

    return {"province_days_written": province_written, "node_days_written": node_written}

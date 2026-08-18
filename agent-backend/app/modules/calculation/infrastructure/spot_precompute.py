"""现货电价多循环 DP 预计算（供手动脚本与应用内日更调度共用）。

把 (区域/站点, 日期, K) 的当日最优结果写入 ir_agent 预计算表；逐 identifier
一次事务提交，已写日期自动跳过，支持中断续跑和滚动一年清理。
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date, timedelta
from decimal import Decimal
from time import perf_counter

from sqlalchemy import create_engine, text

from app.core.config.settings import get_settings
from app.modules.calculation.domain.spot_pricing import day_optimal_by_k
from app.modules.calculation.infrastructure.spot_price_repo import (
    NodeSpotRepository,
    ProvinceSpotRepository,
    UploadedNodeSpotRepository,
)


UPLOADED_WRITE_BATCH_DAYS = 25


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


def _upsert_days(conn, table, scope_id, results):
    """批量 upsert 多个节点日，减少逐个 k 执行 SQL 的往返次数。"""
    if not results:
        return
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
    params = []
    for day_iso, by_k_str in results:
        for k, (charge_sum, discharge_sum, slot_count) in by_k_str.items():
            params.append({
                **scope_id, "d": day_iso, "k": k,
                "cs": str(charge_sum), "ds": str(discharge_sum), "sl": slot_count,
            })
    conn.execute(text(upsert), params)


def _upsert_day(conn, table, scope_id, day_iso, by_k):
    """兼容单日调用；批量路径使用 _upsert_days。"""
    _upsert_days(conn, table, scope_id, [(day_iso, {
        k: (str(charge_sum), str(discharge_sum), slot_count)
        for k, (charge_sum, discharge_sum, slot_count) in by_k.items()
    })])


def _upsert_station(conn, province, station_name, last_seen):
    if conn.dialect.name == "sqlite":
        statement = (
            "INSERT INTO ir_spot_station (province, station_name, last_seen) "
            "VALUES (:p,:s,:d) ON CONFLICT (province, station_name) DO UPDATE SET "
            "last_seen=excluded.last_seen"
        )
    else:
        statement = (
            "INSERT INTO ir_spot_station (province, station_name, last_seen) "
            "VALUES (:p,:s,:d) ON DUPLICATE KEY UPDATE last_seen=VALUES(last_seen)"
        )
    conn.execute(text(statement), {"p": province, "s": station_name, "d": last_seen})


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
        log(f"  跳过 {identifier}: {type(exc).__name__}: {str(exc)[:200]}")
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
                _upsert_station(
                    conn,
                    node_province,
                    station,
                    (end - timedelta(days=1)).isoformat(),
                )
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


def run_uploaded_node_precompute(
    *,
    province: str,
    stations: list[str],
    workers: int = 4,
    force: bool = True,
    dry_run: bool = False,
    price_type: int = 1,
    write_batch_days: int = UPLOADED_WRITE_BATCH_DAYS,
    ir_engine=None,
    uploaded_repo=None,
) -> dict:
    """按上传节点各自最后完整日回填主库文件节点。"""
    if write_batch_days < 1:
        raise ValueError("write_batch_days 必须大于 0")
    settings = get_settings()
    ir = ir_engine or create_engine(
        settings.database.url.replace("+aiomysql", "+pymysql"), pool_pre_ping=True)
    repo = uploaded_repo or UploadedNodeSpotRepository(
        settings.database.url.replace("+aiomysql", "+pymysql"),
        "ir_spot_price",
        price_type,
    )
    selected = repo.list_stations(province) if stations == ["*"] else list(stations)
    summaries = []
    station_count = len(selected)
    total_written = 0
    executor = (
        ProcessPoolExecutor(max_workers=workers)
        if not dry_run and workers > 1
        else None
    )
    log(
        f"文件节点预计算开始：省份={province} 节点={station_count} "
        f"workers={workers} force={force} dry_run={dry_run}"
    )
    if not dry_run:
        log("逐节点有界计算：每次只提交当前节点的待计算日期")

    try:
        for station_index, station in enumerate(selected, start=1):
            prefix = f"[{station_index}/{station_count}] {station}"
            station_started = perf_counter()
            log(f"{prefix}：开始扫描完整数据日")
            read_started = perf_counter()
            all_daily = repo.fetch_daily_prices(province, station)
            read_elapsed = perf_counter() - read_started
            last_valid = max(all_daily, default=None)
            if last_valid is None:
                log(
                    f"{prefix}：无完整 96 点数据日，跳过，"
                    f"读取耗时={read_elapsed:.1f}s"
                )
                summaries.append({"station_name": station, "status": "no_complete_day"})
                continue

            end = last_valid + timedelta(days=1)
            start, _ = _window(end)
            daily = {
                day: prices for day, prices in all_daily.items()
                if start <= day < end
            }
            with ir.connect() as conn:
                done = _done_dates(
                    conn,
                    "ir_spot_daily_optimal_node",
                    {"province": province, "station_name": station},
                    start,
                    end,
                )
            todo = daily if force else {
                day: prices for day, prices in daily.items() if day not in done
            }
            summary = {
                "station_name": station,
                "last_valid_date": last_valid.isoformat(),
                "start": start.isoformat(),
                "end_exclusive": end.isoformat(),
                "complete_days": len(daily),
                "existing_days": len(done),
                "to_write": len(todo),
                "status": "dry_run" if dry_run else "pending",
            }
            log(
                f"{prefix}：last={last_valid} window=[{start},{end}) "
                f"完整日={len(daily)} 已有={len(done)} 待计算={len(todo)} "
                f"读取耗时={read_elapsed:.1f}s"
            )
            if dry_run:
                log(f"{prefix}：预览完成，不计算、不写库")
                summaries.append(summary)
                continue

            if executor is None:
                result_iter = (
                    _compute_day((day.isoformat(), [str(price) for price in prices]))
                    for day, prices in todo.items()
                )
            else:
                futures = [
                    executor.submit(
                        _compute_day,
                        (day.isoformat(), [str(price) for price in prices]),
                    )
                    for day, prices in todo.items()
                ]
                result_iter = (
                    future.result() for future in as_completed(futures)
                )

            result_count = len(todo)
            progress_step = max(1, min(25, result_count // 20))
            result_buffer = []
            completed = 0
            written = 0
            write_elapsed = 0.0
            compute_started = perf_counter()
            scope_id = {"province": province, "station_name": station}

            for result in result_iter:
                result_buffer.append(result)
                completed += 1
                if completed == result_count or completed % progress_step == 0:
                    log(f"{prefix}：DP计算进度 {completed}/{result_count}")
                if len(result_buffer) < write_batch_days:
                    continue

                write_started = perf_counter()
                with ir.begin() as conn:
                    _upsert_days(
                        conn,
                        "ir_spot_daily_optimal_node",
                        scope_id,
                        result_buffer,
                    )
                write_elapsed += perf_counter() - write_started
                written += len(result_buffer)
                result_buffer.clear()
                log(f"{prefix}：批量写入进度 {written}/{result_count}")

            if result_buffer:
                write_started = perf_counter()
                with ir.begin() as conn:
                    _upsert_days(
                        conn,
                        "ir_spot_daily_optimal_node",
                        scope_id,
                        result_buffer,
                    )
                write_elapsed += perf_counter() - write_started
                written += len(result_buffer)
                result_buffer.clear()
                log(f"{prefix}：批量写入进度 {written}/{result_count}")

            if result_count == 0:
                log(f"{prefix}：无待计算日期，仅更新节点最后数据日")

            compute_elapsed = perf_counter() - compute_started - write_elapsed
            with ir.begin() as conn:
                _upsert_station(conn, province, station, last_valid.isoformat())

            total_written += written
            summary["status"] = "written" if written else "up_to_date"
            summaries.append(summary)
            log(
                f"{prefix}：完成，实际写入={written} 个节点日，"
                f"ir_spot_station.last_seen={last_valid}，"
                f"DP计算耗时={compute_elapsed:.1f}s，"
                f"数据库写入耗时={write_elapsed:.1f}s，"
                f"节点总耗时={perf_counter() - station_started:.1f}s，"
                f"累计实际写入={total_written}"
            )
    finally:
        if executor is not None:
            executor.shutdown(wait=True)

    return {
        "province": province,
        "stations": summaries,
        "station_count": len(summaries),
        "node_days_written": total_written,
    }

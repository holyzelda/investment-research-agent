from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.modules.calculation.infrastructure import spot_precompute
from app.modules.calculation.infrastructure.spot_precompute import (
    run_uploaded_node_precompute,
)
from app.modules.calculation.infrastructure.spot_price_repo import (
    GRID_LABELS,
    UploadedNodeSpotRepository,
)


def _source_engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    columns = ", ".join(f'"{label}" NUMERIC' for label in GRID_LABELS)
    with engine.begin() as conn:
        conn.execute(text(f'''CREATE TABLE ir_spot_price (
            area TEXT, station_name TEXT, price_type INTEGER, date TEXT, {columns}
        )'''))
    return engine


def _ir_engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with engine.begin() as conn:
        conn.execute(text('''CREATE TABLE ir_spot_daily_optimal_node (
            province TEXT, station_name TEXT, business_date TEXT, k INTEGER,
            charge_sum NUMERIC, discharge_sum NUMERIC, slot_count INTEGER,
            PRIMARY KEY (province, station_name, business_date, k)
        )'''))
        conn.execute(text('''CREATE TABLE ir_spot_station (
            province TEXT, station_name TEXT, last_seen TEXT,
            PRIMARY KEY (province, station_name)
        )'''))
    return engine


def _insert_day(engine, area, station, price_type, day, value="1"):
    columns = ", ".join(f'"{label}"' for label in GRID_LABELS)
    values = ", ".join(f":v{i}" for i in range(96))
    params = {"area": area, "station": station, "pt": price_type, "date": day.isoformat()}
    params.update({f"v{i}": value for i in range(96)})
    with engine.begin() as conn:
        conn.execute(text(
            f"INSERT INTO ir_spot_price (area, station_name, price_type, date, {columns}) "
            f"VALUES (:area, :station, :pt, :date, {values})"
        ), params)


def test_uploaded_repository_filters_area_price_type_and_ignores_incomplete_days():
    engine = _source_engine()
    _insert_day(engine, "甘肃", "节点A", 1, date(2026, 7, 1), "2")
    _insert_day(engine, "青海", "节点A", 1, date(2026, 7, 2), "3")
    _insert_day(engine, "甘肃", "节点A", 2, date(2026, 7, 3), "4")
    with engine.begin() as conn:
        conn.execute(text('UPDATE ir_spot_price SET "24:00"=NULL WHERE area=\'甘肃\' AND price_type=1'))
    _insert_day(engine, "甘肃", "节点A", 1, date(2026, 7, 4), "5")

    repo = UploadedNodeSpotRepository("sqlite://", price_type=1)
    repo._engine = engine
    assert repo.list_stations("甘肃") == ["节点A"]
    assert repo.fetch_daily_prices("甘肃", "节点A") == {date(2026, 7, 4): [Decimal("5")] * 96}
    assert repo.last_complete_date("甘肃", "节点A") == date(2026, 7, 4)


def test_uploaded_precompute_uses_independent_windows_and_force_overwrites():
    source = _source_engine()
    for day in (date(2025, 8, 1), date(2026, 7, 1)):
        _insert_day(source, "甘肃", "节点A", 1, day, "1")
    for day in (date(2026, 1, 1), date(2026, 7, 3)):
        _insert_day(source, "甘肃", "节点B", 1, day, "2")
    _insert_day(source, "青海", "节点A", 1, date(2026, 7, 4), "9")

    source_repo = UploadedNodeSpotRepository("sqlite://", price_type=1)
    source_repo._engine = source
    ir = _ir_engine()
    with ir.begin() as conn:
        conn.execute(text("INSERT INTO ir_spot_daily_optimal_node VALUES ('甘肃','节点A','2026-07-01',1,0,0,0)"))

    result = run_uploaded_node_precompute(
        province="甘肃", stations=["*"], workers=1, force=True,
        ir_engine=ir, uploaded_repo=source_repo,
    )
    assert result["station_count"] == 2
    summaries = {item["station_name"]: item for item in result["stations"]}
    assert summaries["节点A"]["last_valid_date"] == "2026-07-01"
    assert summaries["节点A"]["start"] == "2025-07-02"
    assert summaries["节点B"]["start"] == "2025-07-04"
    assert result["node_days_written"] == 4
    with ir.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM ir_spot_daily_optimal_node")).scalar() > 0
        assert conn.execute(text("SELECT last_seen FROM ir_spot_station WHERE station_name='节点A'")).scalar() == "2026-07-01"


def test_uploaded_precompute_bounds_submissions_to_current_station(monkeypatch):
    source = _source_engine()
    for day in (date(2026, 7, 1), date(2026, 7, 2)):
        _insert_day(source, "甘肃", "节点A", 1, day, "1")
    _insert_day(source, "甘肃", "节点B", 1, date(2026, 7, 3), "2")
    repo = UploadedNodeSpotRepository("sqlite://", price_type=1)
    repo._engine = source
    ir = _ir_engine()
    executors = []
    station_write_submission_counts = []
    original_upsert_station = spot_precompute._upsert_station

    class ImmediateFuture:
        def __init__(self, result):
            self._result = result

        def result(self):
            return self._result

    class RecordingExecutor:
        def __init__(self, max_workers):
            self.max_workers = max_workers
            self.submitted = []
            self.shutdown_called = False
            executors.append(self)

        def submit(self, function, args):
            self.submitted.append(args[0])
            return ImmediateFuture(function(args))

        def shutdown(self, wait=True):
            self.shutdown_called = wait

    def record_upsert_station(conn, province, station_name, last_seen):
        station_write_submission_counts.append(len(executors[0].submitted))
        original_upsert_station(conn, province, station_name, last_seen)

    monkeypatch.setattr(spot_precompute, "ProcessPoolExecutor", RecordingExecutor)
    monkeypatch.setattr(spot_precompute, "as_completed", lambda futures: futures)
    monkeypatch.setattr(spot_precompute, "_upsert_station", record_upsert_station)

    result = run_uploaded_node_precompute(
        province="甘肃",
        stations=["节点A", "节点B"],
        workers=2,
        force=True,
        ir_engine=ir,
        uploaded_repo=repo,
    )

    assert result["node_days_written"] == 3
    assert len(executors) == 1
    assert executors[0].max_workers == 2
    assert executors[0].submitted == [
        "2026-07-01",
        "2026-07-02",
        "2026-07-03",
    ]
    assert station_write_submission_counts == [2, 3]
    assert executors[0].shutdown_called is True
    with ir.connect() as conn:
        assert conn.execute(text(
            "SELECT COUNT(*) FROM ir_spot_station WHERE province='甘肃'"
        )).scalar() == 2


def test_uploaded_precompute_dry_run_and_skips_existing_days():
    source = _source_engine()
    _insert_day(source, "甘肃", "节点A", 1, date(2026, 7, 1))
    repo = UploadedNodeSpotRepository("sqlite://", price_type=1)
    repo._engine = source
    ir = _ir_engine()
    dry = run_uploaded_node_precompute(
        province="甘肃", stations=["节点A"], workers=1, dry_run=True,
        ir_engine=ir, uploaded_repo=repo,
    )
    assert dry["node_days_written"] == 0
    with ir.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM ir_spot_station")).scalar() == 0

    with ir.begin() as conn:
        conn.execute(text("INSERT INTO ir_spot_daily_optimal_node VALUES ('甘肃','节点A','2026-07-01',1,0,0,0)"))
    result = run_uploaded_node_precompute(
        province="甘肃", stations=["节点A"], workers=1, force=False,
        ir_engine=ir, uploaded_repo=repo,
    )
    assert result["node_days_written"] == 0


def test_uploaded_precompute_writes_completed_days_in_batches(monkeypatch):
    source = _source_engine()
    start = date(2026, 6, 1)
    for offset in range(5):
        _insert_day(source, "甘肃", "节点A", 1, start + timedelta(days=offset))
    repo = UploadedNodeSpotRepository("sqlite://", price_type=1)
    repo._engine = source
    ir = _ir_engine()
    batch_sizes = []
    station_write_counts = []
    original_upsert_days = spot_precompute._upsert_days
    original_upsert_station = spot_precompute._upsert_station

    def compute_day(args):
        day_iso, _ = args
        return day_iso, {8: ("1", "2", 3)}

    def record_upsert_days(conn, table, scope_id, results):
        batch_sizes.append(len(results))
        original_upsert_days(conn, table, scope_id, results)

    def record_upsert_station(conn, province, station_name, last_seen):
        station_write_counts.append(conn.execute(text(
            "SELECT COUNT(DISTINCT business_date) "
            "FROM ir_spot_daily_optimal_node WHERE station_name=:station"
        ), {"station": station_name}).scalar())
        original_upsert_station(conn, province, station_name, last_seen)

    monkeypatch.setattr(spot_precompute, "_compute_day", compute_day)
    monkeypatch.setattr(spot_precompute, "_upsert_days", record_upsert_days)
    monkeypatch.setattr(spot_precompute, "_upsert_station", record_upsert_station)

    result = run_uploaded_node_precompute(
        province="甘肃",
        stations=["节点A"],
        workers=1,
        force=True,
        write_batch_days=2,
        ir_engine=ir,
        uploaded_repo=repo,
    )

    assert result["node_days_written"] == 5
    assert batch_sizes == [2, 2, 1]
    assert station_write_counts == [5]
    with ir.connect() as conn:
        assert conn.execute(text(
            "SELECT COUNT(*) FROM ir_spot_daily_optimal_node"
        )).scalar() == 5
        assert conn.execute(text(
            "SELECT last_seen FROM ir_spot_station WHERE station_name='节点A'"
        )).scalar() == "2026-06-05"


def test_uploaded_precompute_rejects_invalid_write_batch_size():
    try:
        run_uploaded_node_precompute(
            province="甘肃",
            stations=[],
            write_batch_days=0,
        )
    except ValueError as exc:
        assert str(exc) == "write_batch_days 必须大于 0"
    else:
        raise AssertionError("write_batch_days=0 should fail")

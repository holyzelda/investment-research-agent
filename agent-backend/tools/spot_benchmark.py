"""现货电价预计算结果 · 基准脚本（手动执行，非 pytest）。

入参：省份 节点 容量 功率 循环 起始日 结束日
  - 节点给 "" 或 "-" 表示无节点 → 查省级预计算表(按省份)；否则查节点预计算表(按 station_name)。
用法（agent-backend 目录）：
  .venv\\Scripts\\python.exe tools\\spot_benchmark.py
"""
import os
import sys
import time
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

from app.core.config.settings import get_settings
from app.modules.calculation.domain.spot_pricing import k_from_inputs


def main() -> None:
    # ================= 参数配置区 =================
    province = "山西"
    node = "芮城站"  # 节点，给 "" 或 "-" 表示无节点（查省级预计算表）
    capacity = "400"  # 容量 (MWh)
    power = "200"  # 功率 (MW)
    cycles = "1"  # 循环次数
    start_s = "2025-01-01"  # 起始日 (YYYY-MM-DD)
    end_s = "2026-01-01"  # 结束日 (YYYY-MM-DD)
    # ==============================================
    capacity, power, cycles = Decimal(capacity), Decimal(power), Decimal(cycles)
    start = datetime.strptime(start_s, "%Y-%m-%d").date()
    end = datetime.strptime(end_s, "%Y-%m-%d").date()
    node = node if node not in ("", "-") else None

    sp = get_settings().spot_price
    k = k_from_inputs(capacity, power, cycles)
    if node:
        source_label = "节点"
        identifier = node
        sql = (
            "SELECT SUM(charge_sum), SUM(discharge_sum), SUM(slot_count) "
            "FROM ir_spot_daily_optimal_node "
            "WHERE province=:p AND station_name=:st AND k=:k "
            "AND business_date>=:s AND business_date<:e"
        )
        params = {"p": province, "st": node, "k": k, "s": start, "e": end}
    else:
        source_label = "省级"
        identifier = province
        sql = (
            "SELECT SUM(charge_sum), SUM(discharge_sum), SUM(slot_count) "
            "FROM ir_spot_daily_optimal_province "
            "WHERE province=:p AND k=:k "
            "AND business_date>=:s AND business_date<:e"
        )
        params = {"p": province, "k": k, "s": start, "e": end}
    print(f"{source_label} id={identifier} 容量={capacity} 功率={power} "
          f"循环={cycles} K={k} 区间=[{start},{end})")

    ir = create_engine(
        get_settings().database.url.replace("+aiomysql", "+pymysql"),
        pool_pre_ping=True,
    )
    t0 = time.perf_counter()
    with ir.connect() as conn:
        sum_c, sum_d, sum_slots = conn.execute(text(sql), params).first()
    t1 = time.perf_counter()
    print(f"预计算表取数耗时={t1 - t0:.2f}s")

    if not sum_slots:
        print("无可用预计算结果")
        return

    avg_c = Decimal(sum_c) / sum_slots
    avg_d = Decimal(sum_d) / sum_slots
    coefficients = sp.province_price_coefficients.get(province)
    charge_factor = Decimal(str(coefficients.charge)) if coefficients else Decimal(1)
    discharge_factor = Decimal(str(coefficients.discharge)) if coefficients else Decimal(1)
    avg_c = avg_c * charge_factor
    avg_d = avg_d * discharge_factor

    def kwh(v):
        return float(v / Decimal(1000))

    print(f"省份修正系数：charge={charge_factor} discharge={discharge_factor}")
    print(f"avg_charge={avg_c} 元/MWh → {kwh(avg_c)} 元/kWh")
    print(f"avg_discharge={avg_d} 元/MWh → {kwh(avg_d)} 元/kWh")


if __name__ == "__main__":
    main()

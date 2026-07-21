# Spot Benchmark 复用预计算结果 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 使 `tools/spot_benchmark.py` 仅查询已由预计算脚本写入的结果表，验证生产查表口径而不重新运行 DP。

**Architecture:** benchmark 保留文件顶部的硬编码输入，并通过 `k_from_inputs` 将容量、功率和循环次数转换为 K。脚本连接 `ir_agent`，根据是否配置节点选择预计算节点表或省级表，在指定 `[start, end)` 区间聚合每日预计算和与槽数，随后应用省份修正系数并输出均价。

**Tech Stack:** Python 3.13、SQLAlchemy Core、Decimal、项目既有配置 `get_settings()`。

## Global Constraints

- 仅修改 `tools/spot_benchmark.py`；不扩展生产 `PrecomputeSpotPriceAlgo`。
- 不连接原始省级/节点电价库，不读取逐日价格，不运行 DP。
- 工具脚本参数保持顶部“参数配置区”硬编码；不引入命令行参数。
- 使用 `[start, end)` 与 K 查询 `ir_spot_daily_optimal_province` 或 `ir_spot_daily_optimal_node`。
- 无汇总记录或汇总槽数为零时，输出“无可用预计算结果”，不除零且不回退实时计算。
- 不新增自动化测试；由使用者手动运行脚本验证。
- 不执行 `git add`、`git commit`、`git push` 或其他 git 写操作。

---

## File Structure

- Modify: `tools/spot_benchmark.py`
  - 保留硬编码参数与最终展示职责。
  - 改为连接 `ir_agent` 并聚合预计算表，消除原始电价仓储与实时 DP 依赖。

### Task 1: 将 benchmark 改为预计算表聚合路径

**Files:**
- Modify: `tools/spot_benchmark.py:9-72`

**Interfaces:**
- Consumes: `get_settings()` 返回的 `database.url`、`spot_price.province_price_coefficients`；`k_from_inputs(capacity_mwh: Decimal, rated_power_mw: Decimal, cycles: Decimal) -> int`。
- Produces: 手动 POC 输出，包含查询类型、标识、K、区间、预计算表取数耗时、修正系数以及充/放电均价。

- [ ] **Step 1: 替换实时路径的导入和初始化逻辑**

将原始数据仓储和实时 DP 导入：

```python
from app.modules.calculation.domain.spot_pricing import SpotConfig, yearly_average_prices
from app.modules.calculation.infrastructure.spot_price_repo import (
    NodeSpotRepository,
    ProvinceSpotRepository,
)
```

替换为：

```python
from sqlalchemy import create_engine, text

from app.modules.calculation.domain.spot_pricing import k_from_inputs
```

保留 `get_settings()`、`Decimal`、日期解析和 `time` 导入。这样脚本没有访问原始电价库或执行 DP 所需的任何依赖。

- [ ] **Step 2: 根据节点选择预计算表 SQL，并计算 K**

在 `node = node if node not in ("", "-") else None` 后，保留 `sp = get_settings().spot_price` 以读取系数，并新增 `k`、表名与 SQL 参数：

```python
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
```

删除创建 `NodeSpotRepository` / `ProvinceSpotRepository` 的分支。调整输入日志，使其显示 `source_label`、`identifier`、`k` 和 `[start, end)`。

- [ ] **Step 3: 查询 `ir_agent` 预计算表并处理空结果**

用同步 PyMySQL URL 创建 SQLAlchemy 引擎，执行聚合 SQL。将原先从 `repo.fetch_daily_prices()` 到 `yearly_average_prices()` 的整个区段替换为：

```python
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
```

该分支必须在使用 `sum_slots` 作为除数前返回，且不得引入对原始库或 DP 的回退调用。

- [ ] **Step 4: 保留生产一致的系数与单位展示**

在得到 `avg_c`、`avg_d` 后，沿用以下逻辑应用省份系数：

```python
    coefficients = sp.province_price_coefficients.get(province)
    charge_factor = Decimal(str(coefficients.charge)) if coefficients else Decimal(1)
    discharge_factor = Decimal(str(coefficients.discharge)) if coefficients else Decimal(1)
    avg_c = avg_c * charge_factor
    avg_d = avg_d * discharge_factor
```

保留：

```python
    def kwh(v):
        return float(v / Decimal(1000))
```

并输出：

```python
    print(f"省份修正系数：charge={charge_factor} discharge={discharge_factor}")
    print(f"avg_charge={avg_c} 元/MWh → {kwh(avg_c)} 元/kWh")
    print(f"avg_discharge={avg_d} 元/MWh → {kwh(avg_d)} 元/kWh")
```

这保持与 `PrecomputeSpotPriceAlgo.compute()` 一致的系数应用和 MWh→kWh 换算口径。

- [ ] **Step 5: 进行语法编译检查**

运行：

```bash
.venv\Scripts\python.exe -m py_compile tools\spot_benchmark.py
```

预期：命令无输出并以退出码 0 结束。

- [ ] **Step 6: 由使用者手动验证 POC 脚本**

使用配置区中的节点或省级参数手动运行：

```bash
.venv\Scripts\python.exe tools\spot_benchmark.py
```

预期：输出包含 `预计算表取数耗时=` 和 `K=`；不会输出 `DP 耗时=` 或 `取数 OK：完整日=`。有匹配预计算记录时输出两项均价；无匹配记录时输出 `无可用预计算结果`。

## Self-Review

- Spec coverage: 唯一修改文件、K 换算、节点/省级表选择、指定区间聚合、系数/单位口径、空结果处理、排除实时 DP、无自动化测试和手动验证均由 Task 1 覆盖。
- Placeholder scan: 未包含 TBD、TODO 或未定义实现步骤。
- Type consistency: 所有计算值保持 `Decimal`；SQL 传入 `date` 类型边界值，汇总结果仅在 `sum_slots` 非空时参与 `Decimal` 除法。
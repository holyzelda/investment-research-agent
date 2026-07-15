# 省级现货预计算区域规则改造 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用固定的 29 条 area/mode/province 规则完成省级现货预计算，确保蒙西和江苏使用正确的源 area 与写入省份。

**Architecture:** 在预计算基础设施中维护不可变的省级规则清单。每一规则把源库 area、源 mode 与目标 `ir_agent` province 分开；`run_precompute()` 固定遍历该清单，仓储的逐次查询使用规则 mode，写入和断点续跑使用目标 province。

**Tech Stack:** Python 3.13、SQLAlchemy Core、pytest、项目现有 `Decimal` DP 预计算模块。

## Global Constraints

- 省级预计算只处理明确列出的 29 条固定规则。
- `蒙西-全网` 从 `mode=实时` 读取并写入 `province=蒙西`；`江苏-全网` 从 `mode=日前` 读取并写入 `province=江苏`。
- 其他规则都从 `mode=日前` 读取，area 与目标 province 同名。
- 删除 `PROVINCE_AREAS` 和 `run_precompute()` 的 `province_areas` 参数。
- 删除废弃的 `spot_price.province_mode` 配置。
- 节点预计算、逐日 DP、完整日过滤、断点续跑和滚动窗口清理不改变。
- 不执行任何 git 写操作。

---

## File Structure

- Modify: `app/modules/calculation/infrastructure/spot_price_repo.py`
  - 将省级单次读取模式从构造期全局值改为 `fetch_daily_prices()` 调用参数。
- Modify: `app/modules/calculation/infrastructure/spot_precompute.py`
  - 定义固定规则清单，遍历时分离源 area、mode 和目标 province。
- Modify: `tools/spot_precompute.py`
  - 删除省级区域配置参数及向服务传参。
- Modify: `app/core/config/settings.py`
  - 删除 `SpotPriceSettings.province_mode` 与 YAML 加载映射。
- Modify: `configs/application.yml`
  - 删除 `spot_price.province_mode`。
- Modify: `tests/unit/calculation/test_spot_price_repo.py`
  - 断言省级查询按调用参数绑定 mode。
- Modify: `tests/unit/calculation/test_spot_precompute.py`
  - 更新 `run_precompute()` 调用，并验证映射目标 province 和 mode。

### Task 1: 让省级仓储按单次规则查询 mode

**Files:**
- Modify: `app/modules/calculation/infrastructure/spot_price_repo.py:51-85`
- Modify: `tests/unit/calculation/test_spot_price_repo.py`

**Interfaces:**
- Consumes: `ProvinceSpotRepository(dsn: str, table: str, market: str)`。
- Produces: `fetch_daily_prices(area: str, mode: str, start_date: date, end_date: date) -> dict[date, list[Decimal]]`。

- [ ] **Step 1: 更新省级仓储构造器和读取签名**

将构造器改为不接收或保存 mode，并让方法接收 mode：

```python
class ProvinceSpotRepository:
    def __init__(self, dsn: str, table: str, market: str):
        self._dsn, self._table = dsn, table
        self._market = market
        self._engine: Optional[Engine] = None

    def fetch_daily_prices(
        self, area: str, mode: str, start_date: date, end_date: date
    ) -> dict:
```

在 SQL 参数中将 `"mode": self._mode` 改为 `"mode": mode`。无数据异常文本增加 `mode={mode}`，方便定位具体规则。

- [ ] **Step 2: 更新仓储单元测试**

在现有 `tests/unit/calculation/test_spot_price_repo.py` 中将所有省级仓储初始化由：

```python
ProvinceSpotRepository("sqlite://", "points", "省内市场", "日前")
```

改为：

```python
ProvinceSpotRepository("sqlite://", "points", "省内市场")
```

将所有调用由：

```python
repo.fetch_daily_prices("甘肃", start, end)
```

改为：

```python
repo.fetch_daily_prices("甘肃", "日前", start, end)
```

增加一条含相同 area、不同 mode 的行，断言调用 `"实时"` 只返回实时行，以证明 mode 来自方法调用而非构造器状态。

- [ ] **Step 3: 运行仓储测试**

运行：

```bash
.venv\Scripts\python.exe -m pytest tests\unit\calculation\test_spot_price_repo.py -q
```

预期：通过，且不连接真实 MySQL。

### Task 2: 固定 29 条省级规则并将源/目标映射用于预计算

**Files:**
- Modify: `app/modules/calculation/infrastructure/spot_precompute.py:1-178`
- Modify: `tests/unit/calculation/test_spot_precompute.py`

**Interfaces:**
- Consumes: `PROVINCE_PRECOMPUTE_SPECS: tuple[tuple[str, str, str], ...]`，每项为 `(area, mode, province)`；省级仓储 `fetch_daily_prices(area, mode, start, end)`。
- Produces: `run_precompute(run_date, node_stations, node_province="蒙西", workers=10, cleanup_old=True, province_repo=None, node_repo=None, ir_engine=None) -> dict`。

- [ ] **Step 1: 定义完整固定规则清单**

在 `spot_precompute.py` 导入后定义以下常量（顺序与业务提供名单一致）：

```python
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
```

- [ ] **Step 2: 让 `_process_identifier` 透传省级 mode**

将函数定义改为：

```python
def _process_identifier(ex, ir, repo, identifier, start, end, table, scope_id, mode=None):
```

将读取逻辑改为：

```python
        daily = (
            repo.fetch_daily_prices(identifier, mode, start, end)
            if mode is not None
            else repo.fetch_daily_prices(identifier, start, end)
        )
```

节点调用不传 `mode`，保持既有节点仓储签名。

- [ ] **Step 3: 移除省级区域参数并固定遍历规则**

将 `run_precompute` 签名中的 `province_areas: list[str]` 删除。初始化省级仓储时改为：

```python
province_repo = province_repo or ProvinceSpotRepository(
    spot.province_dsn, spot.province_table, spot.province_market
)
```

删除 `province_areas == ["*"]` 的源库自动发现分支，替换为：

```python
        log(f"省级区域 {len(PROVINCE_PRECOMPUTE_SPECS)} 个")
        for area, mode, province in PROVINCE_PRECOMPUTE_SPECS:
            province_written += _process_identifier(
                executor, ir, province_repo, area, start, end,
                "ir_spot_daily_optimal_province", {"province": province}, mode=mode
            )
```

这样断点检查和写入均使用目标 province，但源库读取保持规则 area 和 mode。

- [ ] **Step 4: 更新并扩展预计算测试**

更新现有调用，移除 `province_areas=["宁夏"]`。将 `_FakeProvinceRepo.fetch_daily_prices` 定义更新为：

```python
    def fetch_daily_prices(self, area, mode, start, end):
```

使用 fake 仓储记录 `(area, mode)` 调用；运行后断言：

```python
assert len(PROVINCE_PRECOMPUTE_SPECS) == 29
assert ("蒙西-全网", "实时", "蒙西") in PROVINCE_PRECOMPUTE_SPECS
assert ("江苏-全网", "日前", "江苏") in PROVINCE_PRECOMPUTE_SPECS
assert ("蒙西-全网", "实时") in repo.calls
```

查询 SQLite 结果并断言预计算行使用 `province="蒙西"`，而不存在 `province="蒙西-全网"`。第二次运行断言该目标省份已写日期被跳过。

- [ ] **Step 5: 运行预计算测试**

运行：

```bash
.venv\Scripts\python.exe -m pytest tests\unit\calculation\test_spot_precompute.py -q
```

预期：通过；sqlite 中写入的省级记录使用映射后的目标 province。

### Task 3: 清理入口和废弃配置

**Files:**
- Modify: `tools/spot_precompute.py:15-34`
- Modify: `app/core/config/settings.py:130-145, 225-240`
- Modify: `configs/application.yml:57-70`

**Interfaces:**
- Consumes: 更新后的 `run_precompute()` 不含 `province_areas` 参数。
- Produces: 手动预计算入口固定覆盖 29 条省级规则；配置模型不再暴露 `province_mode`。

- [ ] **Step 1: 删除工具入口区域参数**

删除：

```python
PROVINCE_AREAS = ["*"]
```

并从调用中删除：

```python
province_areas=PROVINCE_AREAS,
```

保留节点、日期、worker 和清理配置。

- [ ] **Step 2: 删除全局 `province_mode` 配置模型和 YAML 项**

在 `app/core/config/settings.py` 的 `SpotPriceSettings` 删除：

```python
province_mode: str = "日前"
```

在 `get_settings()` 的 `SpotPriceSettings(...)` 构造中删除：

```python
province_mode=_nested(y, ["spot_price", "province_mode"], _sd.province_mode),
```

在 `configs/application.yml` 删除：

```yaml
  province_mode: "实时"
```

- [ ] **Step 3: 搜索确认没有旧接口引用**

运行：

```bash
rg "province_mode|province_areas|PROVINCE_AREAS" app tools tests configs
```

预期：无匹配。若测试、文档或代码仍有匹配，按新接口逐处清理后重复本命令。

### Task 4: 执行验证

**Files:**
- Verify only: `app/modules/calculation/infrastructure/spot_price_repo.py`
- Verify only: `app/modules/calculation/infrastructure/spot_precompute.py`
- Verify only: `tools/spot_precompute.py`
- Verify only: `tests/unit/calculation/test_spot_price_repo.py`
- Verify only: `tests/unit/calculation/test_spot_precompute.py`

- [ ] **Step 1: 运行受影响单元测试**

运行：

```bash
.venv\Scripts\python.exe -m pytest tests\unit\calculation\test_spot_price_repo.py tests\unit\calculation\test_spot_precompute.py -q
```

预期：通过，且不连接真实 MySQL。

- [ ] **Step 2: 运行完整测试套件**

运行：

```bash
.venv\Scripts\python.exe -m pytest
```

预期：全部通过。若存在既有无关失败，记录失败用例和完整输出，不宣称全量通过。

## Self-Review

- Spec coverage: 29 条固定规则、蒙西/江苏映射、按规则 mode 查询、移除区域参数与全局 mode、断点续跑、节点不变及测试验证均被覆盖。
- Placeholder scan: 不包含 TBD、TODO 或未定义的代码步骤。
- Type consistency: 省级仓储接收 `(area, mode, start, end)`，预计算层在省级模式下完整传递该签名；节点仓储不接收 mode。
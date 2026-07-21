# Spot benchmark 复用预计算结果设计

## 目标

将 `tools/spot_benchmark.py` 从原始电价库读取并实时运行 DP，改为直接查询 `tools/spot_precompute.py` 已写入 `ir_agent` 的预计算表。该脚本用于手动 POC 验证预计算查询路径，不新增自动化测试；由使用者手动运行脚本验证。

## 范围

仅修改 `tools/spot_benchmark.py`。

- 保留顶部硬编码参数：省份、节点、容量、功率、循环、起止日期。
- 容量、功率、循环换算为 K。
- 节点存在时查询 `ir_spot_daily_optimal_node`；节点为空或 `-` 时查询 `ir_spot_daily_optimal_province`。
- 使用指定的 `[start, end)` 和 K 聚合 `charge_sum`、`discharge_sum`、`slot_count`。
- 均价按生产口径应用省份充/放电系数，并换算显示为元/kWh。

## 排除项

- 不连接原始省级或节点电价库。
- 不读取逐日价格。
- 不调用 DP 或 `yearly_average_prices()`。
- 不扩展生产 `PrecomputeSpotPriceAlgo` 的接口。
- 不新增自动化测试；由使用者手动执行脚本验证。

## 数据流

```text
配置区输入（province/node/capacity/power/cycles/start/end）
  → k_from_inputs() 得到 K
  → ir_agent 预计算表按身份、K、日期范围 SUM
  → sum / slot_count 得到原始元/MWh均价
  → 应用省份充/放电系数
  → 输出元/MWh与元/kWh均价及查询耗时
```

## 空结果处理

查询无记录、或 `slot_count` 汇总为空/零时，脚本输出“无可用预计算结果”，不发生除零，也不回退到原始电价库或实时 DP。

## 手动验证

使用者运行脚本，观察输出中仅包含“预计算表取数”耗时及结果；可通过替换省级/节点配置和日期范围验证两条查询路径。
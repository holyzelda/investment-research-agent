# 偿债倍数图玄策化视觉设计

## 目标

在不改变偿债倍数数据契约的前提下，强化 `DebtServiceCoverage` 图表对偿债安全边界的表达。视觉参考报告中的“风险区、警戒线、点线与安全余量”信息层次，但不复制其白底、海军蓝或青绿色报告风格；所有界面与语义色均遵循当前玄策深色主题。

## 视觉构成

- 图表标题保持“现金流口径偿债能力”。
- 图表容器保持当前深色毛玻璃卡片、圆角、半透明边框与玄策间距 token。
- 业务序列使用玄策 `--xc-status-ok` 绿色；每个非空数据点显示圆点，使用绿色填充和当前深色卡片底色描边。
- 鼠标悬停时显示 crosshair 与 tooltip，内容为“第 N 年”和格式化后的“偿债倍数：x.xx 倍”。不显示首年、末年或其他常驻数值标签。
- 以 `y=1` 作为警戒线：使用 `--xc-status-danger` 红色虚线，并在绘图区右端使用同一语义色标注“警戒线 1.0”。
- `y<1` 的区域以 `--xc-status-danger-soft` 所对应的低透明红色着色，强调覆盖不足风险，但不压过网格、曲线和 tooltip。
- 折线至警戒线之间使用低透明 `--xc-status-ok` 绿色面积填充，表达安全余量；数据点中间的 `null` 继续作为折线及面积断点，不能跨缺口连接。
- 网格、轴线、坐标文字全部使用 `--xc-border-soft`、`--xc-text-mute` 等现有玄策 token；不引入报告参考样式的颜色值。

## ECharts 设计

- 业务 series：`line`，`smooth: true`，`showSymbol: true`，非空点启用 `symbol: circle` 和约 7px 点径；`connectNulls: false`。
- 系列的 `areaStyle.origin` 固定为 `1`，低透明绿色渐变/填充仅在相对警戒线的区域表达余量。
- `markLine`：`yAxis: 1`、无端点符号、红色虚线，并配置右端标签“警戒线 1.0”。
- 使用 `markArea` 对 `yAxis: 0` 至 `yAxis: 1` 区间生成低透明风险底色。
- tooltip 使用轴触发、crosshair 指针，formatter 过滤 `null` 值并显示中文年份与“倍”。

## 测试

更新 `tests/charts.spec.js`，验证：

1. 业务线仍保留 `null` 断点，且所有非空年份有 circle 数据点；
2. 业务线和面积填充使用玄策成功色 token；
3. `markArea` 覆盖 `0–1` 风险区并使用玄策危险色软色；
4. `markLine` 为 `y=1`、危险色虚线、右端标注“警戒线 1.0”；
5. tooltip 仅在悬停时返回年份和偿债倍数，不依赖任何常驻标签。

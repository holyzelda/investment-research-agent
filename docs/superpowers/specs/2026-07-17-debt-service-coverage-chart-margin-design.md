# 偿债倍数图安全余量面积设计

## 目标

红色风险区保持为完整横向背景；蓝色不再作为上半区背景，而是只填充真实偿债倍数高于 1.0 时，警戒线到主折线之间的安全余量。

## 实现

- X 轴使用 `boundaryGap: false`，首年与末年数据点/刻度贴合绘图区左右边界。
- 业务主 series 维持品牌蓝折线与圆点，采用真实值映射后的显示坐标。
- 新增一个不参与 legend、tooltip 或视觉线条的辅助面积 series：
  - `>1` 的真实值使用映射显示坐标；
  - `<=1` 的真实值钳制为警戒线显示坐标 `2`；
  - `null` 保持 `null`；
  - `areaStyle.origin = 2`，因此仅在曲线高于警戒线时绘制蓝色安全余量，不会在低于阈值处绘制蓝区。
- 红色风险区继续以 `markArea` 从显示坐标 0 覆盖至 2；移除蓝色 `markArea`。
- 警戒线继续定位显示坐标 2，tooltip 仍返回原始真实值。

## 测试

断言：X 轴 `boundaryGap=false`；主 series 保持断点；辅助 series data 对 `<=1` 为 2、`>1` 为映射值、`null` 为 null；辅助 series `areaStyle.origin=2` 且无 line/symbol；仅保留红色 `0–2` markArea。

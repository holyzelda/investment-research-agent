# 报告记录 IRR 同款发光设计

**日期：** 2026-07-27  
**状态：** 已确认

## 目标

移除报告记录定位后的上浮动画，改用与“核心投资收益指标 / 项目全投资 IRR”一致的 XC 蓝色发光效果。

## 实现

- 目标报告卡片保留现有的 `ir-report-list__item--highlighted` 状态及约 1.6 秒自动清除逻辑。
- 高亮状态使用：`border-color: var(--xc-border-accent)`、`background: var(--xc-surface-control)`，以及 `box-shadow: inset 0 1px 0 var(--xc-border-card), var(--xc-glow-blue)`。
- 删除 `ir-report-record-highlight` keyframes 与 `animation` 属性，不再移动卡片。
- 不新增依赖；所有视觉值复用 XC token。

## 测试

- 保持现有组件测试对目标卡片高亮类的验证；该类是可观察的定位结果。
- 运行侧栏回归与生产构建，保证移除动画不影响跳转定位行为。

# 玄策（XC）设计体系 — 朱雀投研智能体

本目录从 `etrader-agent-nx/agent-frontend/src/design-system/` **移植**，作为本系统的视觉基线，与统一平台观感一致。

## 已移植
- `tokens.css` — 工程引用源（`--xc-*` CSS 变量），全局引入，禁止内联 hex。

## 待按需补充（从 trader 设计体系拷贝）
- `element-plus-overrides.scss` — Element Plus → XC token 桥接（组件成规模使用时引入）
- `design-system.md` — 主规范（组件守则、页面骨架）
- `CHARTS.md` — ECharts 配色硬约束（Batch 4 图表实现时引入，红涨绿跌）

## 使用
```scss
@import '@/design-system/tokens.css';
```
根节点 `class="xc-app"` 触发深色基线；`data-theme="light"` 切浅色（报告导出用）。
组件用 `var(--xc-*)` 与 `.xc-*` 书写。

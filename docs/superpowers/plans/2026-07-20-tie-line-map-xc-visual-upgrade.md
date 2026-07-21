# 联络线地图 XC 工作台视觉升级 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变联络线地图接口、store、事件和地图业务行为的前提下，将整页升级为符合 XC 设计体系的深色投研工作台。

**Architecture:** 展示层仅重构页面容器和现有子组件，维持全部 props、emit 和 Pinia 调用关系。地图 ECharts option、筛选、详情读取、键盘导航及全屏行为不改；调整内容只包含 XC 语义类、布局结构、数据状态表达和 Lucide 图标。

**Tech Stack:** Vue 3、`<script setup>`、Pinia、Vitest、Vue Test Utils、ECharts 5、Lucide Vue、XC CSS Variables。

---

## 文件结构与职责

| 文件 | 变更职责 |
| --- | --- |
| `agent-frontend/src/views/tie-line/index.vue` | 组织标题、KPI、筛选上下文条、地图主舞台与线路档案，补齐加载、错误与筛选空态 |
| `agent-frontend/src/views/tie-line/components/TieLineStatsBar.vue` | 四项静态指标升级为紧凑 XC KPI |
| `agent-frontend/src/views/tie-line/components/TieLineFilterBar.vue` | 保持事件契约，改用 XC 表单、按钮和 Lucide 图标 |
| `agent-frontend/src/views/tie-line/components/MapToolbar.vue` | 保持五个控制事件，以 Lucide 图标和 XC glass 视觉重构 |
| `agent-frontend/src/views/tie-line/components/ChinaTieLineMap.vue` | 保持 ECharts 与全屏逻辑，收敛地图内浮层的视觉层级 |
| `agent-frontend/src/views/tie-line/components/TieLineListPanel.vue` | 保持键盘和选择逻辑，升级为密集 XC 列表 |
| `agent-frontend/src/views/tie-line/components/TieLineDetailPanel.vue` | 静态字段升级为线路档案，明确功率时序未接入状态 |
| `agent-frontend/tests/tie-line-filter-bar.spec.js` | 锁定筛选事件、XC 表单类和交换图标 |
| `agent-frontend/tests/tie-line-map-toolbar.spec.js` | 锁定五个工具事件、可访问标签和 Lucide 图标 |
| `agent-frontend/tests/tie-line-detail-panel.spec.js` | 锁定起讫路径、容量数值与功率时序数据状态 |

不修改 `src/api/tieLine.js`、`src/store/modules/tieLine.js`、路由、后端接口、地图数据以及 `tieLineMapOption`。

### Task 1: 固化视觉重构不得破坏的组件契约

**Files:**
- Modify: `agent-frontend/tests/tie-line-filter-bar.spec.js`
- Modify: `agent-frontend/tests/tie-line-map-toolbar.spec.js`
- Modify: `agent-frontend/tests/tie-line-detail-panel.spec.js`

- [ ] **Step 1: 为筛选栏补充 XC 类名与交换图标的失败断言**

在第二个测试末尾追加：

```js
expect(wrapper.find('.xc-input').exists()).toBe(true)
expect(wrapper.find('.xc-btn--icon').exists()).toBe(true)
expect(wrapper.find('svg.lucide-arrow-left-right').exists()).toBe(true)
```

- [ ] **Step 2: 运行筛选栏测试，确认断言失败**

Run: `pnpm vitest run tests/tie-line-filter-bar.spec.js`

Expected: FAIL，提示 `.xc-input`、`.xc-btn--icon` 或 Lucide 图标不存在。

- [ ] **Step 3: 为地图工具栏补充 Lucide 图标断言**

在第一个测试末尾追加：

```js
expect(wrapper.find('svg.lucide-zoom-in').exists()).toBe(true)
expect(wrapper.find('svg.lucide-list').exists()).toBe(true)
expect(wrapper.find('.xc-btn--icon').exists()).toBe(true)
```

- [ ] **Step 4: 运行工具栏测试，确认断言失败**

Run: `pnpm vitest run tests/tie-line-map-toolbar.spec.js`

Expected: FAIL，提示 Lucide SVG 或 XC icon button 不存在。

- [ ] **Step 5: 为详情档案补充路径和数据状态断言**

在“使用线路强调色 token 渲染标题”用例追加：

```js
expect(wrapper.find('.tl-detail__route').text()).toContain('甲站')
expect(wrapper.find('.tl-detail__route').text()).toContain('乙站')
expect(wrapper.find('.tl-detail__metric-value.xc-num').text()).toContain('4,000 MW')
expect(wrapper.find('.tl-detail__data-state').text()).toContain('功率时序数据未接入')
```

- [ ] **Step 6: 运行详情面板测试，确认断言失败**

Run: `pnpm vitest run tests/tie-line-detail-panel.spec.js`

Expected: FAIL，提示路径、指标类或数据状态模块不存在。

- [ ] **Step 7: 提交测试基线**

```bash
git add agent-frontend/tests/tie-line-filter-bar.spec.js agent-frontend/tests/tie-line-map-toolbar.spec.js agent-frontend/tests/tie-line-detail-panel.spec.js
git commit -m "test: cover tie line xc presentation contract"
```

本仓库规则要求由人工执行 Git 命令；此步骤只记录应提交的文件集合。

### Task 2: 升级筛选上下文条与地图工具栏

**Files:**
- Modify: `agent-frontend/src/views/tie-line/components/TieLineFilterBar.vue`
- Modify: `agent-frontend/src/views/tie-line/components/MapToolbar.vue`
- Test: `agent-frontend/tests/tie-line-filter-bar.spec.js`
- Test: `agent-frontend/tests/tie-line-map-toolbar.spec.js`

- [ ] **Step 1: 将筛选栏的手写 SVG 改为 Lucide 图标且保留事件**

在 `TieLineFilterBar.vue` 的 `<script setup>` 顶部添加：

```js
import { ArrowLeftRight, RotateCcw } from 'lucide-vue-next'
```

将交换按钮替换为：

```vue
<button
  class="xc-btn xc-btn--icon tl-filter__swap"
  type="button"
  aria-label="交换起点和终点区域"
  title="交换起终点"
  @click="$emit('swap-regions')"
>
  <ArrowLeftRight :size="16" aria-hidden="true" />
</button>
```

将重置按钮替换为：

```vue
<button class="xc-btn xc-btn--ghost tl-filter__reset" type="button" @click="$emit('reset-filters')">
  <RotateCcw :size="14" aria-hidden="true" />
  <span>重置筛选</span>
</button>
```

- [ ] **Step 2: 为输入和选择控件加入 XC 语义类**

保留现有 DOM、value 和 change 事件；将两个原生 `select` 的 class 改为 `xc-select tl-filter__select`，两个容量 `input` 改为 `xc-input tl-filter__input`。容量单位维持 `MW`，为输入容器增加 `xc-num` 类。

- [ ] **Step 3: 使用 token 重写筛选栏样式**

删除旧的 `.tl-filter__select, .tl-filter__input` 裸样式规则，使用以下结构性规则：

```scss
.tl-filter {
  display: flex;
  align-items: center;
  gap: var(--xc-space-3);
  min-height: 44px;
  padding: 0 var(--xc-space-4);
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-md);
  background: var(--xc-surface-1);
}
.tl-filter__field { display: inline-flex; align-items: center; gap: var(--xc-space-2); }
.tl-filter__label { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.tl-filter__swap { flex: 0 0 auto; }
.tl-filter__reset { margin-left: auto; }
```

保留 focus-visible，颜色改为 `var(--xc-border-accent)`，不写裸颜色或 fallback 像素值。

- [ ] **Step 4: 用 Lucide 重写地图工具栏图标**

在 `MapToolbar.vue` 中导入：

```js
import { List, LocateFixed, Maximize2, Minimize2, ZoomIn, ZoomOut } from 'lucide-vue-next'
```

按现有 `data-action` 和事件顺序替换五个内联 `<svg>`：`ZoomIn`、`ZoomOut`、`LocateFixed`、`Maximize2/Minimize2`、`List`。每个图标使用 `:size="16"` 和 `aria-hidden="true"`。

- [ ] **Step 5: 用 XC glass 视觉重写工具栏样式**

将工具栏容器保留为 inline-flex，采用：

```scss
.tl-map-tools {
  overflow: hidden;
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-md);
  background: var(--xc-surface-glass);
  box-shadow: var(--xc-shadow-glass);
  backdrop-filter: blur(var(--xc-blur-lg));
}
.tl-map-tools .xc-btn--icon {
  border-radius: 0;
  color: var(--xc-text-soft);
}
.tl-map-tools .xc-btn--icon:hover,
.tl-map-tools .xc-btn--icon.is-active {
  color: var(--xc-text-strong);
  background: var(--xc-accent-blue-soft);
}
```

- [ ] **Step 6: 运行组件测试，确认通过**

Run: `pnpm vitest run tests/tie-line-filter-bar.spec.js tests/tie-line-map-toolbar.spec.js`

Expected: PASS，筛选事件和五个地图工具事件仍全部通过。

- [ ] **Step 7: 提交筛选与工具栏重构**

```bash
git add agent-frontend/src/views/tie-line/components/TieLineFilterBar.vue agent-frontend/src/views/tie-line/components/MapToolbar.vue agent-frontend/tests/tie-line-filter-bar.spec.js agent-frontend/tests/tie-line-map-toolbar.spec.js
git commit -m "feat: refresh tie line controls with xc styles"
```

本仓库规则要求由人工执行 Git 命令；此步骤只记录应提交的文件集合。

### Task 3: 重构线路档案和静态 KPI

**Files:**
- Modify: `agent-frontend/src/views/tie-line/components/TieLineDetailPanel.vue`
- Modify: `agent-frontend/src/views/tie-line/components/TieLineStatsBar.vue`
- Test: `agent-frontend/tests/tie-line-detail-panel.spec.js`

- [ ] **Step 1: 重组详情模板为线路档案头部、路径和指标栅格**

在 `displayLine` 分支中，将现有 header 后的 `dl` 替换为：

```vue
<div class="tl-detail__route" aria-label="线路起讫路径">
  <span>{{ displayLine.startPoint || '—' }}</span>
  <span class="tl-detail__route-arrow" aria-hidden="true">→</span>
  <span>{{ displayLine.endPoint || '—' }}</span>
</div>
<dl class="tl-detail__metrics">
  <div class="tl-detail__metric"><dt>起始区域</dt><dd>{{ regionText }}</dd></div>
  <div class="tl-detail__metric"><dt>线路长度</dt><dd class="xc-num">{{ displayLine.lengthText || '—' }}</dd></div>
  <div class="tl-detail__metric"><dt>电压等级</dt><dd>{{ displayLine.voltageText || '—' }}</dd></div>
  <div class="tl-detail__metric"><dt>额定容量</dt><dd class="tl-detail__metric-value xc-num">{{ capText }}</dd></div>
  <div class="tl-detail__metric"><dt>投运年份</dt><dd class="xc-num">{{ displayLine.operationYear || '—' }}</dd></div>
</dl>
```

保留 `regionText`、`capText`、`noteText` 的现有计算逻辑。

- [ ] **Step 2: 将功率趋势占位改为数据状态模块**

替换原 `tl-detail__trend` 内容为：

```vue
<section class="tl-detail__data-state" aria-label="功率时序数据状态">
  <span class="tl-detail__data-state-label">功率趋势</span>
  <strong>功率时序数据未接入</strong>
  <p>当前仅展示线路静态资料，接入可追溯功率时序后展示趋势。</p>
</section>
```

禁止绘制假折线、假数值或伪实时状态。

- [ ] **Step 3: 将详情样式改为 XC 档案层级**

使用 `grid-template-columns: repeat(2, minmax(0, 1fr))` 布局 `.tl-detail__metrics`；每个 metric 使用 `var(--xc-surface-tinted)`、`var(--xc-border-soft)` 和 `var(--xc-radius-sm)`。头部保留电压 token 标题色，路径使用 `--xc-text-strong`，箭头使用 `--xc-accent-blue`。功率数据状态使用 `--xc-surface-frosted`、`--xc-text-mute` 和 `--xc-border-soft`，而非大色块告警背景。

- [ ] **Step 4: 将顶部统计条改为 XC KPI**

保留 `cards` 计算属性，在 `TieLineStatsBar.vue` 模板中改为：

```vue
<div class="tl-stats" aria-label="联络线统计">
  <div v-for="item in cards" :key="item.key" class="xc-kpi tl-stats__item">
    <span class="tl-stats__label">{{ item.label }}</span>
    <strong class="xc-num tl-stats__value">{{ item.value }}</strong>
  </div>
</div>
```

样式使用 token 建立四列等宽栅格，容量项允许最小宽度更大但不换行；不新增或替换静态统计字段。

- [ ] **Step 5: 运行详情测试，确认通过**

Run: `pnpm vitest run tests/tie-line-detail-panel.spec.js`

Expected: PASS，已选线路仍优先于推荐线路，容量仍为 `4,000 MW`，两种空态不变。

- [ ] **Step 6: 提交详情与 KPI 重构**

```bash
git add agent-frontend/src/views/tie-line/components/TieLineDetailPanel.vue agent-frontend/src/views/tie-line/components/TieLineStatsBar.vue agent-frontend/tests/tie-line-detail-panel.spec.js
git commit -m "feat: redesign tie line archive and kpis"
```

本仓库规则要求由人工执行 Git 命令；此步骤只记录应提交的文件集合。

### Task 4: 收敛地图浮层和线路列表

**Files:**
- Modify: `agent-frontend/src/views/tie-line/components/ChinaTieLineMap.vue`
- Modify: `agent-frontend/src/views/tie-line/components/TieLineListPanel.vue`
- Test: `agent-frontend/tests/tie-line-list-panel.spec.js`
- Test: `agent-frontend/tests/tie-line-map-option.spec.js`

- [ ] **Step 1: 保持地图逻辑，仅调整地图内浮层定位和说明样式**

不改 `buildOption`、`onChartClick`、缩放、复位、列表切换、全屏和 watcher。将地图内工具、列表、说明的定位改为 token 间距：

```scss
.china-tie-line-map__tools { position: absolute; top: var(--xc-space-4); right: var(--xc-space-4); z-index: var(--xc-z-raised); }
.china-tie-line-map__list { position: absolute; top: calc(var(--xc-space-4) + 44px); right: var(--xc-space-4); z-index: var(--xc-z-raised); }
.china-tie-line-map__note { left: var(--xc-space-4); bottom: var(--xc-space-4); }
```

若 token 中 `--xc-z-raised` 不存在，使用已有 `--xc-z-base` 与 `--xc-z-overlay` 的已定义值；不要自行引入 z-index 数字。

- [ ] **Step 2: 将地图说明升级为低干扰辅助信息条**

保留文案“箭头表示线路资料起点至终点，不代表实时潮流或功率方向”，给其增加 `aria-live="off"`。样式使用 `--xc-surface-glass`、`--xc-border-soft`、`--xc-text-mute`、`--xc-shadow-sm` 和 `backdrop-filter: blur(var(--xc-blur-sm))`。

- [ ] **Step 3: 保留列表可访问性，改为密集 XC 列表**

不改 `role="listbox"`、`role="option"`、`tabindex`、`onKeydown` 和 `select`。样式调整为：列表面板背景 `--xc-surface-glass`，边框 `--xc-border-soft`，仅该面板应用 `backdrop-filter`；行内信息沿用名称、路径、长度三层，selected 用 `--xc-accent-blue-soft`，focus 用 `--xc-border-accent` 和 `--xc-glow-blue`。

- [ ] **Step 4: 清除列表和地图样式中的 fallback 旧尺寸**

把 `10px`、`12px`、`16px` 等 fallback 形式改成对应 XC token。宽度或高度需固定时使用 `--xc-space-*` 的组合；保留必要的 `min()`、`calc()` 和百分比布局。不要改列表最大高度、地图满宽高和键盘行为。

- [ ] **Step 5: 运行地图与列表回归测试，确认通过**

Run: `pnpm vitest run tests/tie-line-list-panel.spec.js tests/tie-line-map-option.spec.js tests/tie-line-map-toolbar.spec.js`

Expected: PASS，列表键盘选择、Esc 关闭、地图 option 构造与工具栏事件全部通过。

- [ ] **Step 6: 提交地图浮层与列表重构**

```bash
git add agent-frontend/src/views/tie-line/components/ChinaTieLineMap.vue agent-frontend/src/views/tie-line/components/TieLineListPanel.vue
git commit -m "feat: refine tie line map overlays"
```

本仓库规则要求由人工执行 Git 命令；此步骤只记录应提交的文件集合。

### Task 5: 组装整页工作台与数据状态

**Files:**
- Modify: `agent-frontend/src/views/tie-line/index.vue`
- Test: `agent-frontend/tests/tie-line-store.spec.js`
- Test: `agent-frontend/tests/tie-line-detail-panel.spec.js`

- [ ] **Step 1: 保持页面数据和事件绑定，重组页面语义区域**

保持当前 `store.loadLines()`、`hasNoVisibleLines`、`detailAccentToken`、所有传参和监听事件不变。将标题区改为：

```vue
<header class="tie-line-page__header">
  <div class="tie-line-page__heading">
    <p class="tie-line-page__eyebrow">网络资产浏览</p>
    <h2 class="tie-line-page__title">跨省跨区联络线</h2>
    <p class="tie-line-page__subtitle">按起点、终点与额定容量定位全国线路资料</p>
  </div>
  <TieLineStatsBar :stats="store.stats" />
</header>
```

筛选组件仍放标题区下方，地图和详情仍只渲染一次。

- [ ] **Step 2: 增加地图加载、错误和筛选无结果的稳定容器**

在 `.tie-line-page__map-wrap` 内保留地图组件的原条件渲染，并将 loading 和 error 改为独立状态区：

```vue
<div v-if="store.loading" class="tie-line-page__state tie-line-page__state--loading" aria-live="polite">
  <span class="xc-skeleton xc-skeleton-rect tie-line-page__skeleton" aria-hidden="true" />
  <span>正在加载联络线资料</span>
</div>
<div v-else-if="store.error" class="tie-line-page__state tie-line-page__state--error" role="alert">
  <strong>数据加载失败</strong>
  <span>{{ store.error }}</span>
  <button class="xc-btn xc-btn--ghost" type="button" @click="store.loadLines">重试</button>
</div>
```

为筛选无结果时的地图区域增加覆盖提示“未找到匹配的数据”，并提供按钮触发 `store.resetFilters`。该提示不得覆盖 loading 或 error 状态。

- [ ] **Step 3: 使用 XC 三层 surface 和工作站网格重写页面样式**

页面使用 `padding: var(--xc-gutter-y) var(--xc-gutter-x)`，标题区使用 `justify-content: space-between`；主体使用 `grid-template-columns: minmax(0, 1fr) 360px`，详情固定宽度仅在页面可用空间足够时展示。地图容器保留 `min-height: 0`、`overflow: hidden` 与地图专属画布色；不把地图包装为多层卡片。

- [ ] **Step 4: 在 1920 与 1440 宽度补充防溢出规则**

加入如下媒体规则，避免标题、KPI、筛选项和详情面板文本重叠：

```scss
@media (max-width: 1440px) {
  .tie-line-page__header { align-items: flex-start; }
  .tie-line-page__body { grid-template-columns: minmax(0, 1fr) 320px; }
  .tie-line-page__heading { max-width: 420px; }
}
```

保持桌面工作站布局，不实现移动端重排。

- [ ] **Step 5: 运行 tied-line 单元测试，确认业务契约未变**

Run: `pnpm vitest run tests/tie-line-store.spec.js tests/tie-line-filter-bar.spec.js tests/tie-line-detail-panel.spec.js tests/tie-line-list-panel.spec.js tests/tie-line-map-toolbar.spec.js tests/tie-line-map-option.spec.js`

Expected: PASS，筛选、推荐线路、详情降级、列表键盘操作、地图 option 和工具栏事件全部保持通过。

- [ ] **Step 6: 提交页面工作台组装**

```bash
git add agent-frontend/src/views/tie-line/index.vue
git commit -m "feat: compose tie line xc workstation"
```

本仓库规则要求由人工执行 Git 命令；此步骤只记录应提交的文件集合。

### Task 6: XC 合规扫描、构建与人工验收

**Files:**
- Modify only if scan exposes a violation: the files changed in Tasks 2–5
- Verify: `agent-frontend/`

- [ ] **Step 1: 扫描遗留 v5 token、裸色和手写 SVG**

Run:

```bash
rg "var\(--(pri|t1|t2|t3|t4|bg|s[1-4]|red|amber|blue|slate|line|chart-[1-6])\)|#[0-9A-Fa-f]{3,8}|<svg" src/views/tie-line
```

Expected: 不输出 v5 token、裸 hex 或手写 `<svg>`。ECharts 资产和第三方渲染不属于本次扫描对象。

- [ ] **Step 2: 运行 XC P0 自检**

逐项检查 `design-system.md §9`：颜色和间距只用 `--xc-*`；所有容量、计数和年份有 `.xc-num`；不存在交易语义混用；glass 仅在地图工具、地图列表和说明中使用且不超过两层；没有 EP 黑名单组件。

- [ ] **Step 3: 运行全部前端测试**

Run: `pnpm test`

Expected: PASS，Vitest 全量用例通过。

- [ ] **Step 4: 运行生产构建**

Run: `pnpm build`

Expected: 退出码 `0`，生成 `dist/`，无 Vue 编译错误或未解析的 Lucide 导入。

- [ ] **Step 5: 启动并人工验收工作站页面**

Run: `pnpm dev`

Expected: Vite 输出本地 URL，默认 `http://localhost:5210`。

在 1920×1080 和 1440 宽度检查：标题与 KPI 不重叠；筛选、交换和重置生效；地图 hover、点击、缩放、复位、全屏与线路列表仍可用；列表方向键、Home/End、Enter/Space、Esc 可用；筛选后隐藏选中线路时详情被清空；功率模块明确显示未接入，不展示假图表。

- [ ] **Step 6: 提交最终验证修复**

```bash
git add agent-frontend/src/views/tie-line agent-frontend/tests
git commit -m "fix: complete tie line xc visual verification"
```

本仓库规则要求由人工执行 Git 命令；此步骤只记录应提交的文件集合。

## 计划自检

- 规格覆盖：Task 2 覆盖筛选与工具；Task 3 覆盖 KPI 和线路档案；Task 4 覆盖地图浮层与列表；Task 5 覆盖整页布局及五态中的首次加载、错误、筛选空态；Task 6 覆盖 XC 合规、测试、构建和人工交互验收。
- 边界检查：全部任务不涉及 API、store、路由、后端、地图 option 或数据契约；不新增功率时序、实时潮流或假数据。
- 一致性检查：筛选仍派发 `update:start-region`、`update:end-region`、`update:min-capacity-mw`、`update:max-capacity-mw`、`swap-regions`、`reset-filters`；地图工具仍派发五个现有事件；详情仍保留四个既有 props。
- 占位扫描：计划不包含待补充实现或未定义的数据字段；每个改动步骤含明确文件、命令和预期结果。

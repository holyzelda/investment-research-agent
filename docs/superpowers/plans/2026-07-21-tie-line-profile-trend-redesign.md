# 联络线线路档案与功率趋势重设计 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将右侧详情改为“线路名片 + 微型线路图 + 三列数据带 + 轻量数据口径 + 连续功率趋势”的分析侧栏。

**Architecture:** 仅重构现有 `TieLineDetailPanel.vue` 与 `TieLinePowerTrend.vue` 的模板、计算属性和局部样式；页面布局、Store、API、地图组件和后端保持不变。通过 props 将线路强调色和额定容量传给趋势组件，使微型线路图、趋势曲线、额定容量虚线颜色与地图选中线路一致。

**Tech Stack:** Vue 3 SFC、Composition API、ECharts、Vitest、@vue/test-utils、XC CSS token。

---

## 文件结构与职责

| 文件 | 变更 | 职责 |
|---|---|---|
| `agent-frontend/src/views/tie-line/components/TieLineDetailPanel.vue` | 修改 | 线路名片、微型线路图、三列数据带、数据口径展开入口、长文本不省略。 |
| `agent-frontend/src/views/tie-line/components/TieLinePowerTrend.vue` | 修改 | 接收强调色与额定容量；空态保留坐标区域、零轴、额定容量虚线，无模拟曲线。 |
| `agent-frontend/tests/tie-line-detail-panel.spec.js` | 修改 | 新结构、删除重复字段、数据带、数据口径展开和长文本规则测试。 |
| `agent-frontend/tests/tie-line-power-trend.spec.js` | 修改 | 强调色、额定容量虚线、空态无模拟曲线测试。 |

## Task 1：用测试锁定线路名片与数据带结构

**Files:**
- Modify: `agent-frontend/tests/tie-line-detail-panel.spec.js`
- Modify: `agent-frontend/src/views/tie-line/components/TieLineDetailPanel.vue`

- [ ] **Step 1: 写失败测试**

在 `tie-line-detail-panel.spec.js` 中新增或调整断言：

```js
it('以线路名片、微型线路图和三列数据带展示线路档案', () => {
  const wrapper = mountPanel({ line, accentToken: '--xc-map-voltage-4' })

  expect(wrapper.find('.tl-profile__eyebrow').text()).toBe('线路档案')
  expect(wrapper.find('.tl-profile__name').text()).toBe('甲乙线')
  expect(wrapper.find('.tl-profile__type').text()).toBe('跨区直流输电线路')
  expect(wrapper.find('.tl-profile__voltage').text()).toBe('±800 kV')
  expect(wrapper.find('.tl-mini-route').exists()).toBe(true)
  expect(wrapper.find('.tl-mini-route__station--start').text()).toContain('甲站')
  expect(wrapper.find('.tl-mini-route__station--end').text()).toContain('乙站')
  expect(wrapper.find('.tl-metric-strip').exists()).toBe(true)
  expect(wrapper.text()).toContain('额定容量')
  expect(wrapper.text()).toContain('线路长度')
  expect(wrapper.text()).toContain('投运年份')
  expect(wrapper.findAll('.tl-detail__metric')).toHaveLength(0)
  expect(wrapper.text()).not.toContain('起始区域')
  expect(wrapper.text()).not.toContain('电压等级')
})
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:$PATH"
pnpm vitest run tests/tie-line-detail-panel.spec.js
```

预期：失败，提示新 class 不存在。

- [ ] **Step 3: 重构详情面板模板与计算属性**

将 `TieLineDetailPanel.vue` 中原 header、route、metrics 替换为：

```vue
<header class="tl-profile__head">
  <div class="tl-profile__identity">
    <span class="tl-profile__eyebrow">线路档案</span>
    <h3 class="tl-profile__name" :style="{ color: `var(${accentToken})` }">{{ displayLine.name }}</h3>
    <p class="tl-profile__type">{{ lineTypeText }}</p>
  </div>
  <span class="tl-profile__voltage">{{ displayLine.voltageText || '电压未知' }}</span>
</header>

<section class="tl-mini-route" :style="{ '--tl-accent': `var(${accentToken})` }" aria-label="线路起讫路径">
  <div class="tl-mini-route__station tl-mini-route__station--start">
    <span class="tl-mini-route__dot" aria-hidden="true" />
    <strong>{{ displayLine.startPoint || '—' }}</strong>
    <small>{{ displayLine.startRegion || '—' }}</small>
  </div>
  <div class="tl-mini-route__link" aria-hidden="true"><span /></div>
  <div class="tl-mini-route__station tl-mini-route__station--end">
    <span class="tl-mini-route__dot" aria-hidden="true" />
    <strong>{{ displayLine.endPoint || '—' }}</strong>
    <small>{{ displayLine.endRegion || '—' }}</small>
  </div>
</section>

<dl class="tl-metric-strip" aria-label="线路关键指标">
  <div class="tl-metric-strip__item"><dt>额定容量</dt><dd class="xc-num">{{ capText }}</dd></div>
  <div class="tl-metric-strip__item"><dt>线路长度</dt><dd class="xc-num">{{ displayLine.lengthText || '—' }}</dd></div>
  <div class="tl-metric-strip__item"><dt>投运年份</dt><dd class="xc-num">{{ displayLine.operationYear || '—' }}</dd></div>
</dl>
```

在 `<script setup>` 中添加：

```js
const lineTypeText = computed(() => {
  const voltage = displayLine.value?.voltageText || ''
  const name = displayLine.value?.name || ''
  return voltage.includes('±') || name.includes('直流') ? '跨区直流输电线路' : '跨区交流输电线路'
})
```

- [ ] **Step 4: 运行测试确认通过或进入下一个失败**

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:$PATH"
pnpm vitest run tests/tie-line-detail-panel.spec.js
```

## Task 2：实现数据口径轻量入口与长文本规则

**Files:**
- Modify: `agent-frontend/tests/tie-line-detail-panel.spec.js`
- Modify: `agent-frontend/src/views/tie-line/components/TieLineDetailPanel.vue`

- [ ] **Step 1: 写失败测试**

```js
it('数据口径默认显示摘要，点击后展开完整说明', async () => {
  const wrapper = mountPanel({
    line: {
      ...line,
      coordinateBasis: '换流站经纬度',
      dataBasisNote: '额定容量来自公开资料',
      sourceNote: '公开资料整理，含长期长文本说明',
    },
  })

  expect(wrapper.find('.tl-data-basis__summary').text()).toContain('换流站经纬度')
  expect(wrapper.text()).not.toContain('公开资料整理，含长期长文本说明')
  await wrapper.find('.tl-data-basis__toggle').trigger('click')
  expect(wrapper.text()).toContain('坐标基准：换流站经纬度')
  expect(wrapper.text()).toContain('数据说明：额定容量来自公开资料')
  expect(wrapper.text()).toContain('来源备注：公开资料整理，含长期长文本说明')
})

it('关键长文本区域不使用省略号截断', () => {
  const styles = tieLineDetailPanelSource.match(/<style scoped>([\s\S]*)<\/style>/)?.[1] || ''

  expect(styles).not.toContain('text-overflow: ellipsis')
  expect(styles).not.toContain('white-space: nowrap')
})
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:$PATH"
pnpm vitest run tests/tie-line-detail-panel.spec.js
```

- [ ] **Step 3: 实现数据口径入口**

在模板数据带后加入：

```vue
<section v-if="basisSummary" class="tl-data-basis">
  <button class="tl-data-basis__toggle" type="button" @click="basisOpen = !basisOpen">
    <span>数据口径</span>
    <strong class="tl-data-basis__summary">{{ basisSummary }}</strong>
    <em>{{ basisOpen ? '收起' : '展开' }}</em>
  </button>
  <div v-if="basisOpen" class="tl-data-basis__body">
    <p v-if="displayLine.coordinateBasis">坐标基准：{{ displayLine.coordinateBasis }}</p>
    <p v-if="displayLine.dataBasisNote">数据说明：{{ displayLine.dataBasisNote }}</p>
    <p v-if="displayLine.sourceNote">来源备注：{{ displayLine.sourceNote }}</p>
  </div>
</section>
```

在 `<script setup>` 中引入 `ref` 并添加：

```js
const basisOpen = ref(false)
const basisSummary = computed(() => {
  if (!displayLine.value) return ''
  return [displayLine.value.coordinateBasis, displayLine.value.dataBasisNote].filter(Boolean).join(' · ')
})
```

- [ ] **Step 4: 运行详情面板测试**

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:$PATH"
pnpm vitest run tests/tie-line-detail-panel.spec.js
```

## Task 3：实现连续侧栏视觉、微型线路图和数据带 CSS

**Files:**
- Modify: `agent-frontend/src/views/tie-line/components/TieLineDetailPanel.vue`
- Test: `agent-frontend/tests/tie-line-detail-panel.spec.js`

- [ ] **Step 1: 替换详情面板 CSS**

保留 `.tl-detail` 容器，删除旧 `.tl-detail__*` 指标样式，加入：

```css
.tl-profile__head { display:flex; align-items:flex-start; justify-content:space-between; gap:var(--xc-space-3); }
.tl-profile__identity { min-width:0; }
.tl-profile__eyebrow { display:block; color:var(--xc-text-mute); font-size:12px; }
.tl-profile__name { margin:var(--xc-space-1) 0 0; font-size:var(--xc-fs-h3); font-weight:var(--xc-fw-semi); line-height:var(--xc-lh-snug); overflow-wrap:anywhere; }
.tl-profile__type { margin:var(--xc-space-1) 0 0; color:var(--xc-text-soft); font-size:var(--xc-fs-xs); line-height:var(--xc-lh-normal); }
.tl-profile__voltage { flex:0 0 auto; padding:var(--xc-space-1) var(--xc-space-2); color:var(--xc-text-soft); border:1px solid var(--xc-border-soft); border-radius:var(--xc-radius-xs); font-size:var(--xc-fs-2xs); }
.tl-mini-route { display:grid; grid-template-columns:minmax(0, 1fr) 52px minmax(0, 1fr); align-items:start; gap:var(--xc-space-2); margin-top:var(--xc-space-5); }
.tl-mini-route__station { min-width:0; display:grid; grid-template-columns:auto minmax(0, 1fr); column-gap:var(--xc-space-2); row-gap:var(--xc-space-1); color:var(--xc-text-strong); }
.tl-mini-route__station strong { overflow-wrap:anywhere; line-height:var(--xc-lh-snug); }
.tl-mini-route__station small { grid-column:2; color:var(--xc-text-mute); font-size:12px; line-height:var(--xc-lh-normal); overflow-wrap:anywhere; }
.tl-mini-route__dot { width:9px; height:9px; margin-top:0.35em; border-radius:999px; background:var(--tl-accent); box-shadow:0 0 0 3px var(--xc-surface-1); }
.tl-mini-route__link { position:relative; height:24px; margin-top:0.15em; }
.tl-mini-route__link::before { content:''; position:absolute; left:0; right:8px; top:8px; border-top:1px solid var(--tl-accent); }
.tl-mini-route__link::after { content:'▶'; position:absolute; right:0; top:1px; color:var(--tl-accent); font-size:10px; }
.tl-metric-strip { display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:0; margin:var(--xc-space-5) 0 0; }
.tl-metric-strip__item { min-width:0; padding:0 var(--xc-space-3); position:relative; }
.tl-metric-strip__item:first-child { padding-left:0; }
.tl-metric-strip__item + .tl-metric-strip__item::before { content:''; position:absolute; left:0; top:8px; height:28px; border-left:1px solid var(--xc-border-soft); }
.tl-metric-strip dt { color:var(--xc-text-mute); font-size:12px; }
.tl-metric-strip dd { margin:var(--xc-space-1) 0 0; color:var(--xc-text-strong); font-size:18px; font-weight:600; line-height:var(--xc-lh-snug); overflow-wrap:anywhere; }
.tl-data-basis { margin-top:var(--xc-space-4); }
.tl-data-basis__toggle { width:100%; display:grid; grid-template-columns:auto minmax(0, 1fr) auto; gap:var(--xc-space-2); align-items:start; padding:0; color:var(--xc-text-mute); background:transparent; border:0; text-align:left; cursor:pointer; font-size:12px; }
.tl-data-basis__summary { color:var(--xc-text-soft); font-weight:var(--xc-fw-regular); overflow-wrap:anywhere; }
.tl-data-basis__toggle em { color:var(--xc-accent-blue); font-style:normal; }
.tl-data-basis__body { display:grid; gap:var(--xc-space-1); margin-top:var(--xc-space-2); color:var(--xc-text-mute); font-size:12px; line-height:var(--xc-lh-normal); }
.tl-data-basis__body p { margin:0; overflow-wrap:anywhere; }
@media (max-width: 1180px) {
  .tl-detail { height:auto; }
  .tl-mini-route { grid-template-columns:1fr; }
  .tl-mini-route__link { width:24px; height:38px; margin-left:4px; }
  .tl-mini-route__link::before { left:4px; right:auto; top:0; bottom:8px; border-top:0; border-left:1px solid var(--tl-accent); }
  .tl-mini-route__link::after { left:0; right:auto; top:auto; bottom:0; content:'▼'; }
  .tl-metric-strip { grid-template-columns:1fr; gap:var(--xc-space-3); }
  .tl-metric-strip__item { padding:0; }
  .tl-metric-strip__item + .tl-metric-strip__item::before { display:none; }
}
```

- [ ] **Step 2: 运行详情测试**

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:$PATH"
pnpm vitest run tests/tie-line-detail-panel.spec.js
```

## Task 4：功率趋势接收强调色与额定容量，并重做无数据图表空态

**Files:**
- Modify: `agent-frontend/tests/tie-line-power-trend.spec.js`
- Modify: `agent-frontend/src/views/tie-line/components/TieLinePowerTrend.vue`
- Modify: `agent-frontend/src/views/tie-line/components/TieLineDetailPanel.vue`

- [ ] **Step 1: 写失败测试**

在 `tie-line-power-trend.spec.js` 新增：

```js
it('无真实数据时保留坐标区域、零轴和额定容量虚线，不绘制模拟曲线', () => {
  mount(TieLinePowerTrend, {
    props: {
      accentToken: '--xc-map-voltage-4',
      ratedCapacityMw: 4000,
      trend: { startDate: '2026-07-20', endDate: '2026-07-20', dataDateCount: 0, points: points.map((point) => ({ ...point, powerMw: null })) },
      range: { key: 'yesterday', startDate: '2026-07-20', endDate: '2026-07-20' },
    },
    global: { stubs: { ElDialog: true, ElDatePicker: true } },
  })

  const option = chart.optionFactory()
  expect(option.series[0].data.every((value) => value === null)).toBe(true)
  expect(option.series[0].lineStyle.color).toBe('--xc-map-voltage-4')
  expect(option.series[0].markLine.data).toEqual(expect.arrayContaining([{ yAxis: 0 }, { yAxis: 4000 }]))
  expect(option.graphic[0].style.text).toContain('暂无实时功率数据')
})
```

- [ ] **Step 2: 运行趋势测试确认失败**

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:$PATH"
pnpm vitest run tests/tie-line-power-trend.spec.js
```

- [ ] **Step 3: 修改趋势组件 props 与 option**

在 `TieLinePowerTrend.vue` props 增加：

```js
accentToken: { type: String, default: '--xc-chart-1' },
ratedCapacityMw: { type: Number, default: null },
```

在 `buildOption()` 中：

```js
const accent = xcVar(props.accentToken) || xcVar('--xc-chart-1')
const values = points.map((point) => point.powerMw)
const hasValues = values.some((value) => value !== null && value !== undefined)
```

series 使用：

```js
data: values,
lineStyle: { width: 2, color: accent },
itemStyle: { color: accent },
markLine: {
  symbol: 'none',
  silent: true,
  lineStyle: { color: xcVar('--xc-border-soft'), type: 'dashed', width: 1 },
  label: { color: xcVar('--xc-text-mute'), fontSize: 10 },
  data: [
    { yAxis: 0 },
    ...(props.ratedCapacityMw != null ? [{ yAxis: props.ratedCapacityMw, name: '额定容量' }] : []),
  ],
},
```

option 增加：

```js
graphic: !hasValues ? [{
  type: 'text', left: 'center', top: 'middle',
  style: { text: '暂无实时功率数据\n数据源尚未接入', fill: xcVar('--xc-text-mute'), fontSize: 12, lineHeight: 20, align: 'center' },
}] : [],
```

- [ ] **Step 4: 从详情面板传入颜色和额定容量**

`TieLineDetailPanel.vue` 的 `TieLinePowerTrend` 增加：

```vue
:accent-token="accentToken"
:rated-capacity-mw="displayLine.ratedCapacityMw"
```

- [ ] **Step 5: 运行趋势测试**

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:$PATH"
pnpm vitest run tests/tie-line-power-trend.spec.js
```

## Task 5：最终验证与实际页面检查

**Files:**
- No source changes expected.

- [ ] **Step 1: 运行定向测试**

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:$PATH"
pnpm vitest run tests/tie-line-detail-panel.spec.js tests/tie-line-power-trend.spec.js
```

- [ ] **Step 2: 运行构建**

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:$PATH"
pnpm build
```

- [ ] **Step 3: 启动页面检查实际效果**

```bash
cd agent-frontend
export PATH="/e/openclaw/nodejs:$PATH"
pnpm dev -- --host 127.0.0.1
```

打开 Vite 输出的 `/tie-line` 页面，检查：线路名片完整换行、微型线路图横/纵布局、数据带三列、数据口径可展开、功率趋势和地图选中线同色。

## 覆盖自检

- 线路名片：Task 1。
- 微型线路图与长文本完整：Task 1、Task 3。
- 删除重复字段：Task 1。
- 三列数据带、无外框卡片：Task 1、Task 3。
- 数据口径展开：Task 2。
- 连续侧栏细分隔线：Task 3、Task 4 保持趋势作为子模块。
- 无真实数据不画模拟曲线、保留坐标和容量虚线：Task 4。
- 地图、微型图、趋势同色：Task 4。

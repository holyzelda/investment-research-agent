# 联络线筛选工具栏 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将联络线地图顶部筛选区重构为轻量连续分析工具栏，并保留既有筛选、交换、重置和地图刷新业务行为。

**Architecture:** 以 `TieLineFilterBar.vue` 为展示层重构中心，继续使用原有受控 props 与 emit 事件；父页面只补充 `visibleCount`/`totalCount` 两个展示用 props，不迁移筛选计算。容量范围使用 Element Plus Popover 承载临时输入，点击确定或清除后仍通过原容量更新事件通知现有 store。

**Tech Stack:** Vue 3 `<script setup>`、Pinia、Element Plus `ElPopover`、lucide-vue 图标、Vitest、@vue/test-utils、XC CSS tokens。

---

## 文件结构

- Modify: `agent-frontend/src/views/tie-line/components/TieLineFilterBar.vue`
  - 职责：筛选工具栏 UI、容量 Popover 临时输入、筛选结果文案、交换/重置图标交互。
  - 不能改动外部业务状态的含义；只通过既有事件派发变化。
- Modify: `agent-frontend/src/views/tie-line/index.vue`
  - 职责：向筛选栏传入 `visibleCount` 与 `totalCount`，保持筛选计算仍来自 store。
- Modify: `agent-frontend/tests/tie-line-filter-bar.spec.js`
  - 职责：验证筛选栏事件、容量 Popover、重置启用状态、结果文案和关键视觉 class。
- Optional Modify: `my_projects/联络线地图模块-功能与开发文档.md`
  - 职责：若实现完成后筛选栏结构与文档 4.3 中描述明显不一致，补充“容量 Popover + 结果反馈”的实现事实。

---

### Task 1: 补齐筛选栏行为测试

**Files:**
- Modify: `agent-frontend/tests/tie-line-filter-bar.spec.js`

- [ ] **Step 1: 替换测试文件为新的行为覆盖**

将 `agent-frontend/tests/tie-line-filter-bar.spec.js` 内容替换为：

```js
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import TieLineFilterBar from '@/views/tie-line/components/TieLineFilterBar.vue'

function mountBar(props = {}) {
  return mount(TieLineFilterBar, {
    props: {
      startRegion: '',
      endRegion: '',
      minCapacityMw: null,
      maxCapacityMw: null,
      regionOptions: ['西北', '华南', '华东'],
      visibleCount: 41,
      totalCount: 41,
      ...props,
    },
    global: {
      stubs: {
        ElPopover: {
          template: '<div><slot name="reference" /><div class="el-popover-stub"><slot /></div></div>',
        },
      },
    },
  })
}

describe('联络线筛选栏', () => {
  it('区域 select 使用紧凑控件并派发受控更新事件', async () => {
    const wrapper = mountBar()
    const selects = wrapper.findAll('select')

    expect(selects).toHaveLength(2)
    expect(selects[0].find('option').text()).toBe('全部地区')
    expect(wrapper.findAll('.tl-filter-control')[0].classes()).toContain('tl-filter-control--select')

    await selects[0].setValue('西北')
    await selects[1].setValue('华南')

    expect(wrapper.emitted('update:start-region')).toEqual([['西北']])
    expect(wrapper.emitted('update:end-region')).toEqual([['华南']])
  })

  it('交换按钮只显示图标并派发交换事件', async () => {
    const wrapper = mountBar({ startRegion: '西北', endRegion: '华南' })
    const swap = wrapper.find('.tl-filterbar__swap')

    expect(swap.attributes('aria-label')).toBe('交换起点和终点区域')
    expect(swap.attributes('title')).toBe('交换起点与终点')
    expect(swap.text()).toBe('')
    expect(wrapper.find('svg.lucide-arrow-left-right').exists()).toBe(true)

    await swap.trigger('click')

    expect(wrapper.emitted('swap-regions')).toHaveLength(1)
    expect(swap.classes()).toContain('is-spinning')
  })

  it('容量触发器展示不同范围文案', () => {
    expect(mountBar().find('.tl-filter-control--capacity .tl-filter-control__value').text()).toBe('不限')
    expect(mountBar({ minCapacityMw: 2000, maxCapacityMw: 5000 }).find('.tl-filter-control--capacity .tl-filter-control__value').text()).toBe('2,000-5,000 MW')
    expect(mountBar({ minCapacityMw: null, maxCapacityMw: 2000 }).find('.tl-filter-control--capacity .tl-filter-control__value').text()).toBe('≤ 2,000 MW')
    expect(mountBar({ minCapacityMw: 5000, maxCapacityMw: null }).find('.tl-filter-control--capacity .tl-filter-control__value').text()).toBe('≥ 5,000 MW')
  })

  it('容量 Popover 确定和清除仍派发原容量更新事件', async () => {
    const wrapper = mountBar()
    const inputs = wrapper.findAll('.tl-capacity-popover__input')

    expect(inputs).toHaveLength(2)
    expect(inputs[0].attributes('type')).toBe('number')
    expect(inputs[0].attributes('min')).toBe('0')
    expect(inputs[0].attributes('step')).toBe('1')

    await inputs[0].setValue('2000')
    await inputs[1].setValue('5000')
    await wrapper.find('[data-test="capacity-apply"]').trigger('click')

    expect(wrapper.emitted('update:min-capacity-mw')).toEqual([['2000']])
    expect(wrapper.emitted('update:max-capacity-mw')).toEqual([['5000']])

    await wrapper.find('[data-test="capacity-clear"]').trigger('click')

    expect(wrapper.emitted('update:min-capacity-mw')).toEqual([['2000'], ['']])
    expect(wrapper.emitted('update:max-capacity-mw')).toEqual([['5000'], ['']])
  })

  it('常用容量范围只更新 Popover 临时输入，确定后应用', async () => {
    const wrapper = mountBar()

    await wrapper.find('[data-test="capacity-preset-mid"]').trigger('click')

    const inputs = wrapper.findAll('.tl-capacity-popover__input')
    expect(inputs[0].element.value).toBe('2000')
    expect(inputs[1].element.value).toBe('5000')
    expect(wrapper.emitted('update:min-capacity-mw')).toBeUndefined()

    await wrapper.find('[data-test="capacity-apply"]').trigger('click')

    expect(wrapper.emitted('update:min-capacity-mw')).toEqual([['2000']])
    expect(wrapper.emitted('update:max-capacity-mw')).toEqual([['5000']])
  })

  it('结果文案按筛选状态展示，重置按钮仅在有筛选时启用', async () => {
    const idle = mountBar({ visibleCount: 41, totalCount: 41 })
    expect(idle.find('.tl-filterbar__result').text()).toBe('显示 41 条线路')
    expect(idle.find('.tl-filterbar__reset').attributes('disabled')).toBeDefined()

    const filtered = mountBar({ startRegion: '西北', visibleCount: 8, totalCount: 41 })
    expect(filtered.find('.tl-filterbar__result').text()).toBe('显示 8 / 41 条线路')
    expect(filtered.find('.tl-filterbar__reset').attributes('disabled')).toBeUndefined()

    await filtered.find('.tl-filterbar__reset').trigger('click')
    expect(filtered.emitted('reset-filters')).toHaveLength(1)

    const empty = mountBar({ startRegion: '西北', visibleCount: 0, totalCount: 41 })
    expect(empty.find('.tl-filterbar__result').text()).toBe('未找到符合条件的线路')
  })
})
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
cd agent-frontend && pnpm vitest run tests/tie-line-filter-bar.spec.js
```

Expected: FAIL。失败点应包含缺少 `.tl-filterbar__swap`、`.tl-filter-control--capacity`、`visibleCount` 文案或容量 Popover 相关选择器。

---

### Task 2: 重构 `TieLineFilterBar.vue` 模板与脚本

**Files:**
- Modify: `agent-frontend/src/views/tie-line/components/TieLineFilterBar.vue`

- [ ] **Step 1: 替换组件模板和脚本**

将 `agent-frontend/src/views/tie-line/components/TieLineFilterBar.vue` 的 `<template>` 与 `<script setup>` 替换为下面内容，暂时保留 `<style scoped>` 等 Task 3 替换：

```vue
<template>
  <div class="tl-filterbar" aria-label="联络线筛选工具栏">
    <div class="tl-filterbar__primary">
      <label class="tl-filter-control tl-filter-control--select" :class="{ 'is-active': Boolean(startRegion) }">
        <span class="tl-filter-control__label">起点</span>
        <select class="tl-filter-control__select" :value="startRegion" @change="$emit('update:start-region', $event.target.value)">
          <option value="">全部地区</option>
          <option v-for="r in regionOptions" :key="r" :value="r">{{ r }}</option>
        </select>
        <ChevronDown :size="14" class="tl-filter-control__chevron" aria-hidden="true" />
      </label>

      <button
        class="tl-filterbar__swap"
        :class="{ 'is-spinning': swapAnimating }"
        type="button"
        aria-label="交换起点和终点区域"
        title="交换起点与终点"
        @click="handleSwap"
      >
        <ArrowLeftRight :size="16" aria-hidden="true" />
      </button>

      <label class="tl-filter-control tl-filter-control--select" :class="{ 'is-active': Boolean(endRegion) }">
        <span class="tl-filter-control__label">终点</span>
        <select class="tl-filter-control__select" :value="endRegion" @change="$emit('update:end-region', $event.target.value)">
          <option value="">全部地区</option>
          <option v-for="r in regionOptions" :key="r" :value="r">{{ r }}</option>
        </select>
        <ChevronDown :size="14" class="tl-filter-control__chevron" aria-hidden="true" />
      </label>

      <ElPopover
        v-model:visible="capacityOpen"
        placement="bottom-start"
        trigger="click"
        :width="292"
        popper-class="tl-capacity-popper"
        @show="syncCapacityDraft"
      >
        <template #reference>
          <button
            class="tl-filter-control tl-filter-control--capacity"
            :class="{ 'is-active': hasCapacityFilter }"
            type="button"
            aria-label="筛选额定容量范围"
          >
            <span class="tl-filter-control__label">额定容量</span>
            <span class="tl-filter-control__value xc-num">{{ capacitySummary }}</span>
            <ChevronDown :size="14" class="tl-filter-control__chevron" aria-hidden="true" />
          </button>
        </template>

        <div class="tl-capacity-popover">
          <p class="tl-capacity-popover__title">额定容量范围（MW）</p>
          <div class="tl-capacity-popover__range xc-num">
            <input
              v-model="draftMinCapacity"
              class="tl-capacity-popover__input"
              type="number"
              min="0"
              step="1"
              inputmode="numeric"
              aria-label="额定容量下限（MW）"
              placeholder="最低容量"
            />
            <span class="tl-capacity-popover__dash">—</span>
            <input
              v-model="draftMaxCapacity"
              class="tl-capacity-popover__input"
              type="number"
              min="0"
              step="1"
              inputmode="numeric"
              aria-label="额定容量上限（MW）"
              placeholder="最高容量"
            />
          </div>

          <div class="tl-capacity-popover__presets" aria-label="常用容量范围">
            <span class="tl-capacity-popover__subtitle">常用范围</span>
            <div class="tl-capacity-popover__preset-row">
              <button class="tl-capacity-popover__preset" type="button" data-test="capacity-preset-low" @click="setCapacityDraft('', '2000')">≤ 2,000</button>
              <button class="tl-capacity-popover__preset" type="button" data-test="capacity-preset-mid" @click="setCapacityDraft('2000', '5000')">2,000-5,000</button>
              <button class="tl-capacity-popover__preset" type="button" data-test="capacity-preset-high" @click="setCapacityDraft('5000', '')">≥ 5,000</button>
            </div>
          </div>

          <div class="tl-capacity-popover__actions">
            <button class="tl-capacity-popover__btn tl-capacity-popover__btn--ghost" type="button" data-test="capacity-clear" @click="clearCapacity">清除</button>
            <button class="tl-capacity-popover__btn tl-capacity-popover__btn--primary" type="button" data-test="capacity-apply" @click="applyCapacity">确定</button>
          </div>
        </div>
      </ElPopover>
    </div>

    <div class="tl-filterbar__actions">
      <span class="tl-filterbar__result" aria-live="polite">{{ resultText }}</span>
      <button
        class="tl-filterbar__reset"
        type="button"
        :disabled="!hasActiveFilters"
        aria-label="重置筛选"
        title="重置筛选"
        @click="$emit('reset-filters')"
      >
        <RotateCcw :size="15" aria-hidden="true" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ArrowLeftRight, ChevronDown, RotateCcw } from '@lucide/vue'

const props = defineProps({
  startRegion: { type: String, default: '' },
  endRegion: { type: String, default: '' },
  minCapacityMw: { type: Number, default: null },
  maxCapacityMw: { type: Number, default: null },
  regionOptions: { type: Array, default: () => [] },
  visibleCount: { type: Number, default: 0 },
  totalCount: { type: Number, default: 0 },
})

const emit = defineEmits(['update:start-region', 'update:end-region', 'update:min-capacity-mw', 'update:max-capacity-mw', 'swap-regions', 'reset-filters'])

const capacityOpen = ref(false)
const draftMinCapacity = ref('')
const draftMaxCapacity = ref('')
const swapAnimating = ref(false)
let swapTimer = null

const hasCapacityFilter = computed(() => props.minCapacityMw !== null || props.maxCapacityMw !== null)
const hasActiveFilters = computed(() => Boolean(props.startRegion || props.endRegion || hasCapacityFilter.value))

const capacitySummary = computed(() => {
  const min = props.minCapacityMw
  const max = props.maxCapacityMw
  if (min === null && max === null) return '不限'
  if (min !== null && max !== null) return `${formatCapacity(min)}-${formatCapacity(max)} MW`
  if (max !== null) return `≤ ${formatCapacity(max)} MW`
  return `≥ ${formatCapacity(min)} MW`
})

const resultText = computed(() => {
  const total = props.totalCount
  const visible = props.visibleCount
  if (total > 0 && visible === 0) return '未找到符合条件的线路'
  if (hasActiveFilters.value) return `显示 ${visible} / ${total} 条线路`
  return `显示 ${total} 条线路`
})

watch(
  () => [props.minCapacityMw, props.maxCapacityMw],
  () => {
    if (!capacityOpen.value) syncCapacityDraft()
  },
)

function formatCapacity(value) {
  return Number(value).toLocaleString('zh-CN')
}

function syncCapacityDraft() {
  draftMinCapacity.value = props.minCapacityMw ?? ''
  draftMaxCapacity.value = props.maxCapacityMw ?? ''
}

function setCapacityDraft(min, max) {
  draftMinCapacity.value = min
  draftMaxCapacity.value = max
}

function applyCapacity() {
  emit('update:min-capacity-mw', draftMinCapacity.value)
  emit('update:max-capacity-mw', draftMaxCapacity.value)
  capacityOpen.value = false
}

function clearCapacity() {
  setCapacityDraft('', '')
  emit('update:min-capacity-mw', '')
  emit('update:max-capacity-mw', '')
  capacityOpen.value = false
}

function handleSwap() {
  emit('swap-regions')
  swapAnimating.value = false
  window.clearTimeout(swapTimer)
  requestAnimationFrame(() => {
    swapAnimating.value = true
    swapTimer = window.setTimeout(() => {
      swapAnimating.value = false
    }, 220)
  })
}
</script>
```

- [ ] **Step 2: 运行筛选栏测试确认样式尚未完成但行为接近**

Run:

```bash
cd agent-frontend && pnpm vitest run tests/tie-line-filter-bar.spec.js
```

Expected: 可能仍 FAIL，主要因为旧样式 class 未替换或 Element Plus Popover stub 差异；若出现 `window is not defined`，说明测试环境不是 jsdom，需要检查 `vite.config.js` 的 test environment，而不要在组件里引入额外兼容分支。

---

### Task 3: 替换筛选栏样式

**Files:**
- Modify: `agent-frontend/src/views/tie-line/components/TieLineFilterBar.vue`

- [ ] **Step 1: 替换 `<style scoped>`**

将同一文件的 `<style scoped>` 替换为：

```vue
<style scoped>
.tl-filterbar {
  --tl-filter-border: rgba(15, 23, 42, 0.12);
  --tl-filter-border-hover: rgba(15, 23, 42, 0.2);
  --tl-filter-bg: rgba(255, 255, 255, 0.88);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 44px;
  padding: 8px 0;
  box-sizing: border-box;
}

.tl-filterbar__primary {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  min-width: 0;
}

.tl-filterbar__actions {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  min-width: max-content;
  margin-left: auto;
}

.tl-filter-control {
  position: relative;
  display: inline-flex;
  align-items: center;
  height: 36px;
  min-width: 172px;
  padding: 0 10px;
  gap: 8px;
  border: 1px solid var(--tl-filter-border);
  border-radius: 6px;
  background: var(--tl-filter-bg);
  color: var(--xc-text-strong);
  box-sizing: border-box;
  transition: border-color 160ms ease, box-shadow 160ms ease, background-color 160ms ease;
}

.tl-filter-control:hover {
  border-color: var(--tl-filter-border-hover);
  background: rgba(255, 255, 255, 0.94);
}

.tl-filter-control.is-active {
  border-color: var(--xc-border-accent);
}

.tl-filter-control:focus-within,
.tl-filter-control:focus-visible {
  border-color: var(--xc-border-accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--xc-border-accent) 24%, transparent);
}

.tl-filter-control__label {
  flex: 0 0 auto;
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-2xs);
  line-height: 1;
  white-space: nowrap;
}

.tl-filter-control__select {
  min-width: 0;
  flex: 1 1 auto;
  width: 100%;
  height: 100%;
  padding: 0 18px 0 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--xc-text-strong);
  font: inherit;
  font-size: var(--xc-fs-xs);
  font-weight: var(--xc-fw-medium);
  appearance: none;
  cursor: pointer;
}

.tl-filter-control__chevron {
  position: absolute;
  right: 9px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--xc-text-mute);
  pointer-events: none;
}

.tl-filter-control--capacity {
  min-width: 190px;
  border-color: var(--tl-filter-border);
  cursor: pointer;
}

.tl-filter-control__value {
  min-width: 0;
  flex: 1 1 auto;
  padding-right: 16px;
  color: var(--xc-text-strong);
  font-size: var(--xc-fs-xs);
  font-weight: var(--xc-fw-medium);
  text-align: left;
  white-space: nowrap;
}

.tl-filterbar__swap,
.tl-filterbar__reset {
  width: 32px;
  height: 32px;
  display: inline-grid;
  place-items: center;
  flex: 0 0 auto;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--xc-text-mute);
  padding: 0;
  box-sizing: border-box;
  cursor: pointer;
  transition: background-color 160ms ease, color 160ms ease, opacity 160ms ease, transform 200ms ease;
}

.tl-filterbar__swap:hover,
.tl-filterbar__reset:not(:disabled):hover {
  background: rgba(15, 23, 42, 0.06);
  color: var(--xc-text-strong);
}

.tl-filterbar__swap:focus-visible,
.tl-filterbar__reset:focus-visible {
  outline: 2px solid var(--xc-border-accent);
  outline-offset: 2px;
}

.tl-filterbar__swap.is-spinning svg {
  animation: tl-swap-spin 210ms ease;
}

.tl-filterbar__reset:not(:disabled) {
  color: var(--xc-text-secondary);
}

.tl-filterbar__reset:disabled {
  opacity: 0.35;
  cursor: default;
}

.tl-filterbar__result {
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-2xs);
  line-height: 1;
  white-space: nowrap;
}

.tl-capacity-popover {
  display: grid;
  gap: 12px;
  color: var(--xc-text-strong);
}

.tl-capacity-popover__title,
.tl-capacity-popover__subtitle {
  margin: 0;
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-2xs);
  line-height: var(--xc-lh-normal);
}

.tl-capacity-popover__range {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 8px;
}

.tl-capacity-popover__input {
  width: 100%;
  height: 34px;
  min-width: 0;
  padding: 0 10px;
  border: 1px solid var(--tl-filter-border);
  border-radius: 6px;
  outline: 0;
  background: rgba(255, 255, 255, 0.9);
  color: var(--xc-text-strong);
  font: inherit;
  font-size: var(--xc-fs-xs);
  box-sizing: border-box;
  appearance: textfield;
}

.tl-capacity-popover__input::-webkit-outer-spin-button,
.tl-capacity-popover__input::-webkit-inner-spin-button {
  margin: 0;
  appearance: none;
}

.tl-capacity-popover__input:hover {
  border-color: var(--tl-filter-border-hover);
}

.tl-capacity-popover__input:focus-visible {
  border-color: var(--xc-border-accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--xc-border-accent) 22%, transparent);
}

.tl-capacity-popover__dash {
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-xs);
}

.tl-capacity-popover__presets {
  display: grid;
  gap: 6px;
}

.tl-capacity-popover__preset-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tl-capacity-popover__preset,
.tl-capacity-popover__btn {
  height: 30px;
  border: 1px solid var(--tl-filter-border);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.78);
  color: var(--xc-text-secondary);
  font: inherit;
  font-size: var(--xc-fs-2xs);
  cursor: pointer;
  transition: border-color 160ms ease, background-color 160ms ease, color 160ms ease;
}

.tl-capacity-popover__preset {
  padding: 0 9px;
}

.tl-capacity-popover__preset:hover,
.tl-capacity-popover__btn--ghost:hover {
  border-color: var(--tl-filter-border-hover);
  background: rgba(255, 255, 255, 0.94);
  color: var(--xc-text-strong);
}

.tl-capacity-popover__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.tl-capacity-popover__btn {
  padding: 0 12px;
}

.tl-capacity-popover__btn--primary {
  border-color: var(--xc-border-accent);
  background: color-mix(in srgb, var(--xc-border-accent) 14%, transparent);
  color: var(--xc-text-strong);
}

.tl-capacity-popover__btn--primary:hover {
  background: color-mix(in srgb, var(--xc-border-accent) 20%, transparent);
}

@keyframes tl-swap-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(180deg); }
}

@media (max-width: 1180px) {
  .tl-filterbar { align-items: flex-start; }
  .tl-filterbar__actions {
    width: 100%;
    margin-left: 0;
  }
}
</style>
```

- [ ] **Step 2: 添加 Popover 全局样式**

由于 Element Plus Popover popper 默认挂到 body，`popper-class="tl-capacity-popper"` 不受 scoped 选择器影响。在同一文件 scoped 样式后追加一个非 scoped 样式块：

```vue
<style>
.tl-capacity-popper.el-popper {
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.12);
  box-sizing: border-box;
}
</style>
```

- [ ] **Step 3: 运行筛选栏测试**

Run:

```bash
cd agent-frontend && pnpm vitest run tests/tie-line-filter-bar.spec.js
```

Expected: PASS。若 FAIL 是因为测试环境无法解析 `color-mix`，不要改业务逻辑；只需要确认 jsdom 是否对 CSS 文本不执行解析，通常该失败不会发生。

---

### Task 4: 父页面传入筛选结果数量

**Files:**
- Modify: `agent-frontend/src/views/tie-line/index.vue`
- Test: `agent-frontend/tests/tie-line-filter-bar.spec.js`

- [ ] **Step 1: 给 `TieLineFilterBar` 增加展示用 props**

在 `agent-frontend/src/views/tie-line/index.vue` 的 `TieLineFilterBar` 调用中，紧跟 `:region-options` 后添加：

```vue
      :visible-count="store.visibleLines.length"
      :total-count="store.lines.length"
```

最终片段应为：

```vue
    <TieLineFilterBar
      :start-region="store.activeStartRegion"
      :end-region="store.activeEndRegion"
      :min-capacity-mw="store.activeMinCapacityMw"
      :max-capacity-mw="store.activeMaxCapacityMw"
      :region-options="store.filters.regionOptions"
      :visible-count="store.visibleLines.length"
      :total-count="store.lines.length"
      @update:start-region="store.setStartRegion"
      @update:end-region="store.setEndRegion"
      @update:min-capacity-mw="store.setMinCapacityMw"
      @update:max-capacity-mw="store.setMaxCapacityMw"
      @swap-regions="store.swapRegions"
      @reset-filters="store.resetFilters"
    />
```

- [ ] **Step 2: 运行相关测试**

Run:

```bash
cd agent-frontend && pnpm vitest run tests/tie-line-filter-bar.spec.js tests/tie-line-layout.spec.js
```

Expected: PASS。

---

### Task 5: 验证样式约束和构建

**Files:**
- Verify: `agent-frontend/src/views/tie-line/components/TieLineFilterBar.vue`
- Verify: `agent-frontend/tests/tie-line-filter-bar.spec.js`

- [ ] **Step 1: 搜索旧 class 和原生控件样式残留**

Run:

```bash
cd agent-frontend && pnpm vitest run tests/tie-line-filter-bar.spec.js tests/tie-line-store.spec.js tests/tie-line-layout.spec.js
```

Expected: PASS。

手动检查 `TieLineFilterBar.vue`：

- 不再使用 `.tl-filter__field`、`.tl-filter__label`、`.tl-filter__input`、`.tl-filter__reset` 这些旧结构 class。
- 顶部不再直接展示两个容量 number input；number input 只存在于 Popover 内容中。
- 交换和重置按钮不使用 `xc-btn`，避免继承实色或系统按钮观感。

- [ ] **Step 2: 运行前端构建**

Run:

```bash
cd agent-frontend && pnpm build
```

Expected: PASS，输出包含 Vite build 成功信息，没有 Vue 编译错误。

如果 `node` 不在 PATH，先运行：

```bash
export PATH="/c/Program Files/nodejs:$PATH"
cd agent-frontend && pnpm build
```

Expected: PASS。

---

### Task 6: 浏览器截图验收

**Files:**
- Verify: 联络线地图页面 `/tie-line`

- [ ] **Step 1: 启动前端开发服务器**

Run:

```bash
cd agent-frontend && pnpm dev -- --host 127.0.0.1
```

Expected: 开发服务器启动，终端显示本地访问地址，通常为 `http://127.0.0.1:5210/`。

- [ ] **Step 2: 在 1366×768 检查**

打开 `/tie-line`，设置浏览器视口为 1366×768，检查：

- 起点、交换、终点、容量、结果、重置完整展示。
- 行政区名称没有被省略。
- 没有横向滚动条。
- 容量顶部只有一个触发器，未筛选时显示“不限”。

- [ ] **Step 3: 在 1440×900 检查**

设置浏览器视口为 1440×900，检查：

- 筛选栏与标题之间约 10-12px，筛选栏与地图之间约 12px。
- 筛选栏不比标题更醒目。
- 重置按钮无筛选时禁用，存在筛选后启用。

- [ ] **Step 4: 在 1920×1080 检查**

设置浏览器视口为 1920×1080，检查：

- 筛选栏仍是轻量连续工具栏，没有厚重卡片感。
- 交换和重置按钮 hover 为浅色背景，不是实色圆形按钮。
- 容量 Popover 输入框没有原生 inset 边框和上下箭头。

- [ ] **Step 5: 记录无法截图时的替代验证**

如果当前环境无法打开浏览器或截图，最终报告必须明确说明：

```text
浏览器截图验收未执行：当前环境无法启动/访问浏览器。已完成的替代验证为：相关 Vitest 测试通过，pnpm build 通过，并人工检查组件模板与 CSS 已移除原生边框样式入口。
```

---

### Task 7: 文档同步判断

**Files:**
- Optional Modify: `my_projects/联络线地图模块-功能与开发文档.md`

- [ ] **Step 1: 判断是否需要同步模块文档**

如果实现完成后筛选栏行为仍完全符合文档第 4.3 节的“筛选联动”描述，只是视觉结构变化，可以不改文档。

如果要补充容量 Popover 与结果反馈，在 `my_projects/联络线地图模块-功能与开发文档.md` 第 4.3 节筛选联动条目附近追加一句：

```markdown
- **筛选工具栏表现**：顶部筛选以轻量工具栏呈现；起点、终点和额定容量保持同一受控筛选状态，其中容量范围输入收纳在 Popover 内，点击确定后仍走原 `setMinCapacityMw` / `setMaxCapacityMw` 链路刷新 `visibleLines`。
```

- [ ] **Step 2: 若修改文档，运行一次相关测试**

Run:

```bash
cd agent-frontend && pnpm vitest run tests/tie-line-filter-bar.spec.js
```

Expected: PASS。

---

## 自审结果

- Spec coverage: 结构、起终点 select、交换按钮、容量 Popover、重置按钮、结果反馈、激活态、响应式、测试和截图验收均有对应任务。
- Placeholder scan: 本计划不包含 TBD、TODO、implement later、fill in details 等占位指令。
- Type consistency: 新增 props 统一为 `visibleCount`/`totalCount`，事件名沿用 `update:start-region`、`update:end-region`、`update:min-capacity-mw`、`update:max-capacity-mw`、`swap-regions`、`reset-filters`。
- 项目约束: 计划中不包含 `git add`、`git commit`、`git push` 步骤；如需提交由用户另行明确授权。

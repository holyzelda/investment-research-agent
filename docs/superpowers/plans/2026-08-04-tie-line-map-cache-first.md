# 联络线地图缓存优先加载优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让联络线地图首次正常加载、二次进入直接展示缓存，并在后台静默刷新基础数据。

**Architecture:** 在 `tieLine` Pinia store 中加入缓存加载状态、静默刷新状态和请求版本保护；页面根据 `loaded` 区分阻塞加载与缓存展示。地图组件不做结构性改造，继续通过现有 watcher 接收刷新后的线路数据并保留视角。

**Tech Stack:** Vue 3 `<script setup>`、Pinia、ECharts、Vitest、Vite raw component source tests、npm。

---

## 文件结构

- Modify: `agent-frontend/src/store/modules/tieLine.js`
  - 职责：联络线基础数据、筛选、详情、功率趋势状态管理。
  - 本次增加：`loaded`、`refreshing`、`lastLoadedAt`、`lineRequestVersion`，并改造 `loadLines({ force, silent })`。
- Modify: `agent-frontend/src/views/tie-line/index.vue`
  - 职责：联络线页面布局和页面级加载/错误/地图展示控制。
  - 本次增加：缓存优先加载入口、加载态/错误态条件调整、重试按钮强制加载。
- Modify: `agent-frontend/tests/tie-line-store.spec.js`
  - 职责：store 筛选、推荐、加载状态和异步保护单元测试。
  - 本次增加：API mock 和缓存优先加载测试。
- Modify: `agent-frontend/tests/tie-line-layout.spec.js`
  - 职责：通过 raw source 验证页面模板和关键样式约束。
  - 本次增加：页面 loading/error 条件与挂载调用约束测试。

## 执行约束

- 所有命令从 `agent-frontend/` 目录执行。
- 使用 npm，不使用 pnpm/yarn。
- 先写失败测试，再实现最小代码，再跑测试。
- 不执行 `git add`、`git commit`、`git push`，除非用户明确要求。

---

### Task 1: 为 tieLine store 增加缓存优先加载测试

**Files:**
- Modify: `agent-frontend/tests/tie-line-store.spec.js`
- Test: `agent-frontend/tests/tie-line-store.spec.js`

- [ ] **Step 1: 在测试文件顶部加入 API mock**

将 `agent-frontend/tests/tie-line-store.spec.js` 顶部改为：

```js
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useTieLineStore, normalizeCapacityMw, parseLengthKm } from '@/store/modules/tieLine'
import { getTieLines } from '@/api/tieLine'

vi.mock('@/api/tieLine', () => ({
  getTieLines: vi.fn(),
  getTieLineDetail: vi.fn(),
  getTieLinePower: vi.fn(),
}))
```

保留文件中现有 `lines`、`visibleIds` 和现有测试内容。

- [ ] **Step 2: 在现有 describe 后追加加载测试**

在文件末尾追加：

```js
describe('联络线基础数据缓存加载', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('首次加载成功后写入基础数据并标记已加载', async () => {
    const store = useTieLineStore()
    getTieLines.mockResolvedValue({
      data: {
        items: [{ id: 9, startRegion: '西北', endRegion: '华东' }],
        stats: { total: 1 },
        filters: { voltageOptions: ['±800kV'], regionOptions: ['西北'] },
      },
    })

    const promise = store.loadLines()
    expect(store.loading).toBe(true)
    expect(store.refreshing).toBe(false)

    await promise

    expect(store.lines).toEqual([{ id: 9, startRegion: '西北', endRegion: '华东' }])
    expect(store.stats).toEqual({ total: 1 })
    expect(store.filters).toEqual({ voltageOptions: ['±800kV'], regionOptions: ['西北'] })
    expect(store.loaded).toBe(true)
    expect(store.loading).toBe(false)
    expect(store.refreshing).toBe(false)
    expect(store.error).toBe('')
    expect(store.lastLoadedAt).toBeTypeOf('number')
  })

  it('已有缓存时普通加载直接复用数据，不重复请求接口', async () => {
    const store = useTieLineStore()
    store.loaded = true
    store.lines = [{ id: 1, startRegion: '西北', endRegion: '华南' }]
    store.stats = { total: 1 }

    await store.loadLines()

    expect(getTieLines).not.toHaveBeenCalled()
    expect(store.lines).toEqual([{ id: 1, startRegion: '西北', endRegion: '华南' }])
    expect(store.stats).toEqual({ total: 1 })
    expect(store.loading).toBe(false)
    expect(store.refreshing).toBe(false)
  })

  it('静默刷新不清空旧数据且不进入阻塞 loading', async () => {
    const store = useTieLineStore()
    store.loaded = true
    store.lines = [{ id: 1, startRegion: '西北', endRegion: '华南' }]
    store.stats = { total: 1 }
    getTieLines.mockResolvedValue({
      data: {
        items: [{ id: 2, startRegion: '华北', endRegion: '华东' }],
        stats: { total: 2 },
        filters: { voltageOptions: ['500kV'], regionOptions: ['华北'] },
      },
    })

    const promise = store.loadLines({ force: true, silent: true })

    expect(store.loading).toBe(false)
    expect(store.refreshing).toBe(true)
    expect(store.lines).toEqual([{ id: 1, startRegion: '西北', endRegion: '华南' }])

    await promise

    expect(store.lines).toEqual([{ id: 2, startRegion: '华北', endRegion: '华东' }])
    expect(store.stats).toEqual({ total: 2 })
    expect(store.filters).toEqual({ voltageOptions: ['500kV'], regionOptions: ['华北'] })
    expect(store.loaded).toBe(true)
    expect(store.loading).toBe(false)
    expect(store.refreshing).toBe(false)
    expect(store.error).toBe('')
  })

  it('静默刷新失败时保留旧数据且不展示阻塞错误', async () => {
    const store = useTieLineStore()
    store.loaded = true
    store.lines = [{ id: 1, startRegion: '西北', endRegion: '华南' }]
    store.stats = { total: 1 }
    store.filters = { voltageOptions: ['±800kV'], regionOptions: ['西北'] }
    getTieLines.mockRejectedValue(new Error('网络错误'))

    await store.loadLines({ force: true, silent: true })

    expect(store.lines).toEqual([{ id: 1, startRegion: '西北', endRegion: '华南' }])
    expect(store.stats).toEqual({ total: 1 })
    expect(store.filters).toEqual({ voltageOptions: ['±800kV'], regionOptions: ['西北'] })
    expect(store.loaded).toBe(true)
    expect(store.loading).toBe(false)
    expect(store.refreshing).toBe(false)
    expect(store.error).toBe('')
  })

  it('无缓存加载失败时清空数据并设置错误', async () => {
    const store = useTieLineStore()
    store.lines = [{ id: 1 }]
    getTieLines.mockRejectedValue(new Error('网络错误'))

    await store.loadLines({ force: true })

    expect(store.lines).toEqual([])
    expect(store.loaded).toBe(false)
    expect(store.loading).toBe(false)
    expect(store.refreshing).toBe(false)
    expect(store.error).toBe('联络线数据加载失败，请稍后重试')
  })

  it('后发请求完成后，先发请求不得覆盖状态', async () => {
    const store = useTieLineStore()
    let resolveFirst
    const firstRequest = new Promise((resolve) => { resolveFirst = resolve })
    getTieLines
      .mockReturnValueOnce(firstRequest)
      .mockResolvedValueOnce({
        data: {
          items: [{ id: 2, startRegion: '华北', endRegion: '华东' }],
          stats: { total: 2 },
          filters: { voltageOptions: ['500kV'], regionOptions: ['华北'] },
        },
      })

    const slowPromise = store.loadLines({ force: true })
    const fastPromise = store.loadLines({ force: true, silent: true })
    await fastPromise

    resolveFirst({
      data: {
        items: [{ id: 1, startRegion: '西北', endRegion: '华南' }],
        stats: { total: 1 },
        filters: { voltageOptions: ['±800kV'], regionOptions: ['西北'] },
      },
    })
    await slowPromise

    expect(store.lines).toEqual([{ id: 2, startRegion: '华北', endRegion: '华东' }])
    expect(store.stats).toEqual({ total: 2 })
    expect(store.filters).toEqual({ voltageOptions: ['500kV'], regionOptions: ['华北'] })
    expect(store.loaded).toBe(true)
    expect(store.loading).toBe(false)
    expect(store.refreshing).toBe(false)
  })
})
```

- [ ] **Step 3: 运行测试并确认失败**

Run:

```bash
npm exec vitest -- run tests/tie-line-store.spec.js
```

Expected: FAIL。失败原因应包含 `loaded`、`refreshing`、`lastLoadedAt`、`loadLines` 参数行为或 API mock 相关断言未满足。

---

### Task 2: 实现 tieLine store 缓存优先加载

**Files:**
- Modify: `agent-frontend/src/store/modules/tieLine.js`
- Test: `agent-frontend/tests/tie-line-store.spec.js`

- [ ] **Step 1: 修改 state，增加加载状态字段**

在 `state: () => ({ ... })` 中，将末尾加载状态从：

```js
    loading: false,
    error: '',
```

改为：

```js
    loading: false,
    refreshing: false,
    loaded: false,
    lastLoadedAt: null,
    lineRequestVersion: 0,
    error: '',
```

- [ ] **Step 2: 用缓存优先版本替换 loadLines action**

将现有 `async loadLines() { ... }` 整个替换为：

```js
    async loadLines({ force = false, silent = false } = {}) {
      if (this.loaded && !force && !silent) return

      const requestVersion = this.lineRequestVersion + 1
      this.lineRequestVersion = requestVersion
      const blocking = !silent

      if (blocking) {
        this.loading = true
        this.error = ''
      } else {
        this.refreshing = true
      }

      try {
        const res = await getTieLines()
        if (requestVersion !== this.lineRequestVersion) return

        const data = res?.data || {}
        this.lines = data.items || []
        this.stats = data.stats || null
        this.filters = data.filters || { voltageOptions: [], regionOptions: [] }
        this.loaded = true
        this.lastLoadedAt = Date.now()
        this.error = ''
        this._dropSelectionIfHidden()
      } catch (e) {
        if (requestVersion !== this.lineRequestVersion) return

        if (!this.loaded) {
          this.error = '联络线数据加载失败，请稍后重试'
          this.lines = []
          this.stats = null
          this.filters = { voltageOptions: [], regionOptions: [] }
        }
      } finally {
        if (requestVersion === this.lineRequestVersion) {
          if (blocking) this.loading = false
          else this.refreshing = false
        }
      }
    },
```

- [ ] **Step 3: 运行 store 测试并确认通过**

Run:

```bash
npm exec vitest -- run tests/tie-line-store.spec.js
```

Expected: PASS。

---

### Task 3: 为页面缓存展示逻辑增加 raw source 测试

**Files:**
- Modify: `agent-frontend/tests/tie-line-layout.spec.js`
- Test: `agent-frontend/tests/tie-line-layout.spec.js`

- [ ] **Step 1: 追加页面行为测试**

在 `describe('联络线页面主体布局', () => { ... })` 内追加：

```js
  it('有缓存时不显示整屏加载和错误态，并在挂载时静默刷新', () => {
    expect(tieLinePageSource).toContain('const isBlockingLoading = computed(() => store.loading && !store.loaded)')
    expect(tieLinePageSource).toContain('const isBlockingError = computed(() => store.error && !store.loaded)')
    expect(tieLinePageSource).toContain('v-if="isBlockingLoading"')
    expect(tieLinePageSource).toContain('v-else-if="isBlockingError"')
    expect(tieLinePageSource).toContain('store.loadLines({ force: true, silent: true })')
    expect(tieLinePageSource).toContain('store.loadLines({ force: true })')
  })
```

- [ ] **Step 2: 运行页面测试并确认失败**

Run:

```bash
npm exec vitest -- run tests/tie-line-layout.spec.js
```

Expected: FAIL。失败原因应指出 `isBlockingLoading`、`isBlockingError` 或新的 `loadLines` 调用不存在。

---

### Task 4: 改造联络线页面加载态和挂载逻辑

**Files:**
- Modify: `agent-frontend/src/views/tie-line/index.vue`
- Test: `agent-frontend/tests/tie-line-layout.spec.js`

- [ ] **Step 1: 替换模板中的加载和错误条件**

将模板中的：

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

替换为：

```vue
        <div v-if="isBlockingLoading" class="tie-line-page__state tie-line-page__state--loading" aria-live="polite">
          <span class="xc-skeleton xc-skeleton-rect tie-line-page__skeleton" aria-hidden="true" />
          <span>正在加载联络线资料</span>
        </div>
        <div v-else-if="isBlockingError" class="tie-line-page__state tie-line-page__state--error" role="alert">
          <strong>数据加载失败</strong>
          <span>{{ store.error }}</span>
          <button class="xc-btn xc-btn--ghost" type="button" @click="store.loadLines({ force: true })">重试</button>
        </div>
```

- [ ] **Step 2: 增加阻塞加载和阻塞错误 computed**

在 `hasNoVisibleLines` computed 后面加入：

```js
const isBlockingLoading = computed(() => store.loading && !store.loaded)
const isBlockingError = computed(() => store.error && !store.loaded)
```

- [ ] **Step 3: 替换 onMounted 加载逻辑**

将：

```js
onMounted(() => {
  store.loadLines()
})
```

替换为：

```js
onMounted(() => {
  if (store.loaded) {
    store.loadLines({ force: true, silent: true })
    return
  }
  store.loadLines()
})
```

- [ ] **Step 4: 运行页面测试并确认通过**

Run:

```bash
npm exec vitest -- run tests/tie-line-layout.spec.js
```

Expected: PASS。

---

### Task 5: 跑联络线相关回归测试

**Files:**
- Test: `agent-frontend/tests/tie-line-store.spec.js`
- Test: `agent-frontend/tests/tie-line-layout.spec.js`
- Test: `agent-frontend/tests/tie-line-map-option.spec.js`
- Test: `agent-frontend/tests/tie-line-map-toolbar.spec.js`
- Test: `agent-frontend/tests/tie-line-filter-bar.spec.js`
- Test: `agent-frontend/tests/tie-line-list-panel.spec.js`
- Test: `agent-frontend/tests/tie-line-detail-panel.spec.js`
- Test: `agent-frontend/tests/tie-line-power-store.spec.js`
- Test: `agent-frontend/tests/tie-line-power-trend.spec.js`
- Test: `agent-frontend/tests/tie-line-voltage-presentation.spec.js`

- [ ] **Step 1: 运行联络线相关测试**

Run:

```bash
npm exec vitest -- run tests/tie-line-store.spec.js tests/tie-line-layout.spec.js tests/tie-line-map-option.spec.js tests/tie-line-map-toolbar.spec.js tests/tie-line-filter-bar.spec.js tests/tie-line-list-panel.spec.js tests/tie-line-detail-panel.spec.js tests/tie-line-power-store.spec.js tests/tie-line-power-trend.spec.js tests/tie-line-voltage-presentation.spec.js
```

Expected: PASS。

- [ ] **Step 2: 如果测试失败，按失败类型修复**

如果 `tie-line-layout.spec.js` 中旧测试仍断言过时的 `.tie-line-page__filter-row`，不要为适配旧字符串恢复不存在的 DOM。应先确认当前页面源码中的实际布局类名，然后把测试断言更新为当前布局，例如：

```js
expect(tieLinePageSource).toContain('class="tie-line-page__notice-row"')
expect(styles).toContain('.tie-line-page__notice-row')
```

修复后重新运行 Step 1 的命令，Expected: PASS。

---

### Task 6: 构建验证

**Files:**
- No source changes expected.

- [ ] **Step 1: 运行前端生产构建**

Run:

```bash
npm run build
```

Expected: PASS，Vite 构建完成，无 Vue 编译错误。

- [ ] **Step 2: 记录验证结果**

在最终回复中如实说明：

```text
已运行：npm exec vitest -- run <联络线相关测试列表>
已运行：npm run build
结果：全部通过
```

如果失败，记录失败命令和关键错误输出，不声称完成。

---

## 自检结果

- Spec coverage：计划覆盖了首次加载、二次缓存展示、静默刷新、失败保留旧数据、详情/功率趋势不改动、地图组件不结构性改造、测试验证。
- Placeholder scan：未保留 TBD/TODO/“稍后实现”等占位描述。
- Type consistency：状态字段统一为 `loaded`、`refreshing`、`lastLoadedAt`、`lineRequestVersion`；`loadLines` 签名统一为 `loadLines({ force = false, silent = false } = {})`。

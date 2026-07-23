# 政策与市场模块 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为朱雀投研智能体新增可交互的“政策与市场”三栏工作台，并以模拟 API 支撑后续数据库与咨询服务接入。

**Architecture:** 新页面通过 `/policy-market` 路由进入，并复用应用既有布局、导航轨道与 XC 深色 Token。`api/policyMarket.js` 是模拟数据和未来 HTTP 请求的唯一边界，`policyMarket` Pinia Store 集中管理咨询、资讯、筛选、请求状态；页面组件只消费 Store 状态并触发动作。

**Tech Stack:** Vue 3、Vue Router 4、Pinia、Element Plus、Vitest、Vue Test Utils、XC CSS 自定义属性。

---

## 文件结构

| 文件 | 责任 |
|---|---|
| `agent-frontend/src/api/policyMarket.js` | 提供异步模拟数据与未来真实接口的稳定调用边界。 |
| `agent-frontend/src/store/modules/policyMarket.js` | 管理咨询、资讯、统计筛选、加载和失败状态。 |
| `agent-frontend/src/views/policy-market/index.vue` | 页面编排、初始化加载与三栏响应式布局。 |
| `agent-frontend/src/views/policy-market/components/ConsultationHistory.vue` | 展示并选择“我的提问”，提供新建提问动作。 |
| `agent-frontend/src/views/policy-market/components/ConsultationComposer.vue` | 管理问题输入、快捷问题和键盘提交。 |
| `agent-frontend/src/views/policy-market/components/ConsultationResult.vue` | 显示空态、处理中、失败和完成的咨询结果。 |
| `agent-frontend/src/views/policy-market/components/MarketPulse.vue` | 展示筛选控件、统计概览、资讯列表和市场观察。 |
| `agent-frontend/src/views/policy-market/components/NewsDetailDialog.vue` | 用 Element Plus 弹窗展示单条资讯详情。 |
| `agent-frontend/src/router/index.js` | 注册静态政策与市场路由。 |
| `agent-frontend/src/layout/index.vue` | 将政策与市场页归入隐藏通用测算侧栏的页面集合，并维护导航映射。 |
| `agent-frontend/src/layout/components/AppRail.vue` | 启用“政策与市场”默认导航项。 |
| `agent-frontend/tests/policy-market-api.spec.js` | 校验模拟 API 数据形状和统计筛选行为。 |
| `agent-frontend/tests/policy-market-store.spec.js` | 校验 Store 数据加载、咨询提交和失败处理。 |
| `agent-frontend/tests/policy-market-components.spec.js` | 校验核心组件交互与可访问状态。 |
| `agent-frontend/tests/policy-market-page.spec.js` | 校验页面布局、路由、侧栏隐藏和模块导航。 |
| `agent-frontend/docs/README.md` 或 `my_projects/investment-research-agent-项目开发指南.md` 的前端页面章节 | 按仓库文档规则补充新路由、Store、API 和验证入口。 |

> 实施前先确认开发指南中的前端章节所指向的文档是否存在并读取对应章节；如实际文档位置或命名与上表不同，更新同一权威开发指南，不创建平行说明文档。

### Task 1: 定义模拟 API 边界并以测试固定 DTO

**Files:**
- Create: `agent-frontend/src/api/policyMarket.js`
- Create: `agent-frontend/tests/policy-market-api.spec.js`

- [ ] **Step 1: 编写失败的模拟 API 测试**

```js
import { describe, expect, it } from 'vitest'
import {
  getConsultationStats,
  getConsultations,
  getMarketNews,
  submitConsultation,
} from '@/api/policyMarket'

describe('政策与市场模拟 API', () => {
  it('返回可直接映射为页面 DTO 的咨询记录', async () => {
    const records = await getConsultations()

    expect(records.length).toBeGreaterThan(0)
    expect(records[0]).toMatchObject({
      id: expect.any(String),
      title: expect.any(String),
      question: expect.any(String),
      answer: expect.any(String),
      status: 'completed',
      createdAt: expect.any(String),
      sourceScope: expect.any(Array),
    })
  })

  it('提交咨询后返回已完成的结构化回答', async () => {
    const consultation = await submitConsultation({ question: '储能行业的投资机会' })

    expect(consultation).toMatchObject({
      id: expect.any(String),
      title: '储能行业的投资机会',
      question: '储能行业的投资机会',
      status: 'completed',
      answer: expect.any(String),
    })
  })

  it('按筛选参数聚合统计结果', async () => {
    const all = await getConsultationStats({ province: 'all', period: 'all', topic: 'all' })
    const innerMongolia = await getConsultationStats({ province: '内蒙古', period: 'month', topic: '政策' })

    expect(all).toMatchObject({ total: expect.any(Number), trend: expect.any(Number), rangeLabel: '全部省份' })
    expect(innerMongolia).toMatchObject({ total: 186, rangeLabel: '内蒙古' })
    expect(innerMongolia.total).toBeLessThan(all.total)
  })

  it('返回带来源和正文的市场资讯', async () => {
    const news = await getMarketNews()

    expect(news[0]).toMatchObject({
      id: expect.any(String),
      category: expect.any(String),
      title: expect.any(String),
      publishedAt: expect.any(String),
      content: expect.any(String),
      source: expect.any(String),
    })
  })
})
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `cd agent-frontend && npm exec vitest -- run tests/policy-market-api.spec.js`

Expected: FAIL，原因是 `@/api/policyMarket` 尚不存在。

- [ ] **Step 3: 实现最小模拟 API**

创建 `agent-frontend/src/api/policyMarket.js`。使用下列稳定 DTO 和小型延迟函数，模拟未来网络调用，页面层不得导入任何内部模拟数据。

```js
const delay = (value, ms = 180) => new Promise((resolve) => window.setTimeout(() => resolve(value), ms))

const consultations = [
  {
    id: 'consultation-001',
    title: '新能源消纳政策有何变化？',
    question: '新能源消纳政策有何变化？',
    answer: '近期政策重点已从单纯扩大新能源装机，转向提升系统消纳能力。项目投资应重点关注并网条件、消纳责任权重和峰谷价差变化。',
    status: 'completed',
    createdAt: '2026-07-23T10:42:00+08:00',
    sourceScope: ['政策文件', '市场行情', '行业资讯'],
  },
]

const news = [
  {
    id: 'news-001',
    category: '政策',
    title: '国家能源局：加快推动新型储能规模化发展',
    publishedAt: '2026-07-23T09:00:00+08:00',
    content: '国家能源局近日发布相关工作安排，提出完善新型储能参与电力市场和调度运行机制，进一步释放储能的灵活调节价值。',
    source: '政策与市场研究台公开信息整理',
  },
]

const consultationStats = [
  { province: '内蒙古', period: 'month', topic: '政策', count: 186 },
  { province: '山东', period: 'month', topic: '市场', count: 143 },
  { province: '江苏', period: 'month', topic: '行业', count: 127 },
  { province: '广东', period: 'quarter', topic: '政策', count: 241 },
]

export function getConsultations() {
  return delay(consultations.map((item) => ({ ...item })))
}

export function submitConsultation({ question }) {
  const normalizedQuestion = String(question || '').trim()
  if (!normalizedQuestion) return Promise.reject(new Error('请输入政策或市场问题'))
  return delay({
    id: `consultation-${Date.now()}`,
    title: normalizedQuestion,
    question: normalizedQuestion,
    answer: '已收到你的咨询。系统将结合政策原文、市场数据与相关行业动态进行整理，为你生成结构化分析。',
    status: 'completed',
    createdAt: new Date().toISOString(),
    sourceScope: ['政策文件', '市场行情', '行业资讯'],
  }, 420)
}

export function getMarketNews() {
  return delay(news.map((item) => ({ ...item })))
}

export function getConsultationStats({ province = 'all', period = 'all', topic = 'all' } = {}) {
  const matched = consultationStats.filter((item) =>
    (province === 'all' || item.province === province)
    && (period === 'all' || item.period === period || (period === 'quarter' && item.period === 'month'))
    && (topic === 'all' || item.topic === topic),
  )
  return delay({
    total: matched.reduce((sum, item) => sum + item.count, 0),
    trend: matched.length ? Number((8 + matched.length * 1.3).toFixed(1)) : 0,
    rangeLabel: province === 'all' ? '全部省份' : province,
  })
}
```

补齐参考设计中的其余历史咨询、资讯和统计明细，使用户能看到多个可选择的问题与资讯，但保持上面四个函数签名与 DTO 字段不变。避免将 `Date.now()` 作为测试断言对象，测试只验证类型和稳定字段。

- [ ] **Step 4: 运行 API 测试并确认通过**

Run: `cd agent-frontend && npm exec vitest -- run tests/policy-market-api.spec.js`

Expected: PASS，4 个测试通过。

- [ ] **Step 5: 检查变更范围，不执行 Git 写操作**

Run: `git diff -- agent-frontend/src/api/policyMarket.js agent-frontend/tests/policy-market-api.spec.js`

Expected: 仅包含模拟 API 与其测试。仓库规则禁止未经用户明确要求执行 `git add`、`git commit` 或 `git push`，因此本计划不执行提交。

### Task 2: 建立 Policy Market Store 并测试请求状态

**Files:**
- Create: `agent-frontend/src/store/modules/policyMarket.js`
- Create: `agent-frontend/tests/policy-market-store.spec.js`

- [ ] **Step 1: 编写失败的 Store 行为测试**

```js
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import * as api from '@/api/policyMarket'
import { usePolicyMarketStore } from '@/store/modules/policyMarket'

vi.mock('@/api/policyMarket', () => ({
  getConsultations: vi.fn(),
  submitConsultation: vi.fn(),
  getMarketNews: vi.fn(),
  getConsultationStats: vi.fn(),
}))

describe('政策与市场 Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  it('初始化时加载咨询、资讯和默认统计', async () => {
    api.getConsultations.mockResolvedValue([{ id: 'c-1', title: '问题', status: 'completed' }])
    api.getMarketNews.mockResolvedValue([{ id: 'n-1', title: '资讯' }])
    api.getConsultationStats.mockResolvedValue({ total: 10, trend: 12.6, rangeLabel: '全部省份' })
    const store = usePolicyMarketStore()

    await store.loadInitialData()

    expect(store.consultations).toHaveLength(1)
    expect(store.news).toHaveLength(1)
    expect(store.stats.total).toBe(10)
    expect(store.selectedConsultationId).toBe('c-1')
  })

  it('提交时先插入处理中记录，成功后以 API 回答替换', async () => {
    let resolveSubmit
    api.submitConsultation.mockImplementation(() => new Promise((resolve) => { resolveSubmit = resolve }))
    const store = usePolicyMarketStore()

    const pending = store.submitQuestion('储能行业的投资机会')
    expect(store.selectedConsultation.status).toBe('processing')

    resolveSubmit({ id: 'c-new', title: '储能行业的投资机会', question: '储能行业的投资机会', answer: '结构化分析', status: 'completed', createdAt: '2026-07-23T12:00:00+08:00', sourceScope: [] })
    await pending

    expect(store.selectedConsultation).toMatchObject({ id: 'c-new', status: 'completed', answer: '结构化分析' })
  })

  it('提交失败时保留问题并记录错误，不伪造回答', async () => {
    api.submitConsultation.mockRejectedValue(new Error('服务暂不可用'))
    const store = usePolicyMarketStore()

    await expect(store.submitQuestion('现货市场运行情况')).rejects.toThrow('服务暂不可用')

    expect(store.selectedConsultation).toMatchObject({ question: '现货市场运行情况', status: 'failed' })
    expect(store.selectedConsultation.answer).toBe('')
    expect(store.submitError).toBe('服务暂不可用')
  })

  it('筛选变化时将当前参数传递给统计 API', async () => {
    api.getConsultationStats.mockResolvedValue({ total: 186, trend: 9.3, rangeLabel: '内蒙古' })
    const store = usePolicyMarketStore()

    await store.setStatsFilters({ province: '内蒙古', period: 'month', topic: '政策' })

    expect(api.getConsultationStats).toHaveBeenCalledWith({ province: '内蒙古', period: 'month', topic: '政策' })
    expect(store.stats.total).toBe(186)
  })
})
```

- [ ] **Step 2: 运行 Store 测试并确认失败**

Run: `cd agent-frontend && npm exec vitest -- run tests/policy-market-store.spec.js`

Expected: FAIL，原因是 `@/store/modules/policyMarket` 尚不存在。

- [ ] **Step 3: 实现 Pinia Store**

创建 `agent-frontend/src/store/modules/policyMarket.js`。实现以下状态和动作，字段名必须与测试和设计规格一致：

```js
state: () => ({
  consultations: [],
  selectedConsultationId: null,
  consultationsLoading: false,
  consultationsError: '',
  submitting: false,
  submitError: '',
  news: [],
  newsLoading: false,
  newsError: '',
  statsFilters: { province: 'all', period: 'all', topic: 'all' },
  stats: { total: 0, trend: 0, rangeLabel: '全部省份' },
  statsLoading: false,
  statsError: '',
})
```

实现以下 getter：

```js
selectedConsultation: (state) => state.consultations.find(
  (item) => item.id === state.selectedConsultationId,
) || null
```

实现以下动作：

- `loadInitialData()` 使用 `Promise.allSettled` 并行调用 `loadConsultations()`、`loadNews()` 和 `loadStats()`，确保某一路失败不会清空另两路成功数据。
- `loadConsultations()` 成功后写入列表，并在没有当前选中项时自动选择第一项；失败时设 `consultationsError`，不清空已有列表。
- `loadNews()` 成功后写入 `news`；失败时设 `newsError`，不清空已有列表。
- `loadStats()` 用 `statsFilters` 调用 API，成功时更新 `stats`；失败时设 `statsError`，不重置已有统计。
- `selectConsultation(id)` 仅在列表存在该 id 时更新选中项。
- `startNewConsultation()` 清空选中项和 `submitError`，不删除历史列表。
- `submitQuestion(question)` 去除首尾空白；空值抛出 `Error('请输入政策或市场问题')`；为当前问题创建 `status: 'processing'`、`answer: ''` 的临时记录，置顶并选中；成功后用 API 返回记录替换临时项；失败时仅将该临时项变为 `status: 'failed'`，保留原问题和空回答，赋值 `submitError` 后原样抛出异常。
- `setStatsFilters(nextFilters)` 通过 `{ ...this.statsFilters, ...nextFilters }` 合并，并等待 `loadStats()`。

临时记录 ID 使用 `pending-${Date.now()}`，仅作为前端本次请求内的替换标识。组件不得自行修改这些状态。

- [ ] **Step 4: 运行 Store 测试并确认通过**

Run: `cd agent-frontend && npm exec vitest -- run tests/policy-market-store.spec.js`

Expected: PASS，4 个测试通过。

- [ ] **Step 5: 运行 API 与 Store 回归测试**

Run: `cd agent-frontend && npm exec vitest -- run tests/policy-market-api.spec.js tests/policy-market-store.spec.js`

Expected: PASS，8 个测试通过。

### Task 3: 实现咨询历史、输入与结果组件

**Files:**
- Create: `agent-frontend/src/views/policy-market/components/ConsultationHistory.vue`
- Create: `agent-frontend/src/views/policy-market/components/ConsultationComposer.vue`
- Create: `agent-frontend/src/views/policy-market/components/ConsultationResult.vue`
- Create: `agent-frontend/tests/policy-market-components.spec.js`

- [ ] **Step 1: 编写失败的组件交互测试**

```js
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ConsultationComposer from '@/views/policy-market/components/ConsultationComposer.vue'
import ConsultationHistory from '@/views/policy-market/components/ConsultationHistory.vue'
import ConsultationResult from '@/views/policy-market/components/ConsultationResult.vue'

describe('政策与市场咨询组件', () => {
  it('历史列表发出新建和选择事件，不渲染删除动作', async () => {
    const wrapper = mount(ConsultationHistory, {
      props: {
        consultations: [{ id: 'c-1', title: '新能源消纳政策有何变化？', createdAt: '2026-07-23T10:42:00+08:00' }],
        selectedId: 'c-1',
      },
    })

    expect(wrapper.text()).not.toContain('删除')
    await wrapper.get('[aria-label="新建提问"]').trigger('click')
    await wrapper.get('[data-consultation-id="c-1"]').trigger('click')
    expect(wrapper.emitted('new-question')).toHaveLength(1)
    expect(wrapper.emitted('select')).toEqual([['c-1']])
  })

  it('快捷问题填入输入框，Ctrl+Enter 发出提交事件', async () => {
    const wrapper = mount(ConsultationComposer)

    await wrapper.get('[data-quick-question]').trigger('click')
    expect(wrapper.get('textarea').element.value).toBeTruthy()
    await wrapper.get('textarea').trigger('keydown', { key: 'Enter', ctrlKey: true })
    expect(wrapper.emitted('submit-question')?.[0]?.[0]).toBeTruthy()
  })

  it('空输入不提交并显示结果区空态', async () => {
    const composer = mount(ConsultationComposer)
    const result = mount(ConsultationResult, { props: { consultation: null } })

    await composer.get('[aria-label="提交咨询"]').trigger('click')
    expect(composer.emitted('submit-question')).toBeUndefined()
    expect(result.text()).toContain('你的咨询结果将展示在这里')
  })

  it('按咨询状态显示处理中、失败和完成结果', () => {
    const processing = mount(ConsultationResult, { props: { consultation: { status: 'processing', question: '问题' } } })
    const failed = mount(ConsultationResult, { props: { consultation: { status: 'failed', question: '问题', answer: '' } } })
    const completed = mount(ConsultationResult, { props: { consultation: { status: 'completed', title: '问题', answer: '回答', sourceScope: ['政策文件'] } } })

    expect(processing.text()).toContain('正在分析')
    expect(failed.text()).toContain('咨询失败')
    expect(completed.text()).toContain('回答')
    expect(completed.text()).toContain('政策文件')
  })
})
```

- [ ] **Step 2: 运行组件测试并确认失败**

Run: `cd agent-frontend && npm exec vitest -- run tests/policy-market-components.spec.js`

Expected: FAIL，原因是三个组件尚不存在。

- [ ] **Step 3: 实现 `ConsultationHistory.vue`**

组件 props：`consultations`（数组）和 `selectedId`（字符串或 null）；emits：`new-question`、`select`。

模板必须具备以下可测试结构：

```vue
<aside class="pm-history" aria-label="我的提问">
  <div class="pm-history__heading">
    <h2>我的提问</h2>
    <button type="button" aria-label="新建提问" @click="$emit('new-question')">+</button>
  </div>
  <p class="pm-history__caption">历史咨询记录</p>
  <p v-if="!consultations.length" class="pm-history__empty">暂无咨询记录</p>
  <nav v-else class="pm-history__list" aria-label="历史咨询记录">
    <button
      v-for="item in consultations"
      :key="item.id"
      type="button"
      class="pm-history__item"
      :class="{ 'is-active': item.id === selectedId }"
      :data-consultation-id="item.id"
      :aria-current="item.id === selectedId ? 'page' : undefined"
      @click="$emit('select', item.id)"
    >
      <span>{{ item.title || item.question }}</span>
      <time>{{ formatHistoryTime(item.createdAt) }}</time>
    </button>
  </nav>
</aside>
```

在 `<script setup>` 内提供 `formatHistoryTime(value)`：空值返回 `—`；有效时间以 `Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit' })` 格式化。所有颜色、边框、文字均引用 XC Token；不添加删除控件。

- [ ] **Step 4: 实现 `ConsultationComposer.vue`**

组件 emits：`submit-question`。内部用 `ref('')` 保存文本，定义三个中文快捷问题。实现 `submit()`：`trim()` 后为空则对 `textareaRef.value?.focus()` 并返回；非空时 `$emit('submit-question', question)`，然后清空文本。键盘监听只在 `(event.ctrlKey || event.metaKey) && event.key === 'Enter'` 时调用 `submit()`。

模板至少包含：

```vue
<div class="pm-composer">
  <textarea ref="textareaRef" v-model="question" placeholder="输入你想了解的政策或市场问题…" rows="2" />
  <div class="pm-composer__tools">
    <span>Ctrl / Cmd + Enter 提交咨询</span>
    <button type="button" aria-label="提交咨询" @click="submit">提交</button>
  </div>
  <div class="pm-composer__quick">
    <span>试试这些：</span>
    <button v-for="item in quickQuestions" :key="item" type="button" data-quick-question @click="question = item">{{ item }}</button>
  </div>
</div>
```

使用 `defineExpose({ focus: () => textareaRef.value?.focus() })`，供页面在新建提问时聚焦。

- [ ] **Step 5: 实现 `ConsultationResult.vue`**

组件 props：`consultation`。按如下状态渲染：

- `null`：显示“你的咨询结果将展示在这里”。
- `status === 'processing'`：显示“正在分析”，并添加 `role="status" aria-live="polite"`。
- `status === 'failed'`：显示“咨询失败”和“请重新提交问题”。
- `status === 'completed'`：显示标题、回答、`sourceScope.join(' / ')` 与“分析完成”。

完成态模板使用 `v-if="consultation?.status === 'completed'"`，并对 `title || question` 做回退。不得使用 `v-html` 渲染任何问题、回答或资讯文本。

- [ ] **Step 6: 运行组件测试并确认通过**

Run: `cd agent-frontend && npm exec vitest -- run tests/policy-market-components.spec.js`

Expected: PASS，4 个测试通过。

### Task 4: 实现市场脉搏与资讯详情组件

**Files:**
- Create: `agent-frontend/src/views/policy-market/components/MarketPulse.vue`
- Create: `agent-frontend/src/views/policy-market/components/NewsDetailDialog.vue`
- Modify: `agent-frontend/tests/policy-market-components.spec.js`

- [ ] **Step 1: 向组件测试追加市场脉搏与资讯详情的失败用例**

```js
import MarketPulse from '@/views/policy-market/components/MarketPulse.vue'
import NewsDetailDialog from '@/views/policy-market/components/NewsDetailDialog.vue'

it('筛选变化时发出完整筛选条件，并可选择资讯', async () => {
  const wrapper = mount(MarketPulse, {
    props: {
      filters: { province: 'all', period: 'all', topic: 'all' },
      stats: { total: 186, trend: 9.3, rangeLabel: '内蒙古' },
      news: [{ id: 'n-1', category: '政策', title: '储能规模化发展', publishedAt: '2026-07-23T09:00:00+08:00' }],
    },
  })

  await wrapper.get('[data-filter="province"]').setValue('内蒙古')
  await wrapper.get('[data-news-id="n-1"]').trigger('click')
  expect(wrapper.emitted('filters-change')?.[0]?.[0]).toMatchObject({ province: '内蒙古' })
  expect(wrapper.emitted('open-news')).toEqual([['n-1']])
})

it('资讯详情弹窗展示正文和来源', () => {
  const wrapper = mount(NewsDetailDialog, {
    props: {
      modelValue: true,
      news: { category: '政策', title: '储能规模化发展', publishedAt: '2026-07-23T09:00:00+08:00', content: '正文内容', source: '公开信息整理' },
    },
    global: { stubs: { ElDialog: { template: '<div><slot /></div>' } } },
  })

  expect(wrapper.text()).toContain('正文内容')
  expect(wrapper.text()).toContain('公开信息整理')
})
```

- [ ] **Step 2: 运行组件测试并确认新增用例失败**

Run: `cd agent-frontend && npm exec vitest -- run tests/policy-market-components.spec.js`

Expected: FAIL，原因是 `MarketPulse.vue` 与 `NewsDetailDialog.vue` 尚不存在。

- [ ] **Step 3: 实现 `MarketPulse.vue`**

组件 props：`filters`、`stats`、`news`、`loading`、`error`；emits：`filters-change`、`open-news`。

使用本地 `draftFilters`，由 `watch(() => props.filters, ...)` 同步。每个选择框变化时调用：

```js
function emitFilters() {
  emit('filters-change', { ...draftFilters })
}
```

提供以下固定下拉选项：

```js
const provinceOptions = ['all', '内蒙古', '山东', '江苏', '广东', '河北', '浙江']
const periodOptions = [
  { value: 'all', label: '全部时间' },
  { value: 'month', label: '本月' },
  { value: 'quarter', label: '近三个月' },
]
const topicOptions = [
  { value: 'all', label: '全部主题' },
  { value: '政策', label: '政策解读' },
  { value: '市场', label: '市场分析' },
  { value: '行业', label: '行业研究' },
]
```

三个原生 `<select>` 必须分别带 `data-filter="province"`、`data-filter="period"`、`data-filter="topic"`。统计区域用 `.xc-num` 展示 `stats.total`，趋势显示 `较上期 +${stats.trend}%`；当 `error` 非空时改为“统计加载失败”。

资讯列表按 `news` 渲染原生按钮，按钮带 `:data-news-id="item.id"` 和 `@click="$emit('open-news', item.id)"`。载入时显示“正在加载市场资讯”；失败时显示 `error`；成功但无数据时显示“暂无市场资讯”。底部固定显示“今日市场观察”及已确认的两条主线：电力市场化交易、新型储能。

- [ ] **Step 4: 实现 `NewsDetailDialog.vue`**

组件 props：`modelValue`（布尔）和 `news`（对象或 null）；emit `update:modelValue`。使用 Element Plus：

```vue
<el-dialog
  :model-value="modelValue"
  width="min(560px, calc(100vw - 32px))"
  :show-close="true"
  @update:model-value="$emit('update:modelValue', $event)"
>
  <template #header>
    <p class="pm-news-dialog__category">{{ news?.category || '市场资讯' }}</p>
    <h2>{{ news?.title || '资讯详情' }}</h2>
  </template>
  <time>{{ formatPublishedAt(news?.publishedAt) }}</time>
  <p>{{ news?.content || '暂无详情内容' }}</p>
  <footer>来源：{{ news?.source || '—' }}</footer>
</el-dialog>
```

`formatPublishedAt` 为空值返回 `—`，有效时间返回 `YYYY.MM.DD`。样式继续使用 XC Token，并为长正文加 `white-space: pre-wrap` 与 `overflow-wrap: anywhere`。

- [ ] **Step 5: 运行组件测试并确认通过**

Run: `cd agent-frontend && npm exec vitest -- run tests/policy-market-components.spec.js`

Expected: PASS，6 个测试通过。

### Task 5: 组装页面、路由和导航入口

**Files:**
- Create: `agent-frontend/src/views/policy-market/index.vue`
- Modify: `agent-frontend/src/router/index.js`
- Modify: `agent-frontend/src/layout/index.vue`
- Modify: `agent-frontend/src/layout/components/AppRail.vue`
- Create: `agent-frontend/tests/policy-market-page.spec.js`
- Modify: `agent-frontend/tests/app-rail.spec.js`

- [ ] **Step 1: 编写失败的路由、导航和页面布局测试**

创建 `agent-frontend/tests/policy-market-page.spec.js`：

```js
import { describe, expect, it } from 'vitest'
import router from '@/router'
import layoutSource from '@/layout/index.vue?raw'
import pageSource from '@/views/policy-market/index.vue?raw'

describe('政策与市场页面集成', () => {
  it('注册独立政策与市场路由，并隐藏通用测算会话侧栏', () => {
    const route = router.getRoutes().find((item) => item.path === '/policy-market')

    expect(route?.name).toBe('PolicyMarket')
    expect(route?.meta?.collapseSidebar).toBe(true)
    expect(layoutSource).toContain("'/policy-market': 'policy'")
  })

  it('使用三栏布局并在窄屏切换为单列', () => {
    expect(pageSource).toContain('grid-template-columns: 248px minmax(0, 1fr) 336px')
    expect(pageSource).toContain('@media (max-width: 1180px)')
    expect(pageSource).toContain('grid-template-columns: 1fr')
  })

  it('页面初始化加载数据，并把操作委托给 Store', () => {
    expect(pageSource).toContain('store.loadInitialData()')
    expect(pageSource).toContain('store.startNewConsultation()')
    expect(pageSource).toContain('store.submitQuestion(question)')
    expect(pageSource).toContain('store.setStatsFilters(filters)')
  })
})
```

将 `agent-frontend/tests/app-rail.spec.js` 的第二个测试预期更新为：第四项“政策与市场”不再具有 `is-disabled` 或 `disabled` 属性；第三个测试预期更新为 `[['home'], ['line'], ['policy']]`。

- [ ] **Step 2: 运行失败测试并确认当前状态不满足要求**

Run: `cd agent-frontend && npm exec vitest -- run tests/policy-market-page.spec.js tests/app-rail.spec.js`

Expected: FAIL，原因是路由、页面和导航尚未实现，且政策导航仍禁用。

- [ ] **Step 3: 注册路由与更新布局导航映射**

在 `agent-frontend/src/router/index.js` 的根布局 `children` 中，在 `tie-line` 路由后添加：

```js
{
  path: 'policy-market',
  name: 'PolicyMarket',
  component: () => import('@/views/policy-market/index.vue'),
  meta: { title: '政策与市场', collapseSidebar: true },
},
```

在 `agent-frontend/src/layout/index.vue` 同时完成以下两项：

```js
const RAIL_TO_PATH = { home: '/home', line: '/tie-line', policy: '/policy-market' }
const PATH_TO_RAIL = { '/home': 'home', '/tie-line': 'line', '/policy-market': 'policy' }
```

将历史会话展开按钮的显示条件从只排除 `TieLineMap` 调整为基于 `route.meta.collapseSidebar`，确保政策页也不会显示测算会话栏的展开按钮：

```vue
v-if="sidebarHidden && !route.meta.collapseSidebar"
```

- [ ] **Step 4: 启用 AppRail 中的政策与市场入口**

在 `agent-frontend/src/layout/components/AppRail.vue` 将默认项改为：

```js
{ key: 'policy', label: '政策与市场', icon: ICON.policy, disabled: false },
```

同步将该文件中的注释改为准确描述：全国指数地图仍为待建；联络线地图和政策与市场可访问。不要改动图标 SVG 或其他导航项。

- [ ] **Step 5: 实现 `views/policy-market/index.vue` 页面编排**

页面使用 `usePolicyMarketStore()`、`onMounted`、`ref`、`nextTick` 和 `ElMessage`。组件引用：`ConsultationHistory`、`ConsultationComposer`、`ConsultationResult`、`MarketPulse`、`NewsDetailDialog`。

初始化：

```js
onMounted(() => {
  store.loadInitialData()
})
```

事件处理：

```js
const composerRef = ref(null)
const dialogVisible = ref(false)
const selectedNewsId = ref(null)

const selectedNews = computed(() => store.news.find((item) => item.id === selectedNewsId.value) || null)

async function handleNewQuestion() {
  store.startNewConsultation()
  await nextTick()
  composerRef.value?.focus()
}

async function handleSubmit(question) {
  try {
    await store.submitQuestion(question)
  } catch (error) {
    ElMessage.error(error?.message || '咨询提交失败，请稍后重试')
  }
}

function handleOpenNews(id) {
  selectedNewsId.value = id
  dialogVisible.value = true
}
```

模板必须具备 `.policy-market-page` 容器及 `.policy-market-page__grid` 三栏网格；通过 props 和 emit 连接所有子组件。给页面加载和错误状态可见的 `aria-live="polite"` 区域，但不重复弹出后端模拟错误。

样式要求：

```css
.policy-market-page {
  min-height: 100%;
  padding: var(--xc-gutter-y) var(--xc-gutter-x);
  box-sizing: border-box;
}
.policy-market-page__grid {
  min-height: calc(100vh - 64px - (var(--xc-gutter-y) * 2));
  display: grid;
  grid-template-columns: 248px minmax(0, 1fr) 336px;
  gap: var(--xc-space-4);
}
@media (max-width: 1180px) {
  .policy-market-page__grid { grid-template-columns: 1fr; }
}
```

各栏使用 XC surface、border、radius、spacing Token；不硬编码 `#hex`、`rgb()`、外部字体或 CSS 渐变。中栏需设置 `min-width: 0`，窄屏时页面可纵向滚动，不得产生横向滚动。

- [ ] **Step 6: 运行路由、导航和页面布局测试并确认通过**

Run: `cd agent-frontend && npm exec vitest -- run tests/policy-market-page.spec.js tests/app-rail.spec.js`

Expected: PASS，政策与市场路由、布局规则和导航测试全部通过。

### Task 6: 完成测试回归、构建与文档同步

**Files:**
- Modify: `agent-frontend/docs/README.md` 或 `my_projects/investment-research-agent-项目开发指南.md` 中实际存在的前端章节
- Modify: 测试执行中暴露的上述政策与市场文件（仅为修正明确的失败）

- [ ] **Step 1: 读取当前权威前端开发文档并定位页面清单章节**

Run: `rg -n "联络线地图|路由|Pinia|src/views" agent-frontend/docs my_projects`

Expected: 找到实际维护前端路由、页面、Store 或 API 的权威文档段落。不要把新模块说明写入不相关的 README。

- [ ] **Step 2: 在权威文档中补充政策与市场模块条目**

补充以下事实：

```markdown
- 政策与市场：路由 `/policy-market`；前端入口为 `views/policy-market/index.vue`；通过 `store/modules/policyMarket.js` 协调咨询、资讯和统计；所有页面数据经 `api/policyMarket.js` 获取。当前 API 是模拟实现，后续数据库和咨询服务接入仅替换 API 请求及 DTO 映射。
```

说明该页面使用自身“我的提问”历史栏，不复用首页的测算会话侧栏。不要在文档中记录密钥、数据库连接、生产地址或未实现的接口路径。

- [ ] **Step 3: 运行完整前端测试套件**

Run: `cd agent-frontend && npm test`

Expected: PASS，所有既有测试和新增政策与市场测试通过。

- [ ] **Step 4: 执行生产构建**

Run: `cd agent-frontend && npm run build`

Expected: Exit code 0，Vite 完成生产构建，无 Vue 模板、导入或 CSS 编译错误。

- [ ] **Step 5: 检查最终差异，不执行 Git 写操作**

Run: `git diff --check && git status --short`

Expected: `git diff --check` 无输出；状态只包含本计划列出的前端、测试和文档文件。除非用户明确要求，不执行 `git add`、`git commit` 或 `git push`。

## 计划自检

- 规格覆盖：Task 1-2 实现占位 API、Store、数据库 DTO 边界和失败保留策略；Task 3 实现新建、历史、快捷提问、键盘提交、空值与回答状态；Task 4 实现统计筛选、资讯和弹窗；Task 5 实现三栏路由、导航、隐藏通用侧栏与响应式样式；Task 6 处理文档和完整验证。
- 一致性：API 方法、Store 字段、筛选参数和 DTO 命名均与设计规格一致，组件通过 Store 的公开动作协作。
- 范围：未规划后端、数据库、真实大模型、资讯采集、删除咨询、持久化、图表或新依赖。
- Git：项目指令禁止未经明确授权的 Git 写操作，故本计划用差异检查替代技能模板要求的提交步骤。

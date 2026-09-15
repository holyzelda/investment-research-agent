import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const state = vi.hoisted(() => {
  const route = { name: 'Home', path: '/home', fullPath: '/home', query: {}, meta: {} }
  return {
    route,
    router: { push: vi.fn().mockResolvedValue(undefined), currentRoute: { value: route } },
    session: { username: 'researcher', nickname: '研究员', loadUserInfo: vi.fn() },
    calc: {},
    message: { error: vi.fn(), success: vi.fn() },
  }
})

vi.mock('@/store/modules/trialQuota', () => ({
  useTrialQuotaStore: () => ({ isTrial: false, quota: null, load: vi.fn(), refresh: vi.fn() }),
}))

vi.mock('vue-router', async () => {
  const { reactive } = await import('vue')
  state.route = reactive(state.route)
  return { useRoute: () => state.route, useRouter: () => state.router }
})

vi.mock('element-plus', () => ({
  ElMessage: state.message,
  ElMessageBox: { confirm: vi.fn(), prompt: vi.fn() },
}))

vi.mock('@/store/modules/session', () => ({ useSessionStore: () => state.session }))
vi.mock('@/store/modules/calculation', () => ({ useCalculationStore: () => state.calc }))
vi.mock('@/api/calc', () => ({ getPlatformStats: vi.fn().mockResolvedValue({ data: {} }) }))

import Home from '@/views/home/index.vue'

const stubs = {
  ResultCard: true,
  ChatComposer: true,
  ThinkingChain: true,
  AiAnswerContent: true,
  ReportGenerationCard: true,
  ShareDialog: true,
  teleport: true,
}

// 各用例共用同一个响应式 route，未卸载的旧组件会继续响应 query 变化并污染断言
const mounted = []

const mountHome = () => {
  const wrapper = mount(Home, { global: { stubs } })
  mounted.push(wrapper)
  return wrapper
}

function makeCalc(overrides = {}) {
  return {
    messages: [],
    versions: [],
    reports: [],
    reportTasks: {},
    selectedVersion: null,
    latestVersion: null,
    conversationId: null,
    responding: false,
    conversationLoading: false,
    conversationLoadingId: null,
    conversationLoadError: '',
    comparisonVersionByVersion: {},
    openConversation: vi.fn().mockResolvedValue(undefined),
    selectVersion: vi.fn(),
    stopStream: vi.fn(),
    sendAndCalculate: vi.fn().mockResolvedValue(undefined),
    disposeReportStreams: vi.fn(),
    disposeActiveTurn: vi.fn(),
    generateReport: vi.fn().mockResolvedValue(undefined),
    comparisonVersionFor: vi.fn(() => null),
    setComparisonVersion: vi.fn(),
    ...overrides,
  }
}

describe('Home route-owned history loading', () => {
  beforeEach(() => {
    state.route.name = 'Home'
    state.route.path = '/home'
    state.route.fullPath = '/home'
    state.route.query = {}
    state.route.meta = {}
    state.calc = makeCalc()
    vi.clearAllMocks()
  })

  afterEach(() => {
    while (mounted.length) mounted.pop().unmount()
  })

  it('opens the routed conversation immediately on first load', async () => {
    state.route.query = { conversationId: '7' }
    mountHome()
    await flushPromises()

    expect(state.calc.openConversation).toHaveBeenCalledWith('7', null)
  })

  it('does not open any conversation when the Home query is empty', async () => {
    mountHome()
    await flushPromises()

    expect(state.calc.openConversation).not.toHaveBeenCalled()
  })

  it('reopens when the query changes while Home stays mounted', async () => {
    state.route.query = { conversationId: '7' }
    mountHome()
    await flushPromises()

    state.route.query = { conversationId: '8' }
    await flushPromises()

    expect(state.calc.openConversation).toHaveBeenNthCalledWith(1, '7', null)
    expect(state.calc.openConversation).toHaveBeenNthCalledWith(2, '8', null)
  })

  it('passes the deep-linked taskId through to the store', async () => {
    state.route.query = { conversationId: '7', taskId: '11' }
    mountHome()
    await flushPromises()

    expect(state.calc.openConversation).toHaveBeenCalledWith('7', '11')
  })

  it('skips reopening when the routed conversation and version are already selected', async () => {
    state.calc = makeCalc({
      conversationId: '7',
      versions: [{ taskId: 11, version: 'V1', result: {} }],
      selectedVersion: 'V1',
    })
    state.route.query = { conversationId: '7', taskId: '11' }
    mountHome()
    await flushPromises()

    expect(state.calc.openConversation).not.toHaveBeenCalled()
  })

  it('shows the loading state instead of the welcome view while history loads', async () => {
    state.calc = makeCalc({ conversationLoading: true, conversationLoadingId: '7' })
    state.route.query = { conversationId: '7' }
    const wrapper = mountHome()
    await flushPromises()

    expect(wrapper.find('.ir-home__history-state').exists()).toBe(true)
    expect(wrapper.text()).toContain('正在加载历史会话')
    expect(wrapper.find('.ir-welcome').exists()).toBe(false)
  })

  it('shows a retryable error state instead of the welcome view when loading fails', async () => {
    state.calc = makeCalc({
      conversationLoadError: '历史会话加载失败',
      openConversation: vi.fn().mockRejectedValue(new Error('boom')),
    })
    state.route.query = { conversationId: '7' }
    const wrapper = mountHome()
    await flushPromises()

    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    expect(wrapper.find('.ir-welcome').exists()).toBe(false)

    await wrapper.find('.ir-home__history-state button').trigger('click')
    await flushPromises()

    expect(state.calc.openConversation).toHaveBeenCalledTimes(2)
  })

  it('does not surface an error for a route the user already navigated away from', async () => {
    const rejecters = new Map()
    state.calc = makeCalc({
      openConversation: vi.fn((conversationId) => new Promise((_resolve, reject) => {
        rejecters.set(String(conversationId), reject)
      })),
    })
    state.route.query = { conversationId: '7' }
    mountHome()
    await flushPromises()

    state.route.query = { conversationId: '8' }
    await flushPromises()

    // 旧会话 7 的请求在用户已切到 8 之后才失败，不应弹出错误提示
    rejecters.get('7')(new Error('stale'))
    await flushPromises()

    expect(state.calc.openConversation.mock.calls.map((call) => call[0])).toEqual(['7', '8'])
    expect(state.message.error).not.toHaveBeenCalled()
  })
})

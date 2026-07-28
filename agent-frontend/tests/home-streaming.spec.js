import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

const api = vi.hoisted(() => ({
  createCalculationTask: vi.fn(),
  deleteConversation: vi.fn(),
  getCalculationResult: vi.fn(),
  getCalculationTask: vi.fn(),
  getConversation: vi.fn(),
  getParamDict: vi.fn(),
  getStations: vi.fn(),
  listConversations: vi.fn(),
  renameConversation: vi.fn(),
}))
const chat = vi.hoisted(() => ({ openChatStream: vi.fn() }))

vi.mock('@/api/calc', () => api)
vi.mock('@/api/report', () => ({ createReport: vi.fn(), getReportTask: vi.fn() }))
vi.mock('@/utils/reportSse', () => ({ streamReportEvents: vi.fn() }))
vi.mock('@/utils/chatSse', () => chat)
vi.mock('@/store/modules/session', () => ({
  useSessionStore: () => ({ username: 'admin' }),
}))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('@/views/home/components/ChatComposer.vue', () => ({
  default: { template: '<div class="composer-stub" />' },
}))
vi.mock('@/views/home/components/ResultCard.vue', () => ({
  default: { template: '<div class="result-card-stub" />' },
}))

import { useCalculationStore } from '@/store/modules/calculation'
import Home from '@/views/home/index.vue'

let handlers

describe('home thinking stream rendering', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.stubGlobal('requestAnimationFrame', (callback) => setTimeout(callback, 0))
    vi.stubGlobal('cancelAnimationFrame', (handle) => clearTimeout(handle))
    chat.openChatStream.mockImplementation((_path, _body, options) => {
      handlers = options
      return { close: vi.fn() }
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders thinking node and token updates before done', async () => {
    const store = useCalculationStore()
    const wrapper = mount(Home)
    const pending = store.sendAndCalculate('分析项目')
    await nextTick()

    handlers.onEvent({
      type: 'thinking',
      id: '1',
      data: {
        data: {
          node_id: 'n1',
          node_seq: 1,
          node_status: 'active',
          node_title: '识别项目参数',
        },
      },
    })
    handlers.onEvent({
      type: 'thinking',
      id: '2',
      data: { data: { node_id: 'n1', text: '正在读取省份' } },
    })
    await nextTick()

    expect(store.responding).toBe(true)
    expect(wrapper.find('.ir-node__title').text()).toContain('识别项目参数')
    expect(wrapper.find('.ir-node__text').text()).toBe('正在读取省份')

    handlers.onEvent({
      type: 'thinking',
      id: '3',
      data: { data: { node_id: 'n1', text: '和装机规模' } },
    })
    await nextTick()

    expect(wrapper.find('.ir-node__text').text()).toBe('正在读取省份和装机规模')

    handlers.onEvent({ type: 'done', id: '4', data: { data: {} } })
    await pending
    wrapper.unmount()
  })
})

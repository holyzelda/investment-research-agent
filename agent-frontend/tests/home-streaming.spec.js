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
  default: { template: '<button class="composer-stub" @click="$emit(\'send\', \'第二次测算\')" />' },
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

  it('renders assistant Markdown while keeping user text literal and thinking separate', async () => {
    const store = useCalculationStore()
    store.messages = [
      { id: 'u1', role: 'user', kind: 'text', text: '**用户原文**' },
      {
        id: 'a1',
        role: 'assistant',
        kind: 'assistant-stream',
        phase: 'complete',
        startedAt: 1,
        finishedAt: 2,
        hasThinkingStarted: true,
        thinkingState: {
          order: ['n1'],
          nodesById: { n1: { nodeId: 'n1', title: '识别项目参数', status: 'completed', open: false, substeps: [], text: '' } },
        },
        answerText: '**投资结论**\n\n| 指标 | 数值 |\n| --- | --- |\n| IRR | 8.6% |',
        recommendedQuestions: [],
      },
    ]
    const wrapper = mount(Home)
    await nextTick()

    expect(wrapper.find('.ir-msg--user strong').exists()).toBe(false)
    expect(wrapper.find('.ir-msg--user').text()).toContain('**用户原文**')
    const stream = wrapper.find('.ir-msg__stream')
    expect(stream.find('.ir-thinking').exists()).toBe(true)
    expect(stream.find('.ir-ai-answer strong').text()).toBe('投资结论')
    expect(stream.find('.ir-ai-answer table').exists()).toBe(true)
    expect(stream.find('.ir-thinking').element.parentElement).toBe(stream.element)
    expect(stream.find('.ir-ai-answer').element.parentElement).toBe(stream.element)
    wrapper.unmount()
  })

  it('keeps report thinking visible above the richer delivery card', async () => {
    const store = useCalculationStore()
    store.versions = [{
      taskId: 42,
      version: 'V2',
      input: { province: '甘肃', node_name: '祥泰站', power_mw: 100, capacity_mwh: 400 },
      result: { basicInfo: { province: '甘肃', nodeName: '祥泰站', powerMw: 100, capacityMwh: 400 } },
    }]
    store.messages = [{
      id: 'report-1',
      role: 'assistant',
      kind: 'assistant-stream',
      flow: 'report',
      taskId: 42,
      reportId: 'r-2',
      phase: 'completed',
      startedAt: 1,
      finishedAt: 2,
      hasThinkingStarted: true,
      thinkingState: {
        order: ['report:prepare'],
        nodesById: {
          'report:prepare': { nodeId: 'report:prepare', title: '读取冻结测算快照', status: 'completed', open: false, substeps: [], text: '' },
        },
      },
      answerText: '正式报告已生成，可查看完整报告。',
      recommendedQuestions: [],
    }]

    const wrapper = mount(Home)
    await nextTick()

    const streamMessage = wrapper.find('.ir-msg__stream')
    expect(streamMessage.find('.ir-thinking').exists()).toBe(true)
    expect(streamMessage.find('.ir-report-delivery').exists()).toBe(true)
    expect(streamMessage.find('.ir-ai-answer').exists()).toBe(false)
    expect(streamMessage.text()).toContain('甘肃 · 祥泰站储能项目')
    expect(streamMessage.text()).toContain('V2')
    wrapper.unmount()
  })

  it('keeps historical report delivery on the same full-width assistant track', async () => {
    const store = useCalculationStore()
    store.versions = [{
      taskId: 42,
      version: 'V2',
      input: { province: '甘肃', node_name: '祥泰站', power_mw: 100, capacity_mwh: 400 },
    }]
    store.messages = [{
      id: 'report-history-1',
      role: 'assistant',
      kind: 'report-generated',
      payload: { report_id: 'r-2', task_id: 42 },
    }]

    const wrapper = mount(Home)
    await nextTick()

    const message = wrapper.find('.ir-msg--assistant')
    expect(message.find('.ir-msg__stream').exists()).toBe(true)
    expect(message.find('.ir-report-delivery').exists()).toBe(true)
    expect(message.find('.ir-report-delivery').element.parentElement).toBe(message.find('.ir-msg__stream').element)
    wrapper.unmount()
  })

  it('renders historical assistant text as Markdown without parsing user text', async () => {
    const store = useCalculationStore()
    store.messages = [
      { id: 'u1', role: 'user', kind: 'text', text: '<b>用户原文</b>' },
      { id: 'a1', role: 'assistant', kind: 'text', text: '## 历史结论\n\n| 版本 | IRR |\n| --- | --- |\n| V1 | 8.6% |' },
    ]
    const wrapper = mount(Home)
    await nextTick()

    expect(wrapper.find('.ir-msg--user b').exists()).toBe(false)
    expect(wrapper.find('.ir-msg--user').text()).toContain('<b>用户原文</b>')
    expect(wrapper.find('.ir-msg--assistant h2').text()).toBe('历史结论')
    expect(wrapper.find('.ir-msg--assistant table').exists()).toBe(true)
    wrapper.unmount()
  })

  it('follows the latest response to the real bottom while streaming', async () => {
    const frames = []
    vi.stubGlobal('requestAnimationFrame', (callback) => {
      frames.push(callback)
      return frames.length
    })
    vi.stubGlobal('cancelAnimationFrame', vi.fn())

    const store = useCalculationStore()
    store.messages = [
      { id: 'old-user', role: 'user', kind: 'text', text: '第一次测算' },
      { id: 'old-answer', role: 'assistant', kind: 'text', text: '第一次测算结果' },
    ]
    const wrapper = mount(Home)
    await wrapper.find('.composer-stub').trigger('click')
    await nextTick()
    const pending = Promise.resolve()

    const rows = wrapper.findAll('.ir-home__stream > .ir-msg')
    expect(rows.slice(0, 3).map((row) => row.text())).toEqual([
      '第一次测算',
      '第一次测算结果',
      '第二次测算',
    ])
    expect(rows[3].find('.ir-msg__stream').exists()).toBe(true)

    const stream = wrapper.find('.ir-home__stream').element
    const currentPrompt = rows[2].element
    let scrollHeight = 1500
    Object.defineProperties(stream, {
      clientHeight: { configurable: true, value: 500 },
      scrollHeight: { configurable: true, get: () => scrollHeight },
      scrollTop: { configurable: true, writable: true, value: 400 },
    })
    stream.getBoundingClientRect = () => ({ top: 100, bottom: 600 })
    currentPrompt.getBoundingClientRect = () => ({
      top: 700 - stream.scrollTop,
      bottom: 740 - stream.scrollTop,
    })

    frames.shift()?.()
    expect(stream.scrollTop).toBe(1000)

    stream.scrollTop = 700
    frames.shift()?.()
    expect(stream.scrollTop).toBe(1000)

    scrollHeight = 650
    frames.shift()?.()
    expect(stream.scrollTop).toBe(150)

    handlers.onEvent({ type: 'done', id: '1', data: { data: {} } })
    await pending
    wrapper.unmount()
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

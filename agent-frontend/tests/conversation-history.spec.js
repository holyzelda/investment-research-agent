import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { useCalculationStore } from '@/store/modules/calculation'
import AppSidebar from '@/layout/components/AppSidebar.vue'

const api = vi.hoisted(() => ({
  createCalculationTask: vi.fn(),
  getCalculationTask: vi.fn(),
  getCalculationResult: vi.fn(),
  listConversations: vi.fn(),
  getConversation: vi.fn(),
  deleteConversation: vi.fn(),
  renameConversation: vi.fn(),
}))

const chat = vi.hoisted(() => ({ openChatStream: vi.fn() }))

vi.mock('@/api/calc', () => api)
vi.mock('@/utils/chatSse', () => chat)

const detail = {
  conversationId: 7,
  title: '甘肃 200MW/800MWh',
  messages: [
    { role: 'user', content: '测算甘肃 200MW/800MWh', createdAt: '2026-07-15T09:00:00' },
    { role: 'assistant', content: 'V1 测算完成', createdAt: '2026-07-15T09:01:00' },
    { role: 'user', content: '再算一次', createdAt: '2026-07-15T09:02:00' },
    { role: 'assistant', content: 'V2 测算完成', createdAt: '2026-07-15T09:03:00' },
  ],
  versions: [
    { taskId: 11, version: 'V1', status: 'completed', result: { basicInfo: { province: '甘肃' }, financial: { capitalIrr: 8 } } },
    { taskId: 12, version: 'V2', status: 'completed', result: { basicInfo: { province: '甘肃' }, financial: { capitalIrr: 9 } } },
  ],
}

describe('conversation history sidebar and replay', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('renders module navigation before conversation history in the unified shell', () => {
    const store = useCalculationStore()
    store.history = [
      { conversationId: 7, title: '甘肃 200MW/800MWh', latestVersion: 'V2' },
      { conversationId: 6, title: '宁夏 100MW/400MWh', latestVersion: 'V1' },
    ]
    const wrapper = mount(AppSidebar, {
      props: { history: store.history },
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.text()).toContain('朱雀投研智能体')
    expect(wrapper.text()).toContain('新建会话')
    expect(wrapper.text()).toContain('投资分析工作台')
    expect(wrapper.text()).toContain('历史测算')
    const nav = wrapper.find('.ir-shell__nav')
    const history = wrapper.find('.ir-shell__history')
    expect(nav.element.compareDocumentPosition(history.element) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    const histTitles = wrapper.findAll('.ir-shell__history-name').map((n) => n.text())
    expect(histTitles).toEqual(['甘肃 200MW/800MWh', '宁夏 100MW/400MWh'])
  })

  it('marks the currently open conversation as active in the history list', () => {
    const wrapper = mount(AppSidebar, {
      props: {
        history: [
          { conversationId: 7, title: '甘肃 200MW/800MWh', latestVersion: 'V2' },
          { conversationId: 6, title: '宁夏 100MW/400MWh', latestVersion: 'V1' },
        ],
        current: 6,
      },
      global: { stubs: { teleport: true } },
    })

    const items = wrapper.findAll('.ir-shell__history-item')
    expect(items[0].classes()).not.toContain('is-current')
    expect(items[1].classes()).toContain('is-current')
  })

  it('emits open-history when a history item is clicked', async () => {
    const wrapper = mount(AppSidebar, {
      props: { history: [{ conversationId: 7, title: '甘肃 200MW/800MWh', latestVersion: 'V2' }] },
      global: { stubs: { teleport: true } },
    })

    await wrapper.find('.ir-shell__history-item').trigger('click')

    expect(wrapper.emitted('open-history')[0]).toEqual([7])
  })

  it('emits delete-history from the hover delete icon without triggering open', async () => {
    const wrapper = mount(AppSidebar, {
      props: { history: [{ conversationId: 7, title: '甘肃 200MW/800MWh', latestVersion: 'V2' }] },
      global: { stubs: { teleport: true } },
    })

    await wrapper.find('.ir-shell__history-delete').trigger('click')

    expect(wrapper.emitted('delete-history')[0]).toEqual([7])
    expect(wrapper.emitted('open-history')).toBeUndefined()
  })

  it('emits rename-history with the conversation from the hover edit icon', async () => {
    const conversation = { conversationId: 7, title: '甘肃 200MW/800MWh', latestVersion: 'V2' }
    const wrapper = mount(AppSidebar, {
      props: { history: [conversation] },
      global: { stubs: { teleport: true } },
    })

    await wrapper.find('.ir-shell__history-edit').trigger('click')

    expect(wrapper.emitted('rename-history')[0]).toEqual([conversation])
    expect(wrapper.emitted('open-history')).toBeUndefined()
  })

  it('renameConversation patches the trimmed title and updates history in place', async () => {
    api.renameConversation.mockResolvedValue({ data: { conversationId: 7, title: '甘肃复核' } })
    const store = useCalculationStore()
    store.history = [
      { conversationId: 7, title: '甘肃' },
      { conversationId: 6, title: '宁夏' },
    ]

    await store.renameConversation(7, '  甘肃复核  ')

    expect(api.renameConversation).toHaveBeenCalledWith(7, '甘肃复核')
    expect(store.history.find((h) => h.conversationId === 7).title).toBe('甘肃复核')
    expect(store.history.find((h) => h.conversationId === 6).title).toBe('宁夏')
  })

  it('loadHistory stores the current user conversation list', async () => {
    api.listConversations.mockResolvedValue({ data: { items: [
      { conversationId: 7, title: '甘肃 200MW/800MWh', latestVersion: 'V2', latestStatus: 'completed' },
    ] } })
    const store = useCalculationStore()

    await store.loadHistory()

    expect(store.history).toHaveLength(1)
    expect(store.history[0].conversationId).toBe(7)
  })

  it('openConversation replays messages and versions without calling calc APIs', async () => {
    api.getConversation.mockResolvedValue({ data: detail })
    const store = useCalculationStore()

    await store.openConversation(7)

    expect(api.createCalculationTask).not.toHaveBeenCalled()
    expect(api.getCalculationResult).not.toHaveBeenCalled()
    expect(store.conversationId).toBe(7)
    expect(store.messages.map((m) => m.kind)).toEqual(['text', 'result', 'text', 'result'])
    expect(store.messages[1].version).toBe('V1')
    expect(store.messages[1].result.basicInfo.province).toBe('甘肃')
    expect(store.versions.map((v) => v.version)).toEqual(['V1', 'V2'])
    expect(store.selectedVersion).toBe('V2')
  })

  it('openConversation preserves historical report payload and metadata without restarting generation', async () => {
    api.getConversation.mockResolvedValue({ data: {
      conversationId: 7,
      messages: [
        { role: 'assistant', content: 'V1 测算完成' },
        { role: 'assistant', messageType: 'report_generated', content: '正式报告已生成', payload: { report_id: 'r-1', task_id: 11 } },
      ],
      versions: [{
        taskId: 11,
        version: 'V1',
        status: 'completed',
        input: { province: '甘肃', power_mw: 200, capacity_mwh: 800 },
        result: { basicInfo: { province: '甘肃', powerMw: 200, capacityMwh: 800 } },
        report: { reportId: 'r-1', taskId: 11, version: 'V1', status: 'completed', title: '甘肃储能项目投资报告' },
      }],
      reports: [{ reportId: 'r-1', taskId: 11, version: 'V1', status: 'completed', title: '甘肃储能项目投资报告' }],
    } })
    const store = useCalculationStore()

    await store.openConversation(7)

    expect(store.messages.map((message) => message.kind)).toEqual(['result', 'report-generated'])
    expect(store.messages[1].payload).toEqual({ report_id: 'r-1', task_id: 11 })
    expect(store.reports[0]).toMatchObject({ reportId: 'r-1', title: '甘肃储能项目投资报告' })
    expect(api.createCalculationTask).not.toHaveBeenCalled()
  })

  it('replayed conversation keeps its id for the next calculation', async () => {
    api.getConversation.mockResolvedValue({ data: detail })
    let handlers
    chat.openChatStream.mockImplementation((_path, _body, options) => {
      handlers = options
      return { close: vi.fn() }
    })
    const store = useCalculationStore()

    await store.openConversation(7)
    const next = store.sendAndCalculate('测算甘肃 300MW/600MWh')

    expect(chat.openChatStream).toHaveBeenCalledWith(
      '/ir/chat/diag',
      { message: '测算甘肃 300MW/600MWh', conversation_id: 7 },
      expect.any(Object),
    )
    handlers.onEvent({ type: 'done', id: '1', data: { data: {} } })
    await next
    expect(store.versions.map((v) => v.version)).toEqual(['V1', 'V2'])
  })

  it('removeConversation soft-deletes and drops it from history', async () => {
    api.deleteConversation.mockResolvedValue({ data: { conversationId: 7, deleted: true } })
    const store = useCalculationStore()
    store.history = [
      { conversationId: 7, title: '甘肃' },
      { conversationId: 6, title: '宁夏' },
    ]
    store.conversationId = 7

    await store.removeConversation(7)

    expect(api.deleteConversation).toHaveBeenCalledWith(7)
    expect(store.history.map((h) => h.conversationId)).toEqual([6])
    expect(store.conversationId).toBeNull()
  })
})

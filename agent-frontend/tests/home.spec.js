import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const api = vi.hoisted(() => ({
  createCalculationTask: vi.fn(), deleteConversation: vi.fn(), getCalculationResult: vi.fn(),
  getCalculationTask: vi.fn(), getConversation: vi.fn(), getParamDict: vi.fn(), getStations: vi.fn(),
  listConversations: vi.fn(), renameConversation: vi.fn(),
}))
const chat = vi.hoisted(() => ({ openChatStream: vi.fn() }))
vi.mock('@/api/calc', () => api)
vi.mock('@/utils/chatSse', () => chat)
vi.mock('@/api/report', () => ({ createReport: vi.fn(), getReportTask: vi.fn() }))
vi.mock('@/utils/reportSse', () => ({ streamReportEvents: vi.fn() }))

import { useCalculationStore } from '@/store/modules/calculation'

describe('home conversation input', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('sends any non-empty user text unchanged to the chat stream', async () => {
    let handlers
    chat.openChatStream.mockImplementation((_path, _body, options) => {
      handlers = options
      return { close: vi.fn() }
    })
    const store = useCalculationStore()
    const sent = store.sendAndCalculate('  测算甘肃储能项目  ')

    expect(chat.openChatStream).toHaveBeenCalledWith(
      '/ir/chat/diag',
      { message: '测算甘肃储能项目', conversation_id: undefined },
      expect.any(Object),
    )
    handlers.onEvent({ type: 'done', id: '1', data: { data: {} } })
    await sent
  })

  it('ignores blank input', async () => {
    const store = useCalculationStore()
    await store.sendAndCalculate('   ')
    expect(chat.openChatStream).not.toHaveBeenCalled()
    expect(store.messages).toEqual([])
  })
})

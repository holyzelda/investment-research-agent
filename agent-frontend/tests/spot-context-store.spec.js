import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const spotApi = vi.hoisted(() => ({
  prepareSpotContext: vi.fn(),
  removeSpotContext: vi.fn(),
  downloadSpotContextTemplate: vi.fn(),
}))
const chat = vi.hoisted(() => ({ openChatStream: vi.fn() }))

vi.mock('@/api/spotContext', () => spotApi)
vi.mock('@/utils/chatSse', () => chat)
vi.mock('@/api/calc', () => ({
  createCalculationTask: vi.fn(), deleteConversation: vi.fn(), getCalculationResult: vi.fn(),
  getCalculationInputs: vi.fn(), getCalculationTask: vi.fn(), getConversation: vi.fn(),
  getParamDict: vi.fn(), getStations: vi.fn(), listConversations: vi.fn(), renameConversation: vi.fn(),
}))
vi.mock('@/api/report', () => ({ createReport: vi.fn(), getReportTask: vi.fn() }))
vi.mock('@/utils/reportSse', () => ({ streamReportEvents: vi.fn() }))

import { useCalculationStore } from '@/store/modules/calculation'

describe('conversation spot context store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('uploads before the first message and sends the staged token to chat', async () => {
    const context = {
      contextToken: 'context-token-1234567890', status: 'ready', fileName: 'spot.xlsx',
      startDate: '2025-01-01', endDate: '2025-12-31', validDays: 365,
    }
    spotApi.prepareSpotContext.mockResolvedValue({ data: context })
    let handlers
    chat.openChatStream.mockImplementation((_path, _body, options) => {
      handlers = options
      return { close: vi.fn() }
    })
    const store = useCalculationStore()

    await store.uploadSpotContext(new File(['xlsx'], 'spot.xlsx'))
    const sent = store.sendAndCalculate('测算山西 100MW/200MWh')

    expect(spotApi.prepareSpotContext).toHaveBeenCalledWith(
      expect.any(File), null, expect.any(AbortSignal),
    )
    expect(chat.openChatStream).toHaveBeenCalledWith(
      '/ir/chat/diag',
      {
        message: '测算山西 100MW/200MWh',
        conversation_id: undefined,
        spot_context_token: 'context-token-1234567890',
      },
      expect.any(Object),
    )
    handlers.onOpen({ conversationId: 'conversation-1' })
    handlers.onEvent({ type: 'done', id: '1', data: { data: {} } })
    await sent
    expect(store.conversationId).toBe('conversation-1')
    expect(store.spotContextToken).toBeNull()
  })

  it('restores a bound context from conversation detail', () => {
    const store = useCalculationStore()
    const context = { status: 'ready', fileName: 'history.xlsx', validDays: 360 }

    store._applyConversationDetail({
      conversationId: 'conversation-1', messages: [], versions: [], spotContext: context,
    }, 'conversation-1')

    expect(store.spotContext).toEqual(context)
    expect(store.spotContextToken).toBeNull()
  })
})

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
      expect.any(File), null, expect.any(AbortSignal), expect.objectContaining({ priceMode: 'both' }),
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

  it('keeps real upload and validation progress until the request finishes', async () => {
    let options
    let resolveUpload
    spotApi.prepareSpotContext.mockImplementation((_file, _conversationId, _signal, callbacks) => {
      options = callbacks
      return new Promise((resolve) => { resolveUpload = resolve })
    })
    const store = useCalculationStore()
    const upload = store.uploadSpotContext(new File(['xlsx'], '2025年度现货电价.xlsx'))

    options.onUploadProgress({ loaded: 50, total: 100 })
    expect(store.spotContextProgress).toMatchObject({
      phase: 'uploading', fileName: '2025年度现货电价.xlsx', uploadPercent: 50,
    })

    options.onProgress({ phase: 'validating', message: '正在读取并校验 Excel 数据' })
      options.onProgress({ phase: 'saving', message: '正在准备本会话电价' })
      expect(store.spotContextProgress).toMatchObject({
        phase: 'saving', fileName: '2025年度现货电价.xlsx',
      })

    resolveUpload({ data: { status: 'ready', contextToken: 'context-token-1234567890' } })
    await upload
    expect(store.spotContextUploading).toBe(false)
    expect(store.spotContextProgress).toBeNull()
  })

  it('allows retrying after an upload fails', async () => {
    spotApi.prepareSpotContext.mockRejectedValue(new Error('表头不匹配'))
    const store = useCalculationStore()

    await expect(store.uploadSpotContext(new File(['xlsx'], '错误文件.xlsx'))).rejects.toThrow('表头不匹配')
    expect(store.spotContextError).toBe('表头不匹配')
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

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick, watch } from 'vue'

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

import { useCalculationStore } from '@/store/modules/calculation'

const result = {
  version: 'V1',
  calculatedAt: '2026-07-28T10:00:00Z',
  basicInfo: { province: '甘肃', powerMw: 200, capacityMwh: 800 },
  financial: { capitalIrr: 8.6 },
  advanced: {},
}

let handlers
let close
function installStream() {
  close = vi.fn()
  chat.openChatStream.mockImplementation((_path, _body, opts) => {
    handlers = opts
    return { close }
  })
}

function answerEvent(answer, biz = []) {
  handlers.onEvent({ type: 'answer', id: '2', data: { data: { answer, biz } } })
}

async function flush() {
  await Promise.resolve()
  await Promise.resolve()
}

describe('calculation chat stream flow', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    setActivePinia(createPinia())
    vi.clearAllMocks()
    installStream()
    api.getCalculationResult.mockResolvedValue({ data: result })
    api.listConversations.mockResolvedValue({ data: { items: [] } })
    api.getParamDict.mockResolvedValue({ data: { parameters: [], switches: {} } })
    api.getStations.mockResolvedValue({ data: { items: [] } })
  })

  afterEach(() => {
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
  })

  it('publishes each thinking frame reactively before done', async () => {
    const store = useCalculationStore()
    const observedText = []
    const stopWatching = watch(
      () => store.messages.at(-1)?.thinkingState?.nodesById?.n1?.text || '',
      (text) => observedText.push(text),
    )
    const promise = store.sendAndCalculate('开始分析')

    handlers.onEvent({
      type: 'thinking', id: '1',
      data: { data: { node_id: 'n1', node_status: 'active', node_title: '识别需求' } },
    })
    handlers.onEvent({
      type: 'thinking', id: '2',
      data: { data: { node_id: 'n1', text: '正在提取参数' } },
    })
    await nextTick()

    const message = store.messages.at(-1)
    expect(message.doneReceived).toBe(false)
    expect(message.thinkingState.nodesById.n1.text).toBe('正在提取参数')
    expect(observedText).toContain('正在提取参数')
    expect(store.responding).toBe(true)

    handlers.onEvent({
      type: 'thinking', id: '3',
      data: { data: { node_id: 'n1', text: '，正在校验' } },
    })
    await nextTick()
    expect(observedText).toContain('正在提取参数，正在校验')

    handlers.onEvent({ type: 'done', id: '4', data: { data: {} } })
    await promise
    stopWatching()
  })

  it('buffers answer until done and shows result without waiting for typing', async () => {
    const store = useCalculationStore()
    const promise = store.sendAndCalculate('测算甘肃 200MW/800MWh')
    handlers.onOpen({ conversationId: 'c1' })
    handlers.onEvent({
      type: 'thinking', id: '1',
      data: { data: { node_id: 'n1', node_status: 'active', node_title: '测算' } },
    })
    const biz = [{
      tool: 'create_calculation_task',
      payload: { data: { conversationId: 'c1', taskId: 't1', version: 'V1', status: 'completed', input: { province: '甘肃' } } },
    }]
    answerEvent('测算完成。', biz)
    answerEvent('', biz)
    handlers.onEvent({ type: 'recommended_questions', id: '3', data: { data: { recommended_questions: ['继续调整吗？'] } } })
    await flush()

    const message = store.messages.at(-1)
    expect(message.answerText).toBe('')
    expect(api.getCalculationResult).toHaveBeenCalledTimes(1)
    expect(message.result).toBeNull()

    handlers.onEvent({ type: 'done', id: '4', data: { data: { reason: 'normal' } } })
    await promise
    await flush()

    expect(message.result).toEqual(result)
    expect(store.versions).toHaveLength(1)
    expect(message.answerText).toBe('')
    expect(message.recommendedQuestions).toEqual([])
    expect(store.responding).toBe(true)

    await vi.runAllTimersAsync()
    expect(message.answerText).toBe('测算完成。')
    expect(message.recommendedQuestions).toEqual(['继续调整吗？'])
    expect(store.responding).toBe(false)
  })

  it.each([
    {
      name: 'a rejected calculation without a task',
      data: {
        conversationId: 'c1', taskId: null, status: 'failed', taskCreated: false,
        requestId: 'req-province',
        error: { code: 400, message: '省份在当前会话中不可修改，请新建会话后重新测算', requestId: 'req-province' },
      },
    },
    {
      name: 'a persisted CalcError task',
      data: {
        conversationId: 'c1', taskId: 153, status: 'failed', taskCreated: true,
        requestId: 'req-failed',
        error: { code: 'calculation_unavailable', message: '测算服务暂时不可用，请稍后重试', requestId: 'req-failed' },
      },
    },
  ])('shows $name returned by the calculation tool', async ({ data }) => {
    const store = useCalculationStore()
    const promise = store.sendAndCalculate('开始测算')
    handlers.onOpen({ conversationId: 'c1' })

    answerEvent('', [{
      tool: 'create_calculation_task',
      payload: { code: 200, msg: 'success', data },
    }])
    await promise
    await flush()

    const message = store.messages.at(-1)
    expect(message.phase).toBe('error')
    expect(message.done).toBe(true)
    expect(message.answerText).toContain(data.error.message)
    expect(message.answerText).not.toContain('request_id')
    expect(message.answerText).not.toContain(data.error.requestId)
    expect(store.versions).toEqual([])
    expect(api.getCalculationResult).not.toHaveBeenCalled()

    handlers.onEvent({ type: 'done', id: '3', data: { data: {} } })
    handlers.onComplete({ reason: 'eof' })
    expect(message.phase).toBe('error')
    expect(message.answerText).toContain(data.error.message)
  })

  it('shows the calculation tool response message from an error event', async () => {
    const store = useCalculationStore()
    const promise = store.sendAndCalculate('开始测算')

    handlers.onEvent({
      type: 'error',
      id: '242',
      data: {
        event: 'error',
        session: { session_id: 's1', chat_id: 'c1', round: 1, state: 'processing', phase: 'flow' },
        data: {
          tool_name: 'create_calculation_task',
          exception: null,
          response: { code: 400, msg: 'EPC单价超出允许范围，正确范围为[0.7, 1.1]', data: null },
        },
      },
    })
    await promise

    const message = store.messages.at(-1)
    expect(message).toMatchObject({
      phase: 'error',
      done: true,
      error: 'EPC单价超出允许范围，正确范围为[0.7, 1.1]',
      answerText: '测算失败：EPC单价超出允许范围，正确范围为[0.7, 1.1]',
    })
  })

  it.each([
    ['question_text', '请问您本次想咨询哪个业务方向？'],
    ['text', '请补充本次需要咨询的业务方向。'],
  ])('uses question.%s as the assistant reply before eof', async (field, questionText) => {
    const store = useCalculationStore()
    const promise = store.sendAndCalculate('我想咨询业务')
    handlers.onEvent({
      type: 'thinking', id: '1',
      data: {
        data: {
          node_id: 'n002-confirm_dir', node_status: 'waiting_user',
          node_title: '业务意图推理研判',
        },
      },
    })
    handlers.onEvent({
      type: 'question', id: '2', data: { data: { [field]: questionText } },
    })
    handlers.onComplete({ reason: 'eof' })
    await promise
    await vi.runAllTimersAsync()

    const message = store.messages.at(-1)
    expect(message.answerText).toBe(questionText)
    expect(message.phase).toBe('completed')
    expect(message.done).toBe(true)
    expect(message.doneReceived).toBe(true)
    expect(message.error).toBeNull()
    expect(message.thinkingState.nodesById['n002-confirm_dir'].status).toBe('waiting_user')
    expect(store.responding).toBe(false)
  })

  it('rejects a calculation result from a different conversation', async () => {
    const store = useCalculationStore()
    const promise = store.sendAndCalculate('测算甘肃 200MW/800MWh')
    handlers.onOpen({ conversationId: 'c1' })

    answerEvent('', [{
      tool: 'create_calculation_task',
      payload: { data: { conversationId: 'c2', taskId: 't1', version: 'V1', status: 'completed' } },
    }])
    await promise
    await flush()

    const message = store.messages.at(-1)
    expect(store.conversationId).toBe('c1')
    expect(store.versions).toEqual([])
    expect(api.getCalculationResult).not.toHaveBeenCalled()
    expect(message.phase).toBe('error')
    expect(message.answerText).toContain('会话标识不一致')
  })

  it('stops the active stream and finalizes the message', async () => {
    const store = useCalculationStore()
    const promise = store.sendAndCalculate('开始')
    handlers.onEvent({ type: 'thinking', id: '1', data: { data: { node_id: 'n1', node_status: 'active' } } })

    store.stopStream()
    handlers.onComplete({ reason: 'aborted' })
    await promise

    const message = store.messages.at(-1)
    expect(close).toHaveBeenCalledOnce()
    expect(message).toMatchObject({ phase: 'cancelled', cancelled: true, done: true, answerText: '已停止生成' })
    expect(message.thinkingState.nodesById.n1.status).toBe('completed')
    expect(store.responding).toBe(false)
  })

  it('treats eof before done as an error and ignores a late result after reset', async () => {
    let resolveResult
    api.getCalculationResult.mockReturnValue(new Promise((resolve) => { resolveResult = resolve }))
    const store = useCalculationStore()
    const promise = store.sendAndCalculate('开始')
    answerEvent('', [{
      tool: 'create_calculation_task',
      payload: { data: { conversationId: 'c1', taskId: 't1', version: 'V1', status: 'completed', input: {} } },
    }])
    handlers.onComplete({ reason: 'eof' })
    await promise
    expect(store.messages.at(-1).answerText).toContain('连接已中断')

    store.resetConversation()
    resolveResult({ data: result })
    await flush()
    expect(store.versions).toEqual([])
  })
})

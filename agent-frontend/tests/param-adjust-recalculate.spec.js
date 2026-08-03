import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useCalculationStore } from '@/store/modules/calculation'

const api = vi.hoisted(() => ({
  createCalculationTask: vi.fn(),
  getCalculationTask: vi.fn(),
  getCalculationResult: vi.fn(),
  listConversations: vi.fn(),
  getConversation: vi.fn(),
  deleteConversation: vi.fn(),
  getParamDict: vi.fn(),
  getStations: vi.fn(),
}))

const chat = vi.hoisted(() => ({ openChatStream: vi.fn() }))

vi.mock('@/api/calc', () => api)
vi.mock('@/utils/chatSse', () => chat)

const resultOf = (province) => ({
  basicInfo: { province }, financial: { capitalIrr: 8 }, advanced: { donut: {}, lines: {} },
})

describe('param adjustment: recalculate + param meta', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    api.listConversations.mockResolvedValue({ data: { items: [] } })
    api.getParamDict.mockResolvedValue({ data: { parameters: [{ id: 'epc_unit_price' }], switches: { switch_spot: 1 } } })
    api.getStations.mockResolvedValue({ data: { items: ['祥泰站'] } })
  })

  it('sendAndCalculate 成功后版本携带本次冻结 input，并加载参数元数据', async () => {
    let handlers
    chat.openChatStream.mockImplementation((_path, _body, options) => {
      handlers = options
      return { close: vi.fn() }
    })
    api.getCalculationResult.mockResolvedValue({ data: resultOf('甘肃') })
    const store = useCalculationStore()

    const sent = store.sendAndCalculate('测算甘肃 200MW/800MWh')
    handlers.onEvent({
      type: 'answer', id: '1', data: { data: { answer: '', biz: [{
        tool: 'create_calculation_task',
        payload: { data: { conversationId: 1, taskId: 10, version: 'V1', status: 'completed', input: { province: '甘肃', spot_charge_avg: 0.2 } } },
      }] } },
    })
    await Promise.resolve()
    await Promise.resolve()
    handlers.onEvent({ type: 'done', id: '2', data: { data: {} } })
    await sent
    await Promise.resolve()

    expect(store.versions[0].input).toEqual({ province: '甘肃', spot_charge_avg: 0.2 })
    expect(api.getParamDict).toHaveBeenCalledWith('甘肃')
    expect(api.getStations).toHaveBeenCalledWith('甘肃')
    expect(store.paramDict).toEqual([{ id: 'epc_unit_price' }])
    expect(store.switches).toEqual({ switch_spot: 1 })
    expect(store.stationOptions).toEqual(['祥泰站'])
  })

  it('recalculate 携带锁定省份、面板基础字段与受控 overrides 发起新版本', async () => {
    const store = useCalculationStore()
    store.conversationId = 1
    store.versions = [{ conversationId: 1, taskId: 10, version: 'V1', status: 'completed', result: resultOf('甘肃'), input: { province: '甘肃' } }]
    api.createCalculationTask.mockResolvedValue({
      data: { conversationId: 1, taskId: 11, version: 'V2', status: 'completed', input: { province: '甘肃', epc_unit_price: 0.8 } },
    })
    api.getCalculationResult.mockResolvedValue({ data: resultOf('甘肃') })

    await store.recalculate({
      overrides: { epc_unit_price: 0.8 },
      basics: { node_name: '新节点', capacity_mwh: 400, power_mw: 100 },
    })

    expect(api.createCalculationTask).toHaveBeenCalledWith({
      province: '甘肃', capacity_mwh: 400, power_mw: 100, node_name: '新节点',
      param_overrides: { epc_unit_price: 0.8 },
    }, 1)
    expect(store.versions.map((v) => v.version)).toEqual(['V1', 'V2'])
    expect(store.versions[1].input.epc_unit_price).toBe(0.8)
    expect(store.selectedVersion).toBe('V2')
  })

  it('recalculate 拒绝其他会话的测算结果', async () => {
    const store = useCalculationStore()
    store.conversationId = 1
    store.versions = [{
      conversationId: 1,
      taskId: 10,
      version: 'V1',
      status: 'completed',
      result: resultOf('甘肃'),
      input: { province: '甘肃' },
    }]
    api.createCalculationTask.mockResolvedValue({
      data: { conversationId: 2, taskId: 11, version: 'V1', status: 'completed' },
    })

    await store.recalculate({
      overrides: { epc_unit_price: 0.8 },
      basics: { node_name: '新节点', capacity_mwh: 400, power_mw: 100 },
    })

    expect(store.conversationId).toBe(1)
    expect(store.versions.map((item) => item.version)).toEqual(['V1'])
    expect(api.getCalculationResult).not.toHaveBeenCalled()
    expect(store.messages.at(-1).answerText).toContain('会话标识不一致')
  })

  it('recalculate 以后端返回的版本号追加新版本且不继承旧报告', async () => {
    const store = useCalculationStore()
    store.conversationId = 1
    store.versions = [{
      conversationId: 1,
      taskId: 10,
      version: 'V1',
      status: 'completed',
      result: resultOf('甘肃'),
      input: { province: '甘肃' },
      report: { status: 'completed', reportId: 'r-1' },
    }]
    api.createCalculationTask.mockResolvedValue({
      data: { conversationId: 1, taskId: 11, version: 'V2', status: 'completed', input: { province: '甘肃', epc_unit_price: 0.8 } },
    })
    api.getCalculationResult.mockResolvedValue({ data: resultOf('甘肃') })

    await store.recalculate({
      overrides: { epc_unit_price: 0.8 },
      basics: { node_name: '新节点', capacity_mwh: 400, power_mw: 100 },
    })

    expect(store.versions.map((item) => item.version)).toEqual(['V1', 'V2'])
    expect(store.versions[1].report).toBeUndefined()
    expect(store.selectedVersion).toBe('V2')
  })

  it('recalculate 在无会话时不发起请求', async () => {
    const store = useCalculationStore()
    await store.recalculate({ overrides: {}, basics: { node_name: null, capacity_mwh: 1, power_mw: 1 } })
    expect(api.createCalculationTask).not.toHaveBeenCalled()
  })

  it('recalculate 测算中重复调用被忽略', async () => {
    const store = useCalculationStore()
    store.conversationId = 1
    store.responding = true
    store.versions = [{ input: { province: '甘肃' } }]
    await store.recalculate({ overrides: {}, basics: { node_name: null, capacity_mwh: 1, power_mw: 1 } })
    expect(api.createCalculationTask).not.toHaveBeenCalled()
  })

  it('openConversation 回放版本携带 input 并按会话省份加载参数元数据', async () => {
    api.getConversation.mockResolvedValue({
      data: {
        conversationId: 7,
        title: '甘肃 200MW/800MWh',
        messages: [
          { role: 'user', content: '测算甘肃 200MW/800MWh', createdAt: '2026-07-15T09:00:00' },
          { role: 'assistant', content: 'V1 完成', createdAt: '2026-07-15T09:01:00' },
        ],
        versions: [
          { taskId: 10, version: 'V1', status: 'completed', result: resultOf('甘肃'), input: { province: '甘肃' } },
        ],
      },
    })
    const store = useCalculationStore()

    await store.openConversation(7)

    expect(store.versions[0].input).toEqual({ province: '甘肃' })
    expect(api.getParamDict).toHaveBeenCalledWith('甘肃')
  })
})

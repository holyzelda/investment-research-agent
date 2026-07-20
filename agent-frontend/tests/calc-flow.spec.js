import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { extractMinInput, useCalculationStore } from '@/store/modules/calculation'

const api = vi.hoisted(() => ({
  createCalculationTask: vi.fn(),
  getCalculationTask: vi.fn(),
  getCalculationResult: vi.fn(),
}))

vi.mock('@/api/calc', () => api)

const result = {
  version: 'V1',
  basicInfo: { province: '甘肃', powerMw: 200, capacityMwh: 800 },
  financial: { capitalIrr: 8.6 },
  advanced: { donut: {}, lines: {} },
}

describe('operation years extraction', () => {
  it.each([
    ['测算甘肃 200MW/800MWh，运营期20年', 20],
    ['按15年测算甘肃 200MW/800MWh', 15],
  ])('extracts explicit operation years from %s', (text, operationYears) => {
    expect(extractMinInput(text).operation_years).toBe(operationYears)
  })

  it('leaves operation years unset when not mentioned', () => {
    expect(extractMinInput('测算甘肃 200MW/800MWh').operation_years).toBeNull()
  })
})


describe('calculation submit-poll-result flow', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    api.getCalculationResult.mockResolvedValue({ data: result })
  })

  it('uses terminal POST result without polling and keeps backend identifiers', async () => {
    api.createCalculationTask.mockResolvedValue({
      data: { conversationId: 'c1', taskId: 't1', version: 'V1', status: 'completed' },
    })
    const store = useCalculationStore()

    await store.sendAndCalculate('测算甘肃 200MW/800MWh')

    expect(api.createCalculationTask).toHaveBeenCalledWith({
      province: '甘肃', capacity_mwh: 800, power_mw: 200,
    })
    expect(api.getCalculationTask).not.toHaveBeenCalled()
    expect(api.getCalculationResult).toHaveBeenCalledWith('t1')
    expect(store.versions[0]).toMatchObject({
      conversationId: 'c1', taskId: 't1', version: 'V1', result,
    })
    expect(store.selectedVersion).toBe('V1')
  })

  it('polls a non-terminal task and includes conversation_id next time', async () => {
    vi.useFakeTimers()
    api.createCalculationTask
      .mockResolvedValueOnce({
        data: { conversationId: 'c1', taskId: 't1', version: 'V1', status: 'created' },
      })
      .mockResolvedValueOnce({
        data: { conversationId: 'c1', taskId: 't2', version: 'V2', status: 'completed' },
      })
    api.getCalculationTask.mockResolvedValue({
      data: { taskId: 't1', status: 'completed', requestId: 'r1' },
    })
    const store = useCalculationStore()

    const first = store.sendAndCalculate('测算甘肃 200MW/800MWh')
    await vi.advanceTimersByTimeAsync(1000)
    await first
    await store.sendAndCalculate('测算宁夏 100MW/400MWh')

    expect(api.getCalculationTask).toHaveBeenCalledWith('t1')
    expect(api.createCalculationTask).toHaveBeenLastCalledWith({
      province: '宁夏', capacity_mwh: 400, power_mw: 100, conversation_id: 'c1',
    })
    expect(store.versions.map((item) => item.version)).toEqual(['V1', 'V2'])
    vi.useRealTimers()
  })

  it('shows backend failure reason and request id without fetching result', async () => {
    api.createCalculationTask.mockResolvedValue({
      data: {
        conversationId: 'c1', taskId: 't1', version: 'V1', status: 'failed',
        error: { message: '底稿接口区损坏', requestId: 'req-123' },
      },
    })
    const store = useCalculationStore()

    await store.sendAndCalculate('测算甘肃 200MW/800MWh')

    expect(api.getCalculationResult).not.toHaveBeenCalled()
    expect(store.messages.at(-1).text).toContain('底稿接口区损坏')
    expect(store.messages.at(-1).text).toContain('req-123')
  })
})

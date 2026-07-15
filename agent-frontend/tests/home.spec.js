import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { extractMinInput, useCalculationStore } from '@/store/modules/calculation'

const api = vi.hoisted(() => ({
  createCalculationTask: vi.fn(),
  getCalculationTask: vi.fn(),
  getCalculationResult: vi.fn(),
}))

vi.mock('@/api/calc', () => api)

describe('home conversation and minimum input extraction', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('extracts province, power and capacity regardless of order', () => {
    expect(extractMinInput('测算甘肃 200MW/800MWh 独立储能项目')).toEqual({
      province: '甘肃',
      power_mw: 200,
      capacity_mwh: 800,
      missing: [],
    })
    expect(extractMinInput('宁夏项目容量 400 MWh，功率 100 mw')).toMatchObject({
      province: '宁夏',
      power_mw: 100,
      capacity_mwh: 400,
      missing: [],
    })
  })

  it('prompts for every missing required field without making a request', async () => {
    const store = useCalculationStore()

    await store.sendAndCalculate('测算甘肃储能项目')

    expect(api.createCalculationTask).not.toHaveBeenCalled()
    expect(store.messages.at(-1).text).toContain('项目功率（MW）')
    expect(store.messages.at(-1).text).toContain('项目容量（MWh）')
    expect(store.responding).toBe(false)
  })
})

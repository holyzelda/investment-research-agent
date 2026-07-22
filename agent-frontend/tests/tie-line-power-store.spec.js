import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const api = vi.hoisted(() => ({
  getTieLineDetail: vi.fn(),
  getTieLinePower: vi.fn(),
  getTieLines: vi.fn(),
}))

vi.mock('@/api/tieLine', () => api)

import {
  getRollingDateRange,
  isValidCustomPowerRange,
  useTieLineStore,
} from '@/store/modules/tieLine'

describe('联络线功率趋势状态', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('以自然日昨天生成昨日、7日、30日和90日闭区间', () => {
    const now = new Date(2026, 6, 21, 12, 0, 0)

    expect(getRollingDateRange(1, now)).toEqual({ startDate: '2026-07-20', endDate: '2026-07-20' })
    expect(getRollingDateRange(7, now)).toEqual({ startDate: '2026-07-14', endDate: '2026-07-20' })
    expect(getRollingDateRange(30, now)).toEqual({ startDate: '2026-06-21', endDate: '2026-07-20' })
    expect(getRollingDateRange(90, now)).toEqual({ startDate: '2026-04-22', endDate: '2026-07-20' })
  })

  it('拒绝结束日期为当天或日期倒置的自定义范围', () => {
    const now = new Date(2026, 6, 21, 12, 0, 0)

    expect(isValidCustomPowerRange('2026-07-19', '2026-07-20', now)).toBe(true)
    expect(isValidCustomPowerRange('2026-07-20', '2026-07-21', now)).toBe(false)
    expect(isValidCustomPowerRange('2026-07-20', '2026-07-19', now)).toBe(false)
  })

  it('选择线路时默认请求昨日趋势', async () => {
    api.getTieLineDetail.mockResolvedValue({ data: { id: 1, name: '甲乙线' } })
    api.getTieLinePower.mockResolvedValue({ data: { lineId: 1, points: [] } })
    const store = useTieLineStore()
    const expectedRange = getRollingDateRange(1)

    await store.selectLine(1)

    expect(api.getTieLinePower).toHaveBeenCalledWith(1, { key: 'yesterday', ...expectedRange })
    expect(store.powerTrend).toEqual({ lineId: 1, points: [] })
  })

  it('后发线路请求完成后，先发线路响应不得覆盖当前详情或趋势', async () => {
    let resolveDetailA
    let resolvePowerA
    api.getTieLineDetail
      .mockImplementationOnce(() => new Promise((resolve) => { resolveDetailA = resolve }))
      .mockResolvedValueOnce({ data: { id: 2, name: '乙丙线' } })
    api.getTieLinePower
      .mockImplementationOnce(() => new Promise((resolve) => { resolvePowerA = resolve }))
      .mockResolvedValueOnce({ data: { lineId: 2, points: [{ time: '00:15', powerMw: 200 }] } })
    const store = useTieLineStore()

    const selectA = store.selectLine(1)
    const selectB = store.selectLine(2)
    await selectB
    resolveDetailA({ data: { id: 1, name: '甲乙线' } })
    resolvePowerA({ data: { lineId: 1, points: [{ time: '00:15', powerMw: 100 }] } })
    await selectA

    expect(store.selectedId).toBe(2)
    expect(store.detail).toEqual({ id: 2, name: '乙丙线' })
    expect(store.powerTrend.lineId).toBe(2)
  })

  it('同一线路快速切换范围时，只保留后发范围的趋势结果', async () => {
    let resolveYesterday
    let resolveSevenDays
    api.getTieLineDetail.mockResolvedValue({ data: { id: 1 } })
    api.getTieLinePower
      .mockImplementationOnce(() => new Promise((resolve) => { resolveYesterday = resolve }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveSevenDays = resolve }))
    const store = useTieLineStore()

    const initial = store.selectLine(1)
    const sevenDays = getRollingDateRange(7)
    const changed = store.setPowerRange('sevenDays', sevenDays)
    resolveSevenDays({ data: { lineId: 1, points: [{ time: '00:15', powerMw: 200 }] } })
    await changed
    resolveYesterday({ data: { lineId: 1, points: [{ time: '00:15', powerMw: 100 }] } })
    await initial

    expect(store.powerRange).toEqual({ key: 'sevenDays', ...sevenDays })
    expect(store.powerTrend.points[0].powerMw).toBe(200)
  })

  it('清空选择后，滞后趋势响应不得恢复数据', async () => {
    let resolvePower
    api.getTieLineDetail.mockResolvedValue({ data: { id: 1 } })
    api.getTieLinePower.mockImplementationOnce(() => new Promise((resolve) => { resolvePower = resolve }))
    const store = useTieLineStore()

    const selection = store.selectLine(1)
    store.clearSelection()
    resolvePower({ data: { lineId: 1, points: [] } })
    await selection

    expect(store.selectedId).toBeNull()
    expect(store.powerTrend).toBeNull()
  })

  it('推荐线路变化时默认请求昨日趋势', async () => {
    api.getTieLinePower.mockResolvedValue({ data: { lineId: 2, points: [] } })
    const store = useTieLineStore()
    store.lines = [
      { id: 1, name: '短线', lengthText: '100 km' },
      { id: 2, name: '长线', lengthText: '2,383 km' },
    ]
    const expectedRange = getRollingDateRange(1)

    await store.loadRecommendedPowerTrend()

    expect(api.getTieLinePower).toHaveBeenCalledWith(2, { key: 'yesterday', ...expectedRange })
    expect(store.powerTrend).toEqual({ lineId: 2, points: [] })
  })

  it('已有用户选中线路时不为推荐线路覆盖功率趋势', async () => {
    const store = useTieLineStore()
    store.lines = [{ id: 2, name: '长线', lengthText: '2,383 km' }]
    store.selectedId = 1

    await store.loadRecommendedPowerTrend()

    expect(api.getTieLinePower).not.toHaveBeenCalled()
  })
})

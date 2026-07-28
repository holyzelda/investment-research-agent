import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api/indexMap', () => ({
  listIndexMapPeriods: vi.fn(),
  getIndexMapOverview: vi.fn(),
  getIndexMapProvinceDetail: vi.fn(),
}))

import { getIndexMapOverview, getIndexMapProvinceDetail, listIndexMapPeriods } from '@/api/indexMap'
import { useIndexMapStore } from '@/store/modules/indexMap'

const overview = {
  provinces: [{ provinceCode: 'NMG', indexScore: 95 }],
  summary: { leader: { provinceCode: 'NMG' } },
  rankings: { investmentHeat: [], returnStability: [] },
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('全国指数地图 Store', () => {
  it('默认选择最新期次，加载概览并选择领跑省份', async () => {
    listIndexMapPeriods.mockResolvedValue({ items: [{ period: '2026-07' }] })
    getIndexMapOverview.mockResolvedValue(overview)
    getIndexMapProvinceDetail.mockResolvedValue({ provinceCode: 'NMG' })

    const store = useIndexMapStore()
    await store.initialize()

    expect(store.activePeriod).toBe('2026-07')
    expect(store.selectedProvinceCode).toBe('NMG')
    expect(getIndexMapProvinceDetail).toHaveBeenCalledWith('NMG', '2026-07')
  })

  it('切换期次优先保留仍存在的省份，否则回退至领跑省份', async () => {
    getIndexMapOverview.mockResolvedValueOnce({
      ...overview,
      provinces: [{ provinceCode: 'NMG' }],
    }).mockResolvedValueOnce({
      ...overview,
      provinces: [{ provinceCode: 'GS' }],
      summary: { leader: { provinceCode: 'GS' } },
    })
    getIndexMapProvinceDetail.mockResolvedValue({})
    const store = useIndexMapStore()
    store.activePeriod = '2026-06'
    store.selectedProvinceCode = 'NMG'

    await store.selectPeriod('2026-07')

    expect(store.selectedProvinceCode).toBe('GS')
  })
})

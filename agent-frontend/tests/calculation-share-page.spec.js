import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const api = vi.hoisted(() => ({
  getPublicShare: vi.fn(),
}))

vi.mock('@/api/calc', () => api)
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { shareCode: 'public-share-code' } }),
}))
vi.mock('echarts', () => ({
  init: () => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn(), on: vi.fn() }),
}))

import CalculationSharePage from '@/views/public/calculation-share.vue'

describe('CalculationSharePage', () => {
  it('renders an active share from the request interceptor response shape', async () => {
    api.getPublicShare.mockResolvedValue({
      code: 200,
      msg: 'success',
      data: {
        status: 'active',
        version: 'V2',
        calculatedAt: '2026-08-13T10:30:00',
        basicInfo: {
          province: '陕西省',
          city: '西安',
          nodeName: '西安节点',
          powerMw: 100,
          capacityMwh: 200,
          actualSpread: 0.4567,
          chargeCost: 0.2,
          dischargeReturn: 0.6,
          lossCost: 0.03,
        },
        financial: { projectIrr: 8.2 },
        advanced: {
          donut: { totalRevenue: 1000, energyRevenue: 600, capacityRevenue: 400 },
          debtServiceCoverage: { cashflowRatio: [1.2, 1.3] },
        },
        warnings: [],
      },
    })

    const wrapper = mount(CalculationSharePage)
    await flushPromises()

    expect(api.getPublicShare).toHaveBeenCalledWith('public-share-code')
    expect(wrapper.find('.ir-share-page__content').exists()).toBe(true)
    expect(wrapper.text()).toContain('V2')
    expect(wrapper.text()).toContain('100')
    expect(wrapper.text()).toContain('实际价差')
    expect(wrapper.text()).toContain('0.4567元/kWh')
    expect(wrapper.findAll('.ir-share-basic__stat')).toHaveLength(6)
    expect(wrapper.text()).toContain('核心投资收益指标')
    expect(wrapper.text()).toContain('首年收入结构')
    expect(wrapper.text()).toContain('偿债覆盖倍数')
    expect(wrapper.findAll('.ir-fin__kpi')).toHaveLength(5)
    expect(wrapper.findAll('.ir-report-watermark__text')).toHaveLength(15)
    expect(wrapper.find('.ir-share-page__watermark').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('无法查看')
  })

  it('shows a useful error when a successful response has no share payload', async () => {
    api.getPublicShare.mockResolvedValue({ code: 200, msg: 'success', data: {} })

    const wrapper = mount(CalculationSharePage)
    await flushPromises()

    expect(wrapper.text()).toContain('分享接口未返回有效内容')
  })
})

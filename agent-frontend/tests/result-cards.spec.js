import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ResultCard from '@/views/home/components/ResultCard.vue'

vi.mock('@/views/home/composables/useEcharts', () => ({
  useEcharts: () => ({ el: { value: null }, resize: vi.fn() }),
  xcChartColors: () => ['#1', '#2', '#3', '#4'],
  xcVar: () => '#888',
}))

const snapshot = {
  basicInfo: {
    province: '甘肃', nodeName: null, powerMw: 200, capacityMwh: 800,
    chargeCost: 0.2, dischargeReturn: 0.61234, lossCost: 0.03,
  },
  financial: {
    projectIrr: 7.1, projectStaticPayback: 8.256, capitalIrr: 9.3,
    capitalStaticPayback: 6, averageProfit: 1200,
  },
  advanced: { donut: {}, debtServiceCoverage: {} },
  warnings: [],
}

describe('result card three modules', () => {
  it('renders basic information, five KPIs and both advanced charts', () => {
    const wrapper = mount(ResultCard, { props: { result: snapshot, version: 'V1' } })
    const text = wrapper.text()

    expect(text).toContain('项目基础边界条件')
    expect(text).toContain('甘肃')
    expect(text).not.toContain('节点')
    expect(text).toContain('核心投资收益指标')
    for (const label of ['项目全投资IRR', '全投资静态回收期', '资本金IRR', '资本金静态回收期', '年均利润']) {
      expect(text).toContain(label)
    }
    expect(text).toContain('收益数据深度分析')
    expect(text).toContain('首年收入结构')
    expect(text).toContain('偿债覆盖倍数')
    expect(text).toContain('0.2000 元/kWh')
    expect(text).toContain('0.6123 元/kWh')
    expect(text).toContain('0.0300 元/kWh')
    expect(text).toContain('8.26')
    expect(text).toContain('6年')
    expect(text).not.toContain('6.00年')
    expect(wrapper.findAll('.ir-report-module')).toHaveLength(3)
    expect(wrapper.find('.ir-result__head--complete').exists()).toBe(true)
    expect(wrapper.find('.ir-fin__kpi--signature').text()).toContain('项目全投资IRR')
    expect(wrapper.findAll('.ir-fin__kpi')).toHaveLength(5)
    expect(snapshot.basicInfo.dischargeReturn).toBe(0.61234)
    expect(snapshot.financial.projectStaticPayback).toBe(8.256)
  })

  it('renders the adjustment panel when param dict is provided, hides it otherwise', async () => {
    const withDict = mount(ResultCard, {
      props: {
        result: snapshot, version: 'V1',
        paramDict: [{ id: 'epc_unit_price', cn: 'EPC单价', zone: 'financial_boundary', control: 'slider', min: 0.7, max: 0.85, step: 0.01 }],
        switches: {}, seedInput: {},
      },
    })
    expect(withDict.find('.ir-adjust__toggle').exists()).toBe(true)
    await withDict.find('.ir-adjust__toggle').trigger('click')
    expect(withDict.find('.ir-adjust__footer .ir-adjust__advanced').exists()).toBe(true)

    const withoutDict = mount(ResultCard, { props: { result: snapshot, version: 'V1' } })
    expect(withoutDict.find('.ir-adjust__toggle').exists()).toBe(false)
  })
})

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
  advanced: { donut: {}, lines: {} },
  warnings: [],
}

describe('result card three modules', () => {
  it('renders basic information, five KPIs and both advanced charts', () => {
    const wrapper = mount(ResultCard, { props: { result: snapshot, version: 'V1' } })
    const text = wrapper.text()

    expect(text).toContain('① 基本信息')
    expect(text).toContain('甘肃')
    expect(text).not.toContain('节点')
    expect(text).toContain('② 财务指标')
    for (const label of ['项目全投资IRR', '全投资静态回收期', '资本金IRR', '资本金静态回收期', '年均利润']) {
      expect(text).toContain(label)
    }
    expect(text).toContain('③ 进阶图形结果')
    expect(text).toContain('首年收入结构')
    expect(text).toContain('15 年现金流序列')
    expect(text).toContain('0.2000 元/kWh')
    expect(text).toContain('0.6123 元/kWh')
    expect(text).toContain('0.0300 元/kWh')
    expect(text).toContain('8.26')
    expect(text).toContain('6年')
    expect(text).not.toContain('6.00年')
    expect(snapshot.basicInfo.dischargeReturn).toBe(0.61234)
    expect(snapshot.financial.projectStaticPayback).toBe(8.256)
    expect(wrapper.find('button').attributes('disabled')).toBeDefined()
  })
})

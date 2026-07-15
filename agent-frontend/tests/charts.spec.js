import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

const captured = vi.hoisted(() => ({ factories: [] }))
const colors = vi.hoisted(() => vi.fn(() => ['c1', 'c2', 'c3', 'c4', 'c5', 'c6']))

vi.mock('@/views/home/composables/useEcharts', () => ({
  useEcharts: (factory) => {
    captured.factories.push(factory)
    return { el: { value: null }, resize: vi.fn() }
  },
  xcChartColors: colors,
  xcVar: () => '#888',
}))

import RevenueDonut from '@/views/home/components/RevenueDonut.vue'
import CashflowLines from '@/views/home/components/CashflowLines.vue'

const years = Array.from({ length: 15 }, (_, i) => i + 1)

describe('result chart series contract', () => {
  beforeEach(() => {
    captured.factories.length = 0
    colors.mockClear()
  })

  it('builds all six revenue categories including zero values', () => {
    mount(RevenueDonut, {
      props: { donut: {
        totalRevenue: 100, energyRevenue: 40, capacityRevenue: 30,
        frequencyRevenue: 0, leaseRevenue: 10, interventionRevenue: 5, subsidyRevenue: 15,
      } },
    })
    const option = captured.factories[0]()

    expect(option.series[0].data.map((item) => item.name)).toEqual([
      '电能量', '容量市场', '调频市场', '租赁市场', '干预补偿', '补贴',
    ])
    expect(option.tooltip.formatter({ name: '电能量', value: 12.345, percent: 33.333 })).toBe(
      '电能量: 12.35 万元 (33.33%)',
    )
    expect(option.color).toEqual(['c1', 'c2', 'c3', 'c4', 'c5', 'c6'])
  })

  it('builds four 15-year cashflow series', () => {
    mount(CashflowLines, { props: { lines: {
      mainBusinessCost: years,
      currentPrincipalInterest: years,
      capitalNetCashflow: years,
      totalInvestNetCashflowAfterTax: years,
    } } })
    const option = captured.factories[0]()

    expect(option.series.map((item) => item.name)).toEqual([
      '主营业务成本', '当期还本付息', '资本金净现金流', '全投资净现金流',
    ])
    expect(option.series.every((item) => item.data.length === 15)).toBe(true)
    expect(option.xAxis.data).toHaveLength(15)
    expect(option.yAxis.axisLabel.formatter(12.345)).toBe('12.35')
    expect(option.yAxis.axisLabel.formatter(12)).toBe('12')
  })
})

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
import DebtServiceCoverage from '@/views/home/components/DebtServiceCoverage.vue'

const years = Array.from({ length: 15 }, (_, i) => i + 1)

describe('result chart series contract', () => {
  beforeEach(() => {
    captured.factories.length = 0
    colors.mockClear()
  })

  it('excludes zero/absent revenue categories from both the ring and the legend', () => {
    mount(RevenueDonut, {
      props: { donut: {
        totalRevenue: 100, energyRevenue: 40, capacityRevenue: 30,
        frequencyRevenue: 0, leaseRevenue: 10, interventionRevenue: 5, subsidyRevenue: 15,
      } },
    })
    const option = captured.factories[0]()

    // 调频市场收益为 0，在环形图上是 0 度扇区（视觉上不存在），图例也不应保留该条目
    expect(option.series[0].data.map((item) => item.name)).toEqual([
      '电能量', '容量市场', '租赁市场', '干预补偿', '补贴',
    ])
    expect(option.tooltip.formatter({ name: '电能量', value: 12.345, percent: 33.333 })).toBe(
      '电能量: 12.35 万元 (33.33%)',
    )
    expect(option.color).toEqual(['c1', 'c2', 'c3', 'c4', 'c5', 'c6'])

    // 首年总收入两行文本用 position:'center' 的环心标签渲染（由 ECharts 自动锚到环心，
    // 不用 graphic 百分比定位），保证在任意容器尺寸下都居中
    expect(option.graphic).toBeUndefined()
    expect(option.series[0].center).toEqual(['34%', '50%'])
    expect(option.series[0].label.position).toBe('center')
    expect(option.series[0].label.formatter).toBe('{label|首年总收入}\n{value|100}')
    expect(option.series[0].emphasis.label.formatter).toBe('{label|首年总收入}\n{value|100}')
  })

  it('builds a debt-service-coverage line with a threshold and a middle break', () => {
    mount(DebtServiceCoverage, {
      props: {
        coverage: { cashflowRatio: [1.12, 0, null, 1.36] },
      },
    })
    const option = captured.factories[0]()

    expect(option.series).toHaveLength(2)
    expect(option.xAxis.boundaryGap).toBe(false)
    expect(option.series[1]).toMatchObject({
      type: 'line',
      data: [2.6, 2, null, 3.8],
      showSymbol: false,
      lineStyle: { opacity: 0 },
      areaStyle: { origin: 2 },
      tooltip: { show: false },
      silent: true,
    })
    expect(option.series[0].data).toEqual([2.6, 0, null, 3.8])
    expect(option.yAxis.interval).toBe(1)
    expect(option.yAxis.axisLabel.formatter(0)).toBe('0.0')
    expect(option.yAxis.axisLabel.formatter(1)).toBe('0.5')
    expect(option.yAxis.axisLabel.formatter(2)).toBe('1.0')
    expect(option.yAxis.axisLabel.formatter(3)).toBe('1.2')
    expect(option.yAxis.axisLabel.formatter(4)).toBe('1.4')
    expect(option.series[0].markLine.data).toEqual([{ yAxis: 2 }])
    expect(option.series[0].markArea).toMatchObject({
      data: [[{ yAxis: 0 }, { yAxis: 2 }]],
    })
    expect(option.tooltip.formatter([{ axisValue: '第1年', dataIndex: 0 }])).toContain('1.12 倍')
    expect(option.series[0]).toMatchObject({
      name: '偿债倍数',
      type: 'line',
      showSymbol: true,
      symbol: 'circle',
      symbolSize: 8,
      connectNulls: false,
      lineStyle: { width: 2 },
      color: '#888',
      itemStyle: { color: '#888', borderWidth: 2 },
    })
    expect(option.series[0].markLine).toMatchObject({
      symbol: 'none',
      lineStyle: { type: 'dashed', width: 1.5 },
      label: { show: true, formatter: '警戒线 1.0', position: 'insideEndTop' },
      data: [{ yAxis: 2 }],
    })
    expect(option.series[0].areaStyle).toBeUndefined()
    expect(option.tooltip.axisPointer).toEqual({ type: 'cross' })
    expect(option.yAxis.axisPointer).toEqual({ label: { show: false } })
    expect(option.xAxis.axisPointer).toBeUndefined()
    expect(option.tooltip.formatter([{ axisValue: '第2年', dataIndex: 1 }])).toContain('第2年')
    expect(option.tooltip.formatter([{ axisValue: '第2年', dataIndex: 1 }])).toContain('0 倍')
    expect(option.xAxis.data).toEqual(['第1年', '第2年', '第3年', '第4年'])
    expect(option.yAxis.name).toBe('偿债倍数')
  })

  it('renders both analysis charts as elevated report cards', () => {
    const donut = mount(RevenueDonut, { props: { donut: { totalRevenue: 100 } } })
    const coverage = mount(DebtServiceCoverage, { props: { coverage: { cashflowRatio: [1, 1.2] } } })

    expect(donut.find('.ir-chart--report').exists()).toBe(true)
    expect(coverage.find('.ir-chart--report').exists()).toBe(true)
  })

  it('does not create a business series for an empty coverage sequence', () => {
    mount(DebtServiceCoverage, { props: { coverage: { cashflowRatio: [] } } })
    const option = captured.factories[0]()

    expect(option.series).toEqual([])
    expect(option.xAxis.data).toEqual([])
  })
})

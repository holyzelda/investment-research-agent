import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

const chart = vi.hoisted(() => ({ optionFactory: null }))
vi.mock('element-plus', () => ({
  ElDatePicker: {},
  ElDialog: {},
}))
vi.mock('@/views/home/composables/useEcharts', () => ({
  useEcharts: (optionFactory) => {
    chart.optionFactory = optionFactory
    return { el: ref(null) }
  },
  xcVar: (token) => token,
}))

import TieLinePowerTrend from '@/views/tie-line/components/TieLinePowerTrend.vue'
import tieLinePowerTrendSource from '@/views/tie-line/components/TieLinePowerTrend.vue?raw'

const points = Array.from({ length: 96 }, (_, index) => ({
  time: index === 95 ? '24:00' : String(index),
  powerMw: index === 1 ? null : index + 100,
}))
const styles = tieLinePowerTrendSource.match(/<style scoped>([\s\S]*)<\/style>/)?.[1] || ''

describe('联络线功率趋势组件', () => {
  it('显示日期范围并将固定 96 点映射为带断点的折线', () => {
    const wrapper = mount(TieLinePowerTrend, {
      props: {
        trend: { startDate: '2026-07-20', endDate: '2026-07-20', dataDateCount: 1, points },
        range: { key: 'yesterday', startDate: '2026-07-20', endDate: '2026-07-20' },
      },
      global: { stubs: { ElDialog: true, ElDatePicker: true } },
    })

    expect(wrapper.text()).toContain('昨日')
    expect(wrapper.text()).toContain('7日')
    expect(wrapper.text()).toContain('30日')
    expect(wrapper.text()).toContain('90日')
    expect(wrapper.text()).toContain('自定义')
    expect(wrapper.text()).toContain('2026-07-20 · 单日功率')
    const option = chart.optionFactory()
    expect(option.xAxis.data).toHaveLength(96)
    expect(option.series[0].data).toHaveLength(96)
    expect(option.series[0].data[1]).toBeNull()
    expect(option.series[0].connectNulls).toBe(false)
  })

  it('无日期记录时显示空态并保留图表宿主节点', () => {
    const wrapper = mount(TieLinePowerTrend, {
      props: {
        trend: { startDate: '2026-07-14', endDate: '2026-07-20', dataDateCount: 0, points: points.map((point) => ({ ...point, powerMw: null })) },
        range: { key: 'sevenDays', startDate: '2026-07-14', endDate: '2026-07-20' },
      },
      global: { stubs: { ElDialog: true, ElDatePicker: true } },
    })

    expect(wrapper.text()).toContain('该线路在所选日期范围内暂无功率数据')
    expect(wrapper.find('.tl-power-trend__canvas').exists()).toBe(true)
  })

  it('加载态保留图表宿主节点，避免 ECharts 初始化到空 DOM', async () => {
    const wrapper = mount(TieLinePowerTrend, {
      props: {
        loading: true,
        range: { key: 'yesterday', startDate: '2026-07-20', endDate: '2026-07-20' },
      },
      global: { stubs: { ElDialog: true, ElDatePicker: true } },
    })

    expect(wrapper.find('.tl-power-trend__canvas').exists()).toBe(true)
    await wrapper.findAll('.tl-power-trend__range')[1].trigger('click')
    expect(wrapper.emitted('range-change')?.[0]?.[0]).toMatchObject({ key: 'sevenDays' })
  })

  it('点击快捷日期按钮时发出范围切换事件', async () => {
    const wrapper = mount(TieLinePowerTrend, {
      props: {
        trend: { startDate: '2026-07-20', endDate: '2026-07-20', dataDateCount: 1, points },
        range: { key: 'yesterday', startDate: '2026-07-20', endDate: '2026-07-20' },
      },
      global: { stubs: { ElDialog: true, ElDatePicker: true } },
    })

    await wrapper.findAll('.tl-power-trend__range')[1].trigger('click')

    expect(wrapper.emitted('range-change')?.[0]?.[0]).toMatchObject({ key: 'sevenDays' })
  })

  it('无真实数据时保留坐标区域、零轴和额定容量虚线，不绘制模拟曲线', () => {
    mount(TieLinePowerTrend, {
      props: {
        accentToken: '--xc-map-voltage-4',
        ratedCapacityMw: 4000,
        trend: { startDate: '2026-07-20', endDate: '2026-07-20', dataDateCount: 0, points: points.map((point) => ({ ...point, powerMw: null })) },
        range: { key: 'yesterday', startDate: '2026-07-20', endDate: '2026-07-20' },
      },
      global: { stubs: { ElDialog: true, ElDatePicker: true } },
    })

    const option = chart.optionFactory()
    expect(option.series[0].data.every((value) => value === null)).toBe(true)
    expect(option.series[0].lineStyle.color).toBe('--xc-map-voltage-4')
    expect(option.series[0].markLine.data).toEqual(expect.arrayContaining([{ yAxis: 0 }, { yAxis: 4000, name: '额定容量' }]))
    expect(option.graphic[0].style.text).toContain('暂无实时功率数据')
    expect(option.graphic[0].style.text).toContain('数据源尚未接入')
  })

  it('为纵轴单位预留顶部空间，避免 MW 被日期按钮遮挡', () => {
    mount(TieLinePowerTrend, {
      props: {
        trend: { startDate: '2026-07-20', endDate: '2026-07-20', dataDateCount: 1, points },
        range: { key: 'yesterday', startDate: '2026-07-20', endDate: '2026-07-20' },
      },
      global: { stubs: { ElDialog: true, ElDatePicker: true } },
    })

    const option = chart.optionFactory()
    expect(option.grid.top).toBeGreaterThanOrEqual(36)
    expect(option.yAxis.nameGap).toBeGreaterThanOrEqual(10)
    expect(option.yAxis.nameLocation).toBe('end')
  })

  it('使用更紧凑的图表高度，减少趋势图下方空白', () => {
    expect(styles).toContain('height: 188px')
    expect(styles).toContain('min-height: 188px')
    expect(styles).toContain('height: 128px')
  })

  it('日期按钮使用自适应网格且隐藏图表不拦截点击', () => {
    expect(styles).toContain('repeat(auto-fit, minmax(58px, 1fr))')
    expect(styles).toContain('pointer-events: none')
  })

  it('加载失败时发出重试事件', async () => {
    const wrapper = mount(TieLinePowerTrend, {
      props: {
        error: '功率趋势加载失败，请稍后重试',
        range: { key: 'yesterday', startDate: '2026-07-20', endDate: '2026-07-20' },
      },
      global: { stubs: { ElDialog: true, ElDatePicker: true } },
    })

    await wrapper.get('[data-test="retry-power-trend"]').trigger('click')
    expect(wrapper.emitted('retry')).toHaveLength(1)
  })
})

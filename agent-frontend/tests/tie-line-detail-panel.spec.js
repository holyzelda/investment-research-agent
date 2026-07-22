import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import TieLineDetailPanel from '@/views/tie-line/components/TieLineDetailPanel.vue'
import tieLineDetailPanelSource from '@/views/tie-line/components/TieLineDetailPanel.vue?raw'

const line = {
  id: 1,
  name: '甲乙线',
  startPoint: '甲站',
  endPoint: '乙站',
  startRegion: '西北',
  endRegion: '华南',
  voltageText: '±800 kV',
  ratedCapacityMw: 4000,
  operationYear: 2020,
}

const TieLinePowerTrendStub = {
  template: '<section data-test="power-trend">功率趋势组件</section>',
}

const mountPanel = (props = {}) => mount(TieLineDetailPanel, {
  props,
  global: { stubs: { TieLinePowerTrend: TieLinePowerTrendStub } },
})
const styles = tieLineDetailPanelSource.match(/<style scoped>([\s\S]*)<\/style>/)?.[1] || ''

describe('联络线详情面板', () => {
  it('以线路名片、微型线路图和两列关键指标展示线路档案', () => {
    const wrapper = mountPanel({ line, accentToken: '--xc-map-voltage-4' })

    const title = wrapper.find('.tl-profile__name')
    expect(wrapper.find('.tl-profile__eyebrow').text()).toBe('线路档案')
    expect(title.text()).toBe('甲乙线')
    expect(title.attributes('style')).toContain('var(--xc-map-voltage-4)')
    expect(wrapper.find('.tl-profile__type').text()).toBe('跨区直流输电线路')
    expect(wrapper.find('.tl-profile__voltage').exists()).toBe(false)
    expect(wrapper.find('.tl-mini-route').exists()).toBe(true)
    expect(wrapper.find('.tl-mini-route__station--start').text()).toContain('甲站')
    expect(wrapper.find('.tl-mini-route__station--start').text()).toContain('西北')
    expect(wrapper.find('.tl-mini-route__station--end').text()).toContain('乙站')
    expect(wrapper.find('.tl-mini-route__station--end').text()).toContain('华南')
    expect(wrapper.find('.tl-metric-strip').exists()).toBe(true)
    expect(wrapper.findAll('.tl-metric-strip__item')).toHaveLength(4)
    expect(wrapper.text()).toContain('额定容量')
    expect(wrapper.text()).toContain('电压等级')
    expect(wrapper.text()).toContain('线路长度')
    expect(wrapper.text()).toContain('投运年份')
    expect(wrapper.text()).toContain('4,000 MW')
    expect(wrapper.text()).toContain('±800 kV')
    expect(styles).toContain('grid-template-columns:repeat(2, minmax(0, 1fr))')
    expect(wrapper.findAll('.tl-detail__metric')).toHaveLength(0)
    expect(wrapper.text()).not.toContain('起始区域')
    expect(wrapper.find('[data-test="power-trend"]').exists()).toBe(true)
  })

  it('支持未知电压的强调色 token', () => {
    const wrapper = mountPanel({ line, accentToken: '--xc-map-voltage-unknown' })

    expect(wrapper.find('.tl-profile__name').attributes('style')).toContain(
      'var(--xc-map-voltage-unknown)',
    )
  })

  it('无线路时直接展示最长线路详情', () => {
    const recommendedLine = { ...line, id: 2, name: '乙丙线', lengthText: '2,383 km' }
    const wrapper = mountPanel({
      recommendedLine,
    })

    expect(wrapper.find('.tl-profile__name').text()).toBe('乙丙线')
    expect(wrapper.text()).toContain('甲站')
    expect(wrapper.text()).toContain('乙站')
    expect(wrapper.text()).toContain('2,383 km')
    expect(wrapper.find('.tl-detail__placeholder').exists()).toBe(false)
    expect(wrapper.find('[data-test="power-trend"]').exists()).toBe(false)
  })

  it('透传功率趋势范围切换事件', async () => {
    const wrapper = mountPanel({
      line,
      powerTrend: { startDate: '2026-07-20', endDate: '2026-07-20', dataDateCount: 1, points: [] },
      powerRange: { key: 'yesterday', startDate: '2026-07-20', endDate: '2026-07-20' },
    })

    wrapper.findComponent(TieLinePowerTrendStub).vm.$emit('range-change', {
      key: 'sevenDays', startDate: '2026-07-14', endDate: '2026-07-20',
    })

    expect(wrapper.emitted('power-range-change')?.[0]?.[0]).toEqual({
      key: 'sevenDays', startDate: '2026-07-14', endDate: '2026-07-20',
    })
  })

  it('详情面板使用紧凑内边距并在窄屏下指标退为单列', () => {
    expect(styles).toContain('padding: var(--xc-space-4)')
    expect(styles).toContain('@media (max-width: 1180px)')
    expect(styles).toContain('grid-template-columns:1fr')
  })

  it('数据口径默认显示摘要，点击后展开完整说明', async () => {
    const wrapper = mountPanel({
      line: {
        ...line,
        coordinateBasis: '换流站经纬度',
        dataBasisNote: '额定容量来自公开资料',
        sourceNote: '公开资料整理，含长期长文本说明',
      },
    })

    expect(wrapper.find('.tl-data-basis__summary').text()).toContain('换流站经纬度')
    expect(wrapper.text()).not.toContain('公开资料整理，含长期长文本说明')
    await wrapper.find('.tl-data-basis__toggle').trigger('click')
    expect(wrapper.text()).toContain('坐标基准：换流站经纬度')
    expect(wrapper.text()).toContain('数据说明：额定容量来自公开资料')
    expect(wrapper.text()).toContain('来源备注：公开资料整理，含长期长文本说明')
  })

  it('关键长文本区域不使用省略号截断', () => {
    expect(styles).not.toContain('text-overflow: ellipsis')
    expect(styles).not.toContain('white-space: nowrap')
  })

  it('无线路且无推荐时保留引导空态', () => {
    const wrapper = mountPanel()

    expect(wrapper.find('.tl-detail__title').exists()).toBe(false)
    expect(wrapper.find('.tl-detail__recommend-card').exists()).toBe(false)
    expect(wrapper.text()).toContain('点击地图上的联络线查看线路详情')
  })

  it('当前筛选条件没有线路时展示筛选空态', () => {
    const wrapper = mountPanel({ noVisibleLines: true })

    expect(wrapper.text()).toContain('当前筛选条件下暂无线路')
    expect(wrapper.text()).not.toContain('点击地图上的联络线查看线路详情')
  })

  it('已选线路优先于默认最长线路', () => {
    const wrapper = mountPanel({ line, recommendedLine: { ...line, id: 2, name: '乙丙线' } })

    expect(wrapper.find('.tl-profile__name').text()).toBe('甲乙线')
  })
})

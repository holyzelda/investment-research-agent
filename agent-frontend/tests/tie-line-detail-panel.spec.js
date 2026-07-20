import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import TieLineDetailPanel from '@/views/tie-line/components/TieLineDetailPanel.vue'

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

describe('联络线详情面板', () => {
  it('使用线路强调色 token 渲染标题', () => {
    const wrapper = mount(TieLineDetailPanel, {
      props: { line, accentToken: '--xc-map-voltage-4' },
    })

    const title = wrapper.find('.tl-detail__title')
    expect(title.text()).toBe('甲乙线')
    expect(title.attributes('style')).toContain('var(--xc-map-voltage-4)')
    expect(wrapper.text()).toContain('甲站')
    expect(wrapper.text()).toContain('乙站')
    expect(wrapper.text()).toContain('4,000 MW')
  })

  it('支持未知电压的强调色 token', () => {
    const wrapper = mount(TieLineDetailPanel, {
      props: { line, accentToken: '--xc-map-voltage-unknown' },
    })

    expect(wrapper.find('.tl-detail__title').attributes('style')).toContain(
      'var(--xc-map-voltage-unknown)',
    )
  })

  it('无线路时直接展示最长线路详情', () => {
    const recommendedLine = { ...line, id: 2, name: '乙丙线', lengthText: '2,383 km' }
    const wrapper = mount(TieLineDetailPanel, { props: { recommendedLine } })

    expect(wrapper.find('.tl-detail__title').text()).toBe('乙丙线')
    expect(wrapper.text()).toContain('甲站')
    expect(wrapper.text()).toContain('乙站')
    expect(wrapper.text()).toContain('2,383 km')
    expect(wrapper.find('.tl-detail__placeholder').exists()).toBe(false)
  })

  it('无线路且无推荐时保留引导空态', () => {
    const wrapper = mount(TieLineDetailPanel)

    expect(wrapper.find('.tl-detail__title').exists()).toBe(false)
    expect(wrapper.find('.tl-detail__recommend-card').exists()).toBe(false)
    expect(wrapper.text()).toContain('点击地图上的联络线查看线路详情')
  })

  it('已选线路优先于默认最长线路', () => {
    const wrapper = mount(TieLineDetailPanel, { props: { line, recommendedLine: { ...line, id: 2, name: '乙丙线' } } })

    expect(wrapper.find('.tl-detail__title').text()).toBe('甲乙线')
  })
})

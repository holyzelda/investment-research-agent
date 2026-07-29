import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ProvinceIndexDetail from '@/views/index-map/components/ProvinceIndexDetail.vue'

const detail = {
  provinceName: '蒙西', grade: 'S', indexScore: 95, investmentAdvice: '强烈推荐·立即布局', annualizedReturn: 8.9,
  maturity: { summary: '成熟', scores: [{ key: 'spot', label: '现货', score: 92 }] },
  factorContributions: [{ key: 'spot', label: '现货价差', value: 90, delta: 23 }],
  installedStructure: { totalGw: 208, items: [{ key: 'renewable', label: '新能源', share: 59, windShare: 26.26, solarShare: 73.74, capacityGw: 122.4, description: '', deltaText: '↑31%' }, { key: 'thermal', label: '火电', share: 38, capacityGw: 78.2, description: '火电装机', deltaText: '↓0.34%' }, { key: 'storage', label: '储能', share: 4, capacityGw: 7.4, description: '新型储能' }] },
}

describe('省份指数详情', () => {
  it('完整显示原型定义的省份详情分区', () => {
    const wrapper = mount(ProvinceIndexDetail, { props: { detail, loading: false, error: '' } })
    expect(wrapper.text()).toContain('蒙西')
    expect(wrapper.text()).toContain('强烈推荐·立即布局')
    expect(wrapper.text()).toContain('市场化成熟度')
    expect(wrapper.text()).toContain('因子贡献度')
    expect(wrapper.text()).toContain('装机结构')
    expect(wrapper.text()).toContain('新能源')
    expect(wrapper.text()).toContain('火电')
    expect(wrapper.text()).toContain('储能')
    expect(wrapper.text()).toContain('122.4 GW')
    expect(wrapper.text()).toContain('风电 26.26% · 光伏 73.74%')
    expect(wrapper.text()).toContain('↑31%')
    expect(wrapper.findAll('.province-detail__capacity')).toHaveLength(3)
    expect(wrapper.find('.province-detail__capacity--renewable').exists()).toBe(true)
    expect(wrapper.find('.province-detail__capacity--thermal .is-down').text()).toBe('↓0.34%')
    expect(wrapper.find('.province-detail__capacity--storage .province-detail__capacity-value > span').exists()).toBe(false)
  })

  it('详情请求失败时发出重试事件', async () => {
    const wrapper = mount(ProvinceIndexDetail, { props: { detail: null, loading: false, error: '加载失败' } })
    await wrapper.get('button').trigger('click')
    expect(wrapper.emitted('retry')).toEqual([[]])
  })
})

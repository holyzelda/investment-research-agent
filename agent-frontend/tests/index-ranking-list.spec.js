import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import IndexRankingList from '@/views/index-map/components/IndexRankingList.vue'

const items = [
  { provinceCode: 'NX', provinceName: '宁夏', rank: 2, indexScore: 92, annualizedReturn: 98 },
  { provinceCode: 'SX', provinceName: '山西', rank: 1, indexScore: 93, annualizedReturn: 87 },
]

describe('全国指数排行榜', () => {
  it('传入 valueKey 时按该字段显示分数并带后缀', () => {
    const wrapper = mount(IndexRankingList, {
      props: { title: '收益稳定榜', items, valueKey: 'annualizedReturn', suffix: '分' },
    })
    const rows = wrapper.findAll('button')
    expect(rows).toHaveLength(2)
    expect(rows[0].text()).toContain('宁夏')
    expect(rows[0].text()).toContain('98分')
    expect(rows[1].text()).toContain('87分')
  })

  it('未传 valueKey 时不渲染分数列', () => {
    const wrapper = mount(IndexRankingList, { props: { title: '收益稳定榜', items } })
    expect(wrapper.find('button strong').exists()).toBe(false)
  })
})

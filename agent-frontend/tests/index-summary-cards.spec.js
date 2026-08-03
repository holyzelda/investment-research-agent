import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import IndexSummaryCards from '@/views/index-map/components/IndexSummaryCards.vue'

const summary = {
  nationalAverage: 82.1,
  leader: { provinceName: '山西', indexScore: 93 },
  openedProvinceCount: 10,
  openedGradeCounts: { S: 2, A: 5, B: 2, C: 1 },
  highPotentialCount: 6,
}

describe('全国指数摘要卡', () => {
  it('已开通区域展示 S/A/B/C 四档计数', () => {
    const wrapper = mount(IndexSummaryCards, { props: { summary } })
    const text = wrapper.text()
    expect(text).toContain('S 2')
    expect(text).toContain('A 5')
    expect(text).toContain('B 2')
    expect(text).toContain('C 1')
    expect(text).toContain('10')
  })

  it('第四张卡为“C 类区域”而非“高潜待挖掘/待开通”', () => {
    const wrapper = mount(IndexSummaryCards, { props: { summary } })
    const text = wrapper.text()
    expect(text).toContain('C 类区域')
    expect(text).toContain('已开通 C 类')
    expect(text).not.toContain('高潜待挖掘')
    expect(text).not.toContain('待开通')
  })

  it('缺失计数时回退为 0', () => {
    const wrapper = mount(IndexSummaryCards, { props: { summary: { openedProvinceCount: 0 } } })
    expect(wrapper.text()).toContain('S 0')
    expect(wrapper.text()).toContain('C 0')
  })
})

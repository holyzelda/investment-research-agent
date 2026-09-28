import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import IndexSummaryCards from '@/views/index-map/components/IndexSummaryCards.vue'

const summarySource = readFileSync(
  resolve(process.cwd(), 'src/views/index-map/components/IndexSummaryCards.vue'),
  'utf8',
)

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

  it('缺失计数时回退为 0', () => {
    const wrapper = mount(IndexSummaryCards, { props: { summary: { openedProvinceCount: 0 } } })
    expect(wrapper.text()).toContain('S 0')
    expect(wrapper.text()).toContain('C 0')
  })

  it('renders four independent compact cards without left markers', () => {
    const wrapper = mount(IndexSummaryCards, { props: { summary } })
    expect(wrapper.findAll('article')).toHaveLength(4)
    expect(summarySource).toContain('grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px;')
    expect(summarySource).toContain('min-height: 60px; padding: 7px 14px;')
    expect(summarySource).toContain('border-radius: 12px; background: var(--xc-surface-raised);')
    expect(summarySource).not.toContain('article::before')
    expect(summarySource).not.toContain('linear-gradient(180deg, #4fd8e2, #8067ff)')
  })
})

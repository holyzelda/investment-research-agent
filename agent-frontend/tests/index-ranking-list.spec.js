import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import IndexRankingList from '@/views/index-map/components/IndexRankingList.vue'

const rankingSource = readFileSync(
  resolve(process.cwd(), 'src/views/index-map/components/IndexRankingList.vue'),
  'utf8',
)

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

  it('选中行和悬停行复用侧栏高亮背景并保留蓝色竖线', () => {
    expect(rankingSource).toContain('button:hover { background: var(--xc-surface-control);')
    expect(rankingSource).toContain('button.is-active { background: var(--xc-surface-control);')
    expect(rankingSource).toContain('button.is-active::before { background: var(--xc-accent-blue); }')
  })

  it('uses the ZRA-3 ranking typography while preserving hover and selected styles', () => {
    expect(rankingSource).toContain('gap: 11px; min-width: 0; min-height: 32px; padding: 6px 11px;')
    expect(rankingSource).toContain('border-radius: 10px; background: transparent;')
    expect(rankingSource).toContain('.index-ranking__name { overflow: hidden; color: var(--xc-text-strong); font-size: 13px; font-weight: 600;')
    expect(rankingSource).toContain('button strong { color: var(--xc-text-strong); font-size: 14px; font-weight: 700; }')
  })

  it('adds the matching title icon and top-three rank badges', () => {
    const heat = mount(IndexRankingList, { props: { title: '投资热力榜', items } })
    const stability = mount(IndexRankingList, { props: { title: '收益稳定榜', items } })
    expect(heat.find('h3 svg').exists()).toBe(true)
    expect(stability.find('h3 svg').exists()).toBe(true)
    expect(heat.get('.index-ranking__rank').classes()).toContain('is-rank-2')
    expect(rankingSource).toContain('.index-ranking__rank.is-rank-1')
    expect(rankingSource).toContain('.index-ranking__rank.is-rank-2')
    expect(rankingSource).toContain('.index-ranking__rank.is-rank-3')
  })
})

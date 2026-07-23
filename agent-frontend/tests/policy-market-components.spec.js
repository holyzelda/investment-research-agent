import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('element-plus', () => ({
  ElDialog: {},
}))
vi.mock('element-plus/es', () => ({
  ElDialog: {},
}))
import ConsultationComposer from '@/views/policy-market/components/ConsultationComposer.vue'
import ConsultationHistory from '@/views/policy-market/components/ConsultationHistory.vue'
import ConsultationResult from '@/views/policy-market/components/ConsultationResult.vue'
import MarketPulse from '@/views/policy-market/components/MarketPulse.vue'
import NewsDetailDialog from '@/views/policy-market/components/NewsDetailDialog.vue'

describe('政策与市场咨询组件', () => {
  it('历史列表发出新建和选择事件，不渲染删除动作', async () => {
    const wrapper = mount(ConsultationHistory, {
      props: {
        consultations: [{ id: 'c-1', title: '新能源消纳政策有何变化？', createdAt: '2026-07-23T10:42:00+08:00' }],
        selectedId: 'c-1',
      },
    })

    expect(wrapper.text()).not.toContain('删除')
    await wrapper.get('[aria-label="新建提问"]').trigger('click')
    await wrapper.get('[data-consultation-id="c-1"]').trigger('click')
    expect(wrapper.emitted('new-question')).toHaveLength(1)
    expect(wrapper.emitted('select')).toEqual([['c-1']])
  })

  it('快捷问题填入输入框，Ctrl+Enter 发出提交事件', async () => {
    const wrapper = mount(ConsultationComposer)

    await wrapper.get('[data-quick-question]').trigger('click')
    expect(wrapper.get('textarea').element.value).toBeTruthy()
    await wrapper.get('textarea').trigger('keydown', { key: 'Enter', ctrlKey: true })
    expect(wrapper.emitted('submit-question')?.[0]?.[0]).toBeTruthy()
  })

  it('空输入不提交并显示结果区空态', async () => {
    const composer = mount(ConsultationComposer)
    const result = mount(ConsultationResult, { props: { consultation: null } })

    await composer.get('[aria-label="提交咨询"]').trigger('click')
    expect(composer.emitted('submit-question')).toBeUndefined()
    expect(result.text()).toContain('你的咨询结果将展示在这里')
  })

  it('按咨询状态显示处理中、失败和完成结果', () => {
    const processing = mount(ConsultationResult, { props: { consultation: { status: 'processing', question: '问题' } } })
    const failed = mount(ConsultationResult, { props: { consultation: { status: 'failed', question: '问题', answer: '' } } })
    const completed = mount(ConsultationResult, { props: { consultation: { status: 'completed', title: '问题', answer: '回答', sourceScope: ['政策文件'] } } })

    expect(processing.text()).toContain('正在分析')
    expect(failed.text()).toContain('咨询失败')
    expect(completed.text()).toContain('回答')
    expect(completed.text()).toContain('政策文件')
  })

  it('筛选变化时发出完整筛选条件，并可选择资讯', async () => {
    const wrapper = mount(MarketPulse, {
      props: {
        filters: { province: 'all', period: 'all', topic: 'all' },
        stats: { total: 186, trend: 9.3, rangeLabel: '内蒙古' },
        news: [{ id: 'n-1', category: '政策', title: '储能规模化发展', publishedAt: '2026-07-23T09:00:00+08:00' }],
      },
    })

    await wrapper.get('[data-filter="province"]').setValue('内蒙古')
    await wrapper.get('[data-news-id="n-1"]').trigger('click')
    expect(wrapper.emitted('filters-change')?.[0]?.[0]).toMatchObject({ province: '内蒙古' })
    expect(wrapper.emitted('open-news')).toEqual([['n-1']])
  })

  it('资讯详情弹窗展示正文和来源', () => {
    const wrapper = mount(NewsDetailDialog, {
      props: {
        modelValue: true,
        news: { category: '政策', title: '储能规模化发展', publishedAt: '2026-07-23T09:00:00+08:00', content: '正文内容', source: '公开信息整理' },
      },
      global: { stubs: { ElDialog: { template: '<div><slot /><slot name="header" /></div>' } } },
    })

    expect(wrapper.text()).toContain('正文内容')
    expect(wrapper.text()).toContain('公开信息整理')
  })
})

import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ReportGenerationCard from '@/views/home/components/ReportGenerationCard.vue'

describe('ReportGenerationCard', () => {
  const context = {
    projectName: '甘肃 · 祥泰站储能项目',
    version: 'V2',
    powerText: '100 MW',
    capacityText: '400 MWh',
  }

  it('生成中展示交付上下文且不重复思考进度', () => {
    const wrapper = mount(ReportGenerationCard, {
      props: { ...context, status: 'generating' },
    })

    expect(wrapper.text()).toContain('生成中')
    expect(wrapper.text()).toContain('甘肃 · 祥泰站储能项目')
    expect(wrapper.text()).toContain('V2')
    expect(wrapper.text()).toContain('AI 正在生成正式投资分析报告')
    expect(wrapper.text()).toContain('报告生成完成后将自动存入项目档案')
    expect(wrapper.find('.ir-report-delivery__hero-mark--generating').exists()).toBe(true)
    expect(wrapper.find('.ir-report-delivery__details').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('报告包含 6 个分析章节')
    expect(wrapper.text()).not.toContain('AI 共生成')
    expect(wrapper.text()).not.toContain('20+ 项财务指标')
    expect(wrapper.text()).not.toContain('立即查看完整报告')
    expect(wrapper.find('.ir-thinking').exists()).toBe(false)
    expect(wrapper.find('button').exists()).toBe(false)
  })

  it('完成后展示完整报告摘要并提供两个报告操作', async () => {
    const wrapper = mount(ReportGenerationCard, {
      props: { ...context, status: 'completed', reportId: 'r-2', archived: true },
    })

    expect(wrapper.text()).toContain('已完成')
    expect(wrapper.text()).toContain('AI 已生成正式投资分析报告')
    expect(wrapper.text()).toContain('已存入项目档案')
    expect(wrapper.text()).toContain('支持 PDF 导出')
    expect(wrapper.text()).toContain('20+ 项财务指标')
    expect(wrapper.text()).toContain('5 项深度分析')
    expect(wrapper.text()).toContain('约 15 页报告')
    expect(wrapper.text()).toContain('预计阅读 8–10 分钟')
    expect(wrapper.text()).toContain('市场与政策')
    expect(wrapper.text()).toContain('项目测算边界')
    expect(wrapper.text()).toContain('敏感情景测试')
    expect(wrapper.text()).toContain('结论与投资建议')
    expect(wrapper.findAll('.ir-report-delivery__chapters li')).toHaveLength(6)
    expect(wrapper.findAll('.ir-report-delivery__summary .xc-num').length).toBeGreaterThanOrEqual(5)

    await wrapper.find('.ir-report-delivery__primary-action').trigger('click')
    expect(wrapper.emitted('view')[0]).toEqual(['r-2'])

    await wrapper.find('.ir-report-delivery__history-action').trigger('click')
    expect(wrapper.emitted('view-history')[0]).toEqual(['r-2'])
  })

  it('失败时展示原因并允许按原测算任务重试', async () => {
    const wrapper = mount(ReportGenerationCard, {
      props: { ...context, status: 'failed', taskId: 42, errorMessage: '中台调用失败' },
    })

    expect(wrapper.text()).toContain('生成失败')
    expect(wrapper.text()).toContain('中台调用失败')
    expect(wrapper.text()).not.toContain('立即查看完整报告')
    expect(wrapper.text()).not.toContain('20+ 项财务指标')
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('retry')[0]).toEqual([42])
  })

  it('历史元数据缺失时使用安全占位且不提供无效操作', () => {
    const wrapper = mount(ReportGenerationCard, {
      props: { status: 'completed' },
    })

    expect(wrapper.text()).toContain('储能投资项目')
    expect(wrapper.text()).toContain('—')
    expect(wrapper.find('.ir-report-delivery__primary-action').exists()).toBe(false)
    expect(wrapper.find('.ir-report-delivery__history-action').exists()).toBe(false)
    expect(wrapper.find('button').exists()).toBe(false)
  })
})

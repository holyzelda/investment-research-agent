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
    expect(wrapper.text()).toContain('项目概览')
    expect(wrapper.text()).toContain('完成后将存入项目档案')
    expect(wrapper.find('.ir-thinking').exists()).toBe(false)
    expect(wrapper.find('button').exists()).toBe(false)
  })

  it('完成后提供报告查看操作和归档提示', async () => {
    const wrapper = mount(ReportGenerationCard, {
      props: { ...context, status: 'completed', reportId: 'r-2', archived: true },
    })

    expect(wrapper.text()).toContain('已完成')
    expect(wrapper.text()).toContain('已存入项目档案')
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('view')[0]).toEqual(['r-2'])
  })

  it('失败时展示原因并允许按原测算任务重试', async () => {
    const wrapper = mount(ReportGenerationCard, {
      props: { ...context, status: 'failed', taskId: 42, errorMessage: '中台调用失败' },
    })

    expect(wrapper.text()).toContain('生成失败')
    expect(wrapper.text()).toContain('中台调用失败')
    expect(wrapper.text()).not.toContain('查看正式报告')
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('retry')[0]).toEqual([42])
  })

  it('历史元数据缺失时使用安全占位且不提供无效操作', () => {
    const wrapper = mount(ReportGenerationCard, {
      props: { status: 'completed' },
    })

    expect(wrapper.text()).toContain('储能投资项目')
    expect(wrapper.text()).toContain('—')
    expect(wrapper.find('button').exists()).toBe(false)
  })
})

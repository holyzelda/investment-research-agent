import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const api = vi.hoisted(() => ({
  getConversation: vi.fn(),
  getCalculationResult: vi.fn(),
}))
const route = vi.hoisted(() => ({ params: { conversationId: 'conversation-2', taskId: '77' } }))

vi.mock('@/api/calc', () => api)
vi.mock('vue-router', () => ({ useRoute: () => route }))
vi.mock('echarts', () => ({
  init: () => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn(), on: vi.fn() }),
}))

import CalculationResultReadonly from '@/views/calculation-result/index.vue'

const DETAIL = {
  data: {
    conversationId: 'conversation-2',
    title: '宁夏 独立储能',
    versions: [
      {
        taskId: 76,
        version: 'V1',
        calculatedAt: '2026-08-11T09:00:00',
        result: { basicInfo: { province: '宁夏', powerMw: 50 }, financial: { projectIrr: 6.1 } },
      },
      {
        taskId: 77,
        version: 'V2',
        calculatedAt: '2026-08-12T10:30:00',
        result: {
          basicInfo: { province: '宁夏', nodeName: '银川节点', powerMw: 100, capacityMwh: 200 },
          financial: { projectIrr: 8.2 },
          advanced: { donut: {}, debtServiceCoverage: {} },
        },
      },
    ],
  },
}

describe('CalculationResultReadonly', () => {
  it('renders exactly the version named by the route task id', async () => {
    api.getConversation.mockResolvedValue(DETAIL)
    api.getCalculationResult.mockResolvedValue({ data: DETAIL.data.versions[1].result })

    const wrapper = mount(CalculationResultReadonly)
    await flushPromises()

    expect(api.getConversation).toHaveBeenCalledWith('conversation-2')
    expect(wrapper.text()).toContain('宁夏 独立储能')
    expect(wrapper.text()).toContain('V2')
    expect(wrapper.text()).not.toContain('V1')
    expect(wrapper.text()).toContain('100')
    expect(wrapper.find('.ir-share-result').exists()).toBe(true)
  })

  it('offers no write actions at all', async () => {
    api.getConversation.mockResolvedValue(DETAIL)
    api.getCalculationResult.mockResolvedValue({ data: DETAIL.data.versions[1].result })

    const wrapper = mount(CalculationResultReadonly)
    await flushPromises()

    expect(wrapper.findAll('button')).toHaveLength(0)
    expect(wrapper.findAll('textarea')).toHaveLength(0)
    expect(wrapper.text()).not.toContain('调整参数')
    expect(wrapper.text()).not.toContain('重新测算')
    expect(wrapper.text()).not.toContain('生成报告')
  })

  it('reports a missing version instead of falling back to the latest one', async () => {
    api.getConversation.mockResolvedValue({ data: { title: '宁夏 独立储能', versions: [DETAIL.data.versions[0]] } })

    const wrapper = mount(CalculationResultReadonly)
    await flushPromises()

    expect(wrapper.text()).toContain('未找到该测算版本的结果')
    expect(wrapper.find('.ir-share-result').exists()).toBe(false)
  })

  it('shows an access message when the record is not visible', async () => {
    api.getConversation.mockRejectedValue({ response: { status: 404 } })

    const wrapper = mount(CalculationResultReadonly)
    await flushPromises()

    expect(wrapper.text()).toContain('测算记录不存在或无权查看')
  })
})

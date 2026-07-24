import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

const route = vi.hoisted(() => ({ params: { reportId: 'r-1' } }))
const router = vi.hoisted(() => ({ back: vi.fn() }))
const captured = vi.hoisted(() => ({ factories: [] }))
vi.mock('@/views/home/composables/useEcharts', () => ({
  useEcharts: (factory) => {
    captured.factories.push(factory)
    return { el: ref(null) }
  },
  xcChartColors: () => ['#3d6f9d', '#b85c38', '#5b8966', '#b69145', '#8879a8', '#6f8999'],
  xcVar: () => '#45515e',
}))
vi.mock('@/api/report', () => ({ getReport: vi.fn().mockResolvedValue({ data: null }) }))
vi.mock('vue-router', () => ({ useRoute: () => route, useRouter: () => router }))

import ReportDetail from '@/views/report/index.vue'

describe('formal report preview', () => {
  beforeEach(() => { captured.factories.length = 0 })

  it('renders the six template chapters, six charts, and print action from a frozen report', async () => {
    const wrapper = mount(ReportDetail, { global: { stubs: { 'el-button': true, 'el-empty': true } } })
    wrapper.vm.report = {
      title: '甘肃200MW/800MWh储能项目测算方案',
      generatedDate: '2026-07-23',
      project: { province: '甘肃', nodeName: '兰州东', powerMw: 200, capacityMwh: 800, durationHours: 4 },
      policyEnvironment: { marketStatus: {}, projectImpact: {} },
      marketOperations: {}, measurementBoundary: {}, financialMetrics: {},
      calculation: { result: { advanced: { donut: {}, debtServiceCoverage: {} } } },
      charts: {
        operationYears: 15,
        series: {
          debtServiceCoverage: [1.2, 1.4], freeCashflow: [20, 30], operatingCashflow: [50, 60],
          principal: [10, 10], interest: [5, 4], netProfit: [12, 14], depreciationAmortization: [8, 8],
        },
        sensitivity: { baseline: 1.5, optimistic: 1.7, pessimistic: 1.1 },
      },
      aiSections: {},
    }
    await nextTick()

    expect(wrapper.text()).toContain('第一章项目基本信息')
    expect(wrapper.text()).toContain('第二章市场供需与政策环境')
    expect(wrapper.text()).toContain('第三章项目测算边界')
    expect(wrapper.text()).toContain('第四章主模型分析')
    expect(wrapper.text()).toContain('第五章敏感情景测试')
    expect(wrapper.text()).toContain('第六章结论与投资建议')
    expect(wrapper.findAll('.ir-report-chart')).toHaveLength(6)
    expect(wrapper.find('.ir-report-document').exists()).toBe(true)
    expect(wrapper.text()).toContain('导出 PDF')
  })
})

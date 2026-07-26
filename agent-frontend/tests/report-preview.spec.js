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

  it('renders the approved cover through chapter three from a frozen report', async () => {
    const wrapper = mount(ReportDetail)
    wrapper.vm.report = {
      title: '甘肃200MW/800MWh储能项目测算方案',
      generatedDate: '2026-07-24',
      project: {
        name: '甘肃200MW/800MWh独立储能项目',
        province: '甘肃', nodeName: '兰州东', powerMw: 200, capacityMwh: 800, durationHours: 4,
        preparer: '西安奇点能源股份有限公司', projectType: '源网侧', singularityRole: '设备商+运营商',
      },
      marketSupplyDemand: {
        energyStructure: '新能源与火电结构。', storage: '独立储能项目储备。', generation: '发电量稳步增长。',
        consumption: '全社会用电量增长。', developmentPlan: '规划新增新能源装机。',
      },
      policyEnvironment: {
        rows: [
          { name: '中长期市场', enabled: true }, { name: '现货市场', enabled: false }, { name: '容量补偿', enabled: false },
          { name: '调频市场', enabled: true }, { name: '租赁市场', enabled: false }, { name: '补贴政策', enabled: true },
          { name: '干预补偿', enabled: false }, { name: '过网费优惠政策', enabled: true },
        ],
      },
      marketOperations: {
        spotChargePrice: 0.1234, spotDischargePrice: 0.5678, spotSpread: 0.4444,
        transmissionPrice: 0.0123, lineLossFee: 0.0034, systemOperationFee: 0.0056, governmentFundSurcharge: 0.0078,
        chargeCost: 0.3012, dischargeReturn: 0.0211, actualSpread: 0.2801,
      },
      calculation: {
        result: {
          advanced: {
            donut: { totalRevenue: 200, energyRevenue: 120, capacityRevenue: 80, frequencyRevenue: 0, leaseRevenue: 0, interventionRevenue: 0, subsidyRevenue: 0 },
          },
        },
      },
      measurementBoundary: {
        epcUnitPrice: 0.75, batteryReplaceCost: 0.3, equityRatio: 0.2, strategyAchievementRate: 0.9,
        annualOperationDays: 330, loanRate: 0.04, loanYears: 10, repaymentMethod: '等额本息', operationYears: 15,
        discountRate: 0.04, energyRevenueVatRate: 0.13, ancillaryServiceVatRate: 0.13,
        capacityCompensationVatRate: 0.13, capacityLeaseVatRate: 0.06, subsidyVatRate: 0.13,
        interventionCompensationVatRate: 0.09, incomeTaxRate: 0.25,
      }, financialMetrics: {},
      charts: { operationYears: 15, series: {}, sensitivity: {} },
      aiSections: {},
    }
    await nextTick()

    expect(wrapper.text()).toContain('储能参与中国电力市场')
    expect(wrapper.text()).toContain('前期项目测算方案')
    expect(wrapper.text()).toContain('项目名称：甘肃200MW/800MWh独立储能项目')
    expect(wrapper.text()).toContain('编制单位：西安奇点能源股份有限公司')
    expect(wrapper.text()).not.toContain('ENERGY STORAGE INVESTMENT REVIEW')
    expect(wrapper.text()).not.toContain('测算版本')
    expect(wrapper.text()).toContain('项目要素')
    expect(wrapper.text()).toContain('并网电压等级')
    expect(wrapper.text()).toContain('☑ 源网侧')
    expect(wrapper.text()).toContain('第二章：市场供需分析')
    expect(wrapper.text()).toContain('该项目处于甘肃，目前该省（地区）电力市场处于现货连续结算试运行阶段，该省能源结构如下：')
    expect(wrapper.text()).toContain('新能源与火电结构。')
    expect(wrapper.text()).toContain('储能：')
    expect(wrapper.text()).toContain('该省十五五规划如下：')
    expect(wrapper.text()).toContain('第三章 政策环境分析')
    expect(wrapper.text()).toContain('3.1 政策环境清单')
    expect(wrapper.text()).toContain('☑ 已启动')
    expect(wrapper.text()).toContain('☑ 未启动')
    expect(wrapper.text()).toContain('3.2 现货基础运营信息')
    expect(wrapper.text()).toContain('0.1234 元/kWh')
    expect(wrapper.text()).toContain('3.3 项目首年收益结构')
    expect(wrapper.find('.ir-report-revenue-layout').exists()).toBe(true)
    expect(wrapper.text()).toContain('第四章 项目测算边界')
    expect(wrapper.text()).toContain('4.1 测算边界参数')
    expect(wrapper.find('.ir-report-boundary-table').exists()).toBe(true)
    expect(wrapper.find('.ir-report-boundary-table').text()).toContain('参数类别')
    expect(wrapper.find('.ir-report-boundary-table').text()).toContain('取值依据')
    expect(wrapper.find('.ir-report-boundary-table').text()).toContain('电能量收入增值税')
    expect(wrapper.find('.ir-report-boundary-table').text()).toContain('13%')
    expect(wrapper.find('.ir-report-boundary-table').text()).toContain('容量租赁收入增值税')
    expect(wrapper.find('.ir-report-boundary-table').text()).toContain('6%')
    const revenueOption = captured.factories[0]()
    expect(revenueOption.tooltip.formatter({ name: '电能量', value: 12.34567, percent: 60 })).toContain('12.3457 万元')
    expect(wrapper.findAll('.ir-report-chapter-heading')).toHaveLength(7)
    expect(wrapper.findAll('.ir-report-chapter-heading').map((item) => item.text())).toEqual([
      '第一章 项目基本信息', '第二章：市场供需分析', '第三章 政策环境分析', '第四章 项目测算边界',
      '第五章 主模型分析', '第六章 敏感情景测试', '第七章 结论与投资建议',
    ])
    expect(wrapper.text()).toContain('导出 PDF')
  })
})

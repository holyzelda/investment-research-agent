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
      }, financialMetrics: {
        projectIrr: 8, capitalIrr: 12.3, projectStaticPayback: 9.1,
        averageProfit: 3200, averageRevenue: 4500.5, totalInvestmentRoi: 7.8,
      },
      charts: {
        operationYears: 15,
        series: {
          debtServiceCoverage: [1.4, 1.6, null, null], principal: [100.12345, 90.54321, null, null], interest: [20.23456, 10.65432, null, null],
          freeCashflow: [30.34567, 45.76543, null, null], operatingCashflow: [150.45678, 145.87654, null, null], netProfit: [40.12345, 55.54321], depreciationAmortization: [60.23456, 58.65432],
        },
        sensitivity: { baseline: 1.4567, optimistic: 1.6789, pessimistic: 0.9876 },
      },
      aiSections: {
        debt_service_coverage: { text: '本节智能分析暂未生成，不影响测算数据、图表及规则化内容的展示。' },
        operating_cashflow: { text: '本节智能分析暂未生成，不影响测算数据、图表及规则化内容的展示。' },
        accounting_profit: { text: '本节智能分析暂未生成，不影响测算数据、图表及规则化内容的展示。' },
      },
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
    expect(wrapper.text()).toContain('4.2 基准方案测算结果')
    expect(wrapper.find('.ir-report-financial-table').exists()).toBe(true)
    expect(wrapper.find('.ir-report-financial-table').text()).toContain('全投资财务内部收益率（IRR）')
    expect(wrapper.find('.ir-report-financial-table').text()).toContain('8.00')
    expect(wrapper.find('.ir-report-financial-table').text()).toContain('12.30')
    expect(wrapper.find('.ir-report-financial-table').text()).toContain('3200.00')
    expect(wrapper.find('.ir-report-financial-table').text()).toContain('4500.50')
    const revenueOption = captured.factories[0]()
    expect(revenueOption.tooltip.formatter({ name: '电能量', value: 12.34567, percent: 60 })).toContain('12.3457 万元')
    const coverageOption = captured.factories[1]()
    expect(coverageOption.xAxis.data).toEqual(['第1年', '第2年'])
    expect(coverageOption.xAxis.boundaryGap).toBe(false)
    expect(coverageOption.yAxis.axisLabel.formatter(0)).toBe('0.0')
    expect(coverageOption.yAxis.axisLabel.formatter(1)).toBe('0.5')
    expect(coverageOption.yAxis.axisLabel.formatter(2)).toBe('1.0')
    expect(coverageOption.yAxis.axisLabel.formatter(3)).toBe('1.2')
    expect(coverageOption.yAxis.nameLocation).toBe('middle')
    expect(coverageOption.yAxis.nameGap).toBe(38)
    expect(coverageOption.series[0].data).toEqual([4, 5])
    expect(coverageOption.series[0].markLine.data).toEqual([{ yAxis: 2 }])
    expect(coverageOption.series[0].markArea.data).toEqual([[
      { yAxis: 0, itemStyle: { color: '#45515e' } }, { yAxis: 2 },
    ]])
    expect(coverageOption.series[1]).toMatchObject({
      data: [4, 5], lineStyle: { opacity: 0 }, areaStyle: { origin: 2 }, silent: true,
    })
    const cashflowOption = captured.factories[2]()
    expect(cashflowOption.xAxis.data).toEqual(['第1年', '第2年'])
    expect(cashflowOption.color).toEqual(['#45515e', '#45515e', '#45515e', '#45515e'])
    expect(cashflowOption.yAxis.nameLocation).toBe('middle')
    expect(cashflowOption.yAxis.nameGap).toBe(42)
    expect(cashflowOption.series.map((series) => series.data)).toEqual([
      [100.12345, 90.54321], [20.23456, 10.65432], [30.34567, 45.76543], [150.45678, 145.87654],
    ])
    expect(cashflowOption.tooltip.formatter([
      { axisValue: '第1年', marker: '●', seriesName: '还本', value: 100.12345 },
    ])).toContain('100.1235 万元')
    const verifiedProfitOption = captured.factories[3]()
    expect(verifiedProfitOption.color).toEqual(['#45515e', '#45515e'])
    expect(verifiedProfitOption.yAxis.nameLocation).toBe('middle')
    expect(verifiedProfitOption.yAxis.nameGap).toBe(42)
    expect(verifiedProfitOption.tooltip.formatter([
      { axisValue: '第1年', marker: '●', seriesName: '净利润', value: 40.12345 },
    ])).toContain('40.1234 万元')
    const sensitivityOption = captured.factories[4]()
    expect(sensitivityOption.tooltip).toEqual({ show: false })
    expect(sensitivityOption.xAxis.show).toBe(false)
    expect(sensitivityOption.grid).toMatchObject({ right: '18%', bottom: 42 })
    expect(sensitivityOption.series[0].barWidth).toBe(28)
    expect(sensitivityOption.series[0].data.map((item) => item.itemStyle.color)).toEqual(['#45515e', '#45515e', '#45515e'])
    expect(sensitivityOption.series[0]).toMatchObject({ z: 2, zlevel: 1 })
    expect(sensitivityOption.series[1]).toMatchObject({ type: 'line', data: [], silent: true, z: 0, zlevel: 0 })
    expect(sensitivityOption.series[0].label.formatter({ value: 1.4567 })).toBe('1.46 倍')
    expect(sensitivityOption.series[1].markLine).toMatchObject({
      silent: true, z: -1, zlevel: -1,
      label: {
        formatter: '警戒线 1.0', position: 'end', distance: 8,
        align: 'left', verticalAlign: 'top',
      },
    })
    expect(coverageOption.series[0].markLine.label.formatter).toBe('警戒线 1.0')
    const matrixOption = captured.factories[5]()
    expect(matrixOption.tooltip.formatter({ data: { value: [0.9876, 1.4567] } })).toBe(
      '悲观情景平均偿债倍数：0.99 倍<br/>基准情景平均偿债倍数：1.46 倍',
    )
    expect(matrixOption.series[0].data[0]).toMatchObject({
      value: [0.9876, 1.4567],
      label: { show: true, formatter: '暂缓', position: 'right', distance: 10 },
    })
    expect(matrixOption.grid).toMatchObject({ left: 94, right: 88 })
    expect(matrixOption.xAxis).toMatchObject({ max: 1.5, interval: 0.5 })
    expect(matrixOption.yAxis).toMatchObject({ max: 2, interval: 0.5 })
    expect(matrixOption.series[0].markLine).toBeUndefined()
    expect(wrapper.findAll('.ir-report-chapter-heading')).toHaveLength(7)
    expect(wrapper.findAll('.ir-report-chapter-heading').map((item) => item.text())).toEqual([
      '第一章 项目基本信息', '第二章：市场供需分析', '第三章 政策环境分析', '第四章 项目测算边界',
      '第五章 主模型分析', '第六章 敏感情景测试', '第七章 结论与投资建议',
    ])
    expect(wrapper.text()).toContain('导出 PDF')
    expect(wrapper.text()).toContain('5.1 偿债能力｜现金流口径下偿债倍数')
    expect(wrapper.text()).toContain('5.2 偿债能力｜经营性现金流对还本付息覆盖能力')
    expect(wrapper.text()).toContain('5.3 财务报表口径｜会计净利润')
    expect(wrapper.text()).toContain('偿债覆盖倍数 = 年度经营性现金流 ÷ 当年还本付息。')
    expect(wrapper.text()).toContain('7.2 投资判断阈值')
    expect(wrapper.text()).toContain('7.3 风险提示与后续动作')
    expect(wrapper.text()).toContain('基准平均偿债倍数 ≥ 1.1 且 悲观平均偿债倍数 ≥ 1.1')
    expect(wrapper.text()).toContain('基准平均偿债倍数 < 1，或贷款期内出现年度偿债覆盖倍数 < 1.00且无明确补足机制')
    expect(wrapper.findAll('.ir-report-model-section')).toHaveLength(3)
    expect(wrapper.findAll('.ir-report-model-section .ir-report-ai')).toHaveLength(3)
    expect(wrapper.text().match(/如何解读这张图/g)).toHaveLength(3)
    const profitOption = captured.factories[3]()
    expect(profitOption.series.map((series) => series.name)).toEqual(['净利润', '折旧摊销'])
  })
})

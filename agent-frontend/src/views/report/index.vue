<template>
  <main class="ir-report-page xc-app">
    <nav class="ir-report-tools" aria-label="报告操作">
      <button
        class="ir-report-tool"
        type="button"
        title="打印报告（建议在打印设置中启用“背景图形”）"
        aria-label="打印报告"
        :disabled="isPreparingPrint"
        @click="printReport"
      >
        <Printer aria-hidden="true" />
      </button>
      <button
        v-if="showBackToTop"
        class="ir-report-tool"
        type="button"
        title="返回顶部"
        aria-label="返回顶部"
        @click="scrollToTop"
      >
        <ArrowUp aria-hidden="true" />
      </button>
    </nav>

    <article v-if="report" class="ir-report-document">
      <ReportCover :project-name="projectName" :preparer="preparer" :generated-date="report.generatedDate" />

      <div ref="reportFlow" class="ir-report-body ir-report-flow">
      <ReportWatermark />
      <ReportChapter :number="1" title="第一章 项目基本信息">
        <div class="ir-report-table-wrap">
          <table class="ir-report-table ir-report-table--four">
          <thead><tr><th>项目要素</th><th>内容</th><th>项目要素</th><th>内容</th></tr></thead>
          <tbody>
            <tr><th>项目名称</th><td>{{ projectName }}</td><th>并网节点</th><td>{{ project.nodeName || project.province }}</td></tr>
            <tr><th>装机功率（MW）</th><td>{{ blankUnit(project.powerMw, 'MW') }}</td><th>储能容量（MWh）</th><td>{{ blankUnit(project.capacityMwh, 'MWh') }}</td></tr>
            <tr><th>储能时长（h）</th><td>{{ blankUnit(project.durationHours, 'h') }}</td><th>并网电压等级</th><td>{{ blank(project.voltageLevel) }}</td></tr>
            <tr><th>业主单位</th><td>{{ blank(project.owner) }}</td><th>预期投运时间</th><td>{{ blank(project.expectedOperationDate) }}</td></tr>
            <tr><th>业主背景</th><td>{{ ownerBackground }}</td><th>项目类型</th><td>{{ projectType }}</td></tr>
            <tr><th>奇点能源定位</th><td class="ir-report-role">{{ singularityRole }}</td><td colspan="2" /></tr>
          </tbody>
          </table>
        </div>
      </ReportChapter>

      <ReportChapter :number="2" title="第二章 市场供需分析">
        <div class="ir-report-market-copy">
          <p>该项目处于{{ project.province }}，目前该省（地区）电力市场处于现货连续结算试运行阶段，该省能源结构如下：</p>
          <p v-if="market.energyStructure">{{ market.energyStructure }}</p>
          <template v-for="item in marketSections" :key="item.label">
            <p v-if="item.value" class="ir-report-market-copy__label">{{ item.label }}</p>
            <p v-if="item.value">{{ item.value }}</p>
          </template>
        </div>
      </ReportChapter>

      <ReportChapter :number="3" title="第三章 政策环境分析">
        <ReportSectionHeading title="3.1 政策环境清单" />
        <div class="ir-report-table-wrap">
          <table class="ir-report-table ir-report-policy-table">
          <thead><tr><th>政策类型</th><th>市场状态</th><th>对项目影响</th></tr></thead>
          <tbody>
            <tr v-for="item in policyRows" :key="item.name">
              <td>{{ item.name }}</td><td>{{ marketStatus(item.enabled) }}</td><td>{{ projectImpact(item.enabled) }}</td>
            </tr>
          </tbody>
          </table>
        </div>

        <ReportSectionHeading title="3.2 现货基础运营信息" />
        <div class="ir-report-operation-layout">
          <section v-for="group in operationGroups" :key="group.title" class="ir-report-operation-group">
            <h4>{{ group.title }}</h4>
            <dl>
              <div v-for="item in group.items" :key="item.label"><dt>{{ item.label }}</dt><dd class="xc-num">{{ price(item.value) }}</dd></div>
            </dl>
          </section>
        </div>

        <ReportSectionHeading title="3.3 项目首年收益结构" />
        <div class="ir-report-revenue-layout">
          <ReportChartCard unit="单位：万元"><ReportChart kind="revenue" :data="{ donut: calculation.advanced?.donut }" /></ReportChartCard>
          <div class="ir-report-table-wrap">
            <table class="ir-report-table ir-report-revenue-table">
              <thead><tr><th>收益项</th><th>金额（万元）</th><th>占比</th></tr></thead>
              <tbody>
                <tr v-for="item in revenueRows" :key="item.name"><td>{{ item.name }}</td><td class="xc-num">{{ formatNumber(item.value) }}</td><td class="xc-num">{{ formatNumber(item.ratio * 100, 1) }}%</td></tr>
                <tr class="ir-report-revenue-total"><th scope="row">合计</th><th class="xc-num">{{ formatNumber(revenueTotal) }}</th><th class="xc-num">100.0%</th></tr>
                <tr v-if="!revenueRows.length"><td colspan="3">{{ missing }}</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </ReportChapter>

      <ReportChapter :number="4" title="第四章 项目测算边界">
        <ReportSectionHeading title="4.1 测算边界参数" />
        <p class="ir-report-intro">本节固化所有输入参数的取值依据，确保不同项目间结果可比、可追溯。</p>
        <div class="ir-report-table-wrap">
          <table class="ir-report-table ir-report-boundary-table">
          <thead><tr><th>参数类别</th><th>参数名称</th><th>基准值</th><th>取值依据</th></tr></thead>
          <tbody>
            <tr v-for="item in measurementBoundaryRows" :key="item.name">
              <td>{{ item.category }}</td><td>{{ item.name }}</td><td class="xc-num">{{ item.value }}</td><td>{{ item.rationale }}</td>
            </tr>
          </tbody>
          </table>
        </div>

        <ReportSectionHeading title="4.2 基准方案测算结果" />
        <p class="ir-report-intro">按上述边界条件运行测算模型，得到的基准方案核心财务指标如下：</p>
        <div class="ir-report-table-wrap">
          <table class="ir-report-table ir-report-financial-table">
          <thead><tr><th>指标名称</th><th>单位</th><th>数值</th><th>说明</th></tr></thead>
          <tbody>
            <tr v-for="item in financialMetricRows" :key="item.name">
              <td>{{ item.name }}</td><td>{{ item.unit }}</td><td class="xc-num">{{ item.value }}</td><td>{{ item.note }}</td>
            </tr>
          </tbody>
          </table>
        </div>
      </ReportChapter>

      <ReportChapter :number="5" title="第五章 主模型分析">

        <section class="ir-report-model-section">
          <ReportSectionHeading title="5.1 偿债能力｜现金流口径下偿债倍数" />
          <ReportChartCard unit="单位：倍">
            <ReportChart kind="coverage" :data="{ coverage: charts.series?.debtServiceCoverage }" />
            <template #interpretation><p>偿债覆盖倍数 = 年度经营性现金流 ÷ 当年还本付息。</p></template>
          </ReportChartCard>
          <ReportAiAnalysis :text="report.aiSections?.debt_service_coverage?.text" :fallback="aiFallback" />
        </section>

        <section class="ir-report-model-section">
          <ReportSectionHeading title="5.2 偿债能力｜经营性现金流对还本付息覆盖能力" />
          <ReportChartCard unit="单位：万元">
            <ReportChart kind="cashflow" :data="charts.series" />
            <template #interpretation><p>对比年度经营性现金流与还本、付息及偿债后自由现金流。</p></template>
          </ReportChartCard>
          <ReportAiAnalysis :text="report.aiSections?.operating_cashflow?.text" :fallback="aiFallback" />
        </section>

        <section class="ir-report-model-section">
          <ReportSectionHeading title="5.3 财务报表口径｜会计净利润" />
          <ReportChartCard unit="单位：万元">
            <ReportChart kind="profit" :data="charts.series" />
            <template #interpretation><p>观察净利润与折旧摊销的年度变化及其对会计收益的影响。</p></template>
          </ReportChartCard>
          <ReportAiAnalysis :text="report.aiSections?.accounting_profit?.text" :fallback="aiFallback" />
        </section>
      </ReportChapter>

      <ReportChapter :number="6" title="第六章 敏感情景测试">
        <ReportSectionHeading title="6.1 压力情景下的平均偿债覆盖倍数" />
        <ReportChartCard unit="单位：倍"><ReportChart kind="sensitivity" :data="charts.sensitivity" /></ReportChartCard>
        <ReportAiAnalysis :text="report.aiSections?.sensitivity?.text" :fallback="aiFallback" />
      </ReportChapter>

      <ReportChapter :number="7" title="第七章 结论与投资建议">
        <ReportSectionHeading title="7.1 风险 - 收益决策矩阵" />
        <ReportChartCard><ReportChart kind="matrix" :data="charts.sensitivity" /></ReportChartCard>
        <ReportSectionHeading title="7.2 投资判断阈值" />
        <div class="ir-report-table-wrap">
          <table class="ir-report-table">
          <thead><tr><th>判断条件</th><th>投资建议</th><th>后续动作</th></tr></thead>
          <tbody><tr v-for="item in decisionRows" :key="item.advice"><td>{{ item.condition }}</td><td>{{ item.advice }}</td><td>{{ item.action }}</td></tr></tbody>
          </table>
        </div>
        <ReportSectionHeading title="7.3 风险提示与后续动作" />
        <ReportAiAnalysis :text="report.aiSections?.investment_conclusion?.text" :fallback="aiFallback" />
      </ReportChapter>
      </div>
      <ReportPrintPages ref="printPages" />
    </article>
    <div v-else-if="loaded" class="ir-report-empty">报告不存在或当前用户无权查看。</div>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ArrowUp, Printer } from '@lucide/vue'
import { useRoute } from 'vue-router'
import { getReport } from '@/api/report'
import { formatNumber, formatPrice } from '@/utils/formatNumber'
import ReportAiAnalysis from './components/ReportAiAnalysis.vue'
import ReportChapter from './components/ReportChapter.vue'
import ReportChart from './components/ReportChart.vue'
import ReportChartCard from './components/ReportChartCard.vue'
import ReportCover from './components/ReportCover.vue'
import ReportPrintPages from './components/ReportPrintPages.vue'
import ReportSectionHeading from './components/ReportSectionHeading.vue'
import ReportWatermark from './components/ReportWatermark.vue'

const route = useRoute()
const report = ref(null)
const loaded = ref(false)
const showBackToTop = ref(false)
const reportFlow = ref(null)
const printPages = ref(null)
const isPreparingPrint = ref(false)
const missing = '——'
const aiFallback = '本节智能分析暂未生成，不影响测算数据、图表及规则化内容的展示。'
const project = computed(() => report.value?.project || {})
const projectName = computed(() => project.value.name || String(report.value?.title || '').replace(/测算方案$/, ''))
const preparer = computed(() => project.value.preparer || '西安奇点能源股份有限公司')
const market = computed(() => report.value?.marketSupplyDemand || {})
const operations = computed(() => report.value?.marketOperations || {})
const boundary = computed(() => report.value?.measurementBoundary || {})
const financialMetrics = computed(() => report.value?.financialMetrics || {})
const calculation = computed(() => report.value?.calculation?.result || {})
const charts = computed(() => report.value?.charts || { series: {}, sensitivity: {} })
const policyRows = computed(() => report.value?.policyEnvironment?.rows || [])
const marketSections = computed(() => [
  { label: '储能：', value: market.value.storage }, { label: '发电量情况如下：', value: market.value.generation },
  { label: '用户用电情况如下：', value: market.value.consumption }, { label: '该省十五五规划如下：', value: market.value.developmentPlan },
])
const ownerBackground = computed(() => checkbox(project.value.ownerBackground === '国央企', '国央企') + '　' + checkbox(project.value.ownerBackground === '民营企业', '民营企业'))
const projectType = computed(() => checkbox(project.value.projectType === '源网侧', '源网侧') + '　' + checkbox(project.value.projectType === '用户侧', '用户侧'))
const singularityRole = computed(() => [checkbox(String(project.value.singularityRole || '').includes('设备'), '设备厂商'), checkbox(String(project.value.singularityRole || '').includes('运营'), '运营商'), checkbox(String(project.value.singularityRole || '').includes('运维'), '运维商')].join('　'))
const operationGroups = computed(() => [
  { title: '现货市场情况', items: [['充电价格', operations.value.spotChargePrice], ['放电价格', operations.value.spotDischargePrice], ['现货价差', operations.value.spotSpread]].map(([label, value]) => ({ label, value })) },
  { title: '充电成本情况', items: [['输配电价', operations.value.transmissionPrice], ['线损费用', operations.value.lineLossFee], ['系统运行费', operations.value.systemOperationFee], ['政府基金及附加', operations.value.governmentFundSurcharge]].map(([label, value]) => ({ label, value })) },
  { title: '实际运营情况', items: [['充电收取费用', operations.value.chargeCost], ['放电返还费用', operations.value.dischargeReturn], ['实际充放价差', operations.value.actualSpread]].map(([label, value]) => ({ label, value })) },
])
const revenueRows = computed(() => {
  const donut = calculation.value.advanced?.donut || {}
  const rows = [['电能量', donut.energyRevenue], ['容量市场', donut.capacityRevenue], ['调频市场', donut.frequencyRevenue], ['租赁市场', donut.leaseRevenue], ['干预补偿', donut.interventionRevenue], ['补贴', donut.subsidyRevenue]].filter(([, value]) => typeof value === 'number' && value > 0)
  const total = rows.reduce((sum, [, value]) => sum + value, 0)
  return rows.map(([name, value]) => ({ name, value, ratio: total ? value / total : 0 }))
})
const revenueTotal = computed(() => revenueRows.value.reduce((sum, item) => sum + item.value, 0))
const measurementBoundaryRows = computed(() => [
  ['投资类', 'EPC单位造价（元/Wh）', boundary.value.epcUnitPrice, 'number', '最近半年同规模项目中标均价'],
  ['投资类', '第11年技改投资（元/Wh）', boundary.value.batteryReplaceCost, 'number', '按届时电芯价格预测，约为初始造价×0.4'],
  ['投资类', '自有资金比例', boundary.value.equityRatio, 'percent', '行业典型水平'],
  ['收益类', '现货策略达成率', boundary.value.strategyAchievementRate, 'percent', '行业经验值，团队成熟度评估'],
  ['收益类', '年等效运行天数', boundary.value.annualOperationDays, 'days', '按现货350天扣除检修天数'],
  ['财务类', '贷款利率', boundary.value.loanRate, 'percent', '当期LPR + 加点'],
  ['财务类', '贷款年限', boundary.value.loanYears, 'years', '标准项目贷年限'],
  ['财务类', '还款方式', boundary.value.repaymentMethod, 'text', '行业经验'],
  ['年限类', '经营期', boundary.value.operationYears, 'years', '电池系统设计寿命*2'],
  ['年限类', '折现率', boundary.value.discountRate, 'percent', '财务部估算标准'],
  ['税率类', '电能量收入增值税', boundary.value.energyRevenueVatRate, 'percent', '国家税务总局规定'],
  ['税率类', '辅助服务收入增值税', boundary.value.ancillaryServiceVatRate, 'percent', ''],
  ['税率类', '容量补偿收入增值税', boundary.value.capacityCompensationVatRate, 'percent', ''],
  ['税率类', '容量租赁收入增值税', boundary.value.capacityLeaseVatRate, 'percent', ''],
  ['税率类', '补贴收入增值税', boundary.value.subsidyVatRate, 'percent', ''],
  ['税率类', '干预补偿收入增值税', boundary.value.interventionCompensationVatRate, 'percent', ''],
  ['税率类', '所得税', boundary.value.incomeTaxRate, 'percent', '西部大开发地区可适用15%'],
].map(([category, name, value, format, rationale]) => ({ category, name, value: formatBoundaryValue(value, format), rationale })))
const financialMetricRows = computed(() => [
  ['全投资财务内部收益率（IRR）', '%', financialMetrics.value.projectIrr, '项目整体盈利能力'],
  ['资本金财务内部收益率（IRR）', '%', financialMetrics.value.capitalIrr, '股东实际回报水平'],
  ['全投资静态回收期', '年', financialMetrics.value.projectStaticPayback, '考虑货币时间价值的回本时间'],
  ['年均利润', '万元', financialMetrics.value.averageProfit, '全周期年均利润'],
  ['年均收入', '万元', financialMetrics.value.averageRevenue, '经营期年均不含税收入'],
  ['总投资收益率（ROI）', '%', financialMetrics.value.totalInvestmentRoi, '年均利润÷动态总投资'],
].map(([name, unit, value, note]) => ({ name, unit, value: formatFixedNumber(value), note })))
const decisionRows = [
  { condition: '基准平均偿债倍数 ≥ 1.1 且 悲观平均偿债倍数 ≥ 1.1', advice: '建议投资', action: '进入详细尽调、设备选型与商务条款固化' },
  { condition: '基准平均偿债倍数 ≥ 1.1，但悲观平均偿债倍数为 1.0-1.1', advice: '可投但需锁定风险', action: '锁定EPC合同价、主要收入来源和政策保障边界' },
  { condition: '基准平均偿债倍数为 1.05 且 悲观平均偿债倍数 ≥ 1.00', advice: '观察', action: '等待收入政策明朗或寻找造价、运维成本改善空间' },
  { condition: '基准平均偿债倍数为 1.0-1.05 或 悲观平均偿债倍数 < 1.00', advice: '暂缓', action: '重新校核收入假设、融资结构和还款节奏' },
  { condition: '基准平均偿债倍数 < 1，或贷款期内出现年度偿债覆盖倍数 < 1.00且无明确补足机制', advice: '不建议投资', action: '项目偿债安全边际不足，暂不具备投资价值' },
]

function handleScroll() {
  showBackToTop.value = window.scrollY > 360
}

onMounted(async () => {
  window.addEventListener('scroll', handleScroll, { passive: true })
  handleScroll()
  try { report.value = (await getReport(route.params.reportId)).data || null } finally { loaded.value = true }
})
onBeforeUnmount(() => {
  window.removeEventListener('scroll', handleScroll)
  window.removeEventListener('afterprint', clearPrintPages)
})
async function printReport() {
  if (isPreparingPrint.value || !reportFlow.value) return
  isPreparingPrint.value = true
  try {
    await printPages.value.prepareForPrint(reportFlow.value)
    window.addEventListener('afterprint', clearPrintPages, { once: true })
    window.print()
  } finally {
    isPreparingPrint.value = false
  }
}
function clearPrintPages() { printPages.value?.clear() }
function scrollToTop() {
  const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' })
}
function blank(value) { return value == null ? '' : String(value) }
function blankUnit(value, unit) { return value == null ? '' : `${formatNumber(value)} ${unit}` }
function checkbox(checked, label) { return `${checked ? '☑' : '□'} ${label}` }
function marketStatus(enabled) { return `${checkbox(enabled, '已启动')}　${checkbox(!enabled, '未启动')}` }
function projectImpact(enabled) { return `${checkbox(enabled, '纳入测算')}　${checkbox(!enabled, '不纳入')}` }
function price(value) { return value == null ? missing : `${formatPrice(value)} 元/kWh` }
function formatBoundaryValue(value, format) {
  if (value == null || value === '') return '——'
  if (format === 'percent') return `${formatNumber(Number(value) * 100, 2)}%`
  if (format === 'days') return `${formatNumber(value)}天`
  if (format === 'years') return `${formatNumber(value)}年`
  return format === 'text' ? String(value) : formatNumber(value)
}
function formatFixedNumber(value) {
  const number = Number(value)
  return Number.isFinite(number) ? number.toFixed(2) : '——'
}
</script>

<style scoped>
.ir-report-page { min-height: 100vh; padding: 32px 64px 88px; overflow-x: hidden; background: var(--xc-report-page); color: var(--xc-text-default); }
.ir-report-tools { position: fixed; z-index: var(--xc-z-nav); right: 32px; bottom: 32px; display: flex; flex-direction: column; gap: var(--xc-space-3); }
.ir-report-tool { display: inline-flex; width: 48px; height: 48px; align-items: center; justify-content: center; border: 1px solid var(--xc-report-border); border-radius: var(--xc-radius-full); background: var(--xc-report-card); box-shadow: var(--xc-shadow-md); color: var(--xc-text-default); cursor: pointer; transition: border-color var(--xc-dur-fast) var(--xc-ease-out), color var(--xc-dur-fast) var(--xc-ease-out), transform var(--xc-dur-fast) var(--xc-ease-out); }
.ir-report-tool:hover { border-color: var(--xc-accent-blue); color: var(--xc-accent-blue); transform: translateY(-1px); }
.ir-report-tool:focus-visible { outline: 2px solid var(--xc-accent-blue); outline-offset: 3px; }
.ir-report-tool :deep(svg) { width: 20px; height: 20px; stroke-width: 1.8; }
.ir-report-document { width: min(241.5mm, calc(100vw - 128px)); margin: 0 auto; background: var(--xc-report-page); box-shadow: var(--xc-shadow-lg); font-family: var(--xc-font-zh); line-height: var(--xc-lh-loose); }
.ir-report-body { position: relative; padding: 22mm 24mm 28mm; }
.ir-report-intro { margin: 0 0 16px; color: var(--xc-text-soft); }
.ir-report-table-wrap { width: 100%; overflow-x: auto; }
.ir-report-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 13px; }
.ir-report-table th, .ir-report-table td { min-height: 44px; padding: 12px 17px; border-right: 1px solid var(--xc-report-border); border-bottom: 1px solid var(--xc-report-border); text-align: left; vertical-align: middle; }
.ir-report-table tr > :first-child { border-left: 1px solid var(--xc-report-border); }
.ir-report-table thead th { border-top: 1px solid var(--xc-report-border); border-bottom-color: var(--xc-border-accent); background: var(--xc-report-table-head); color: var(--xc-text-strong); font-weight: var(--xc-fw-semi); }
.ir-report-table thead th:first-child { border-top-left-radius: var(--xc-radius-xs); }
.ir-report-table thead th:last-child { border-top-right-radius: var(--xc-radius-xs); }
.ir-report-table tbody tr:nth-child(odd) > * { background: var(--xc-report-table-row); }
.ir-report-table tbody tr:nth-child(even) > * { background: var(--xc-report-table-row-alt); }
.ir-report-table tbody th { color: var(--xc-text-soft); font-weight: var(--xc-fw-medium); }
.ir-report-table td { color: var(--xc-text-default); }
.ir-report-cell--number, .ir-report-revenue-table td:nth-child(n + 2), .ir-report-boundary-table td:nth-child(3), .ir-report-financial-table td:nth-child(3) { text-align: right; }
.ir-report-financial-table td:nth-child(3) { color: var(--xc-accent-blue); font-weight: var(--xc-fw-semi); }
.ir-report-table--four th { width: 16%; }.ir-report-table--four td { width: 34%; }
.ir-report-boundary-table th:nth-child(1) { width: 13%; }.ir-report-boundary-table th:nth-child(2) { width: 28%; }.ir-report-boundary-table th:nth-child(3) { width: 18%; text-align: right; }.ir-report-boundary-table th:nth-child(4) { width: 41%; }
.ir-report-financial-table th:nth-child(1) { width: 33%; }.ir-report-financial-table th:nth-child(2) { width: 12%; }.ir-report-financial-table th:nth-child(3) { width: 18%; text-align: right; }.ir-report-financial-table th:nth-child(4) { width: 37%; }
.ir-report-boundary-table th, .ir-report-financial-table th { white-space: nowrap; }
.ir-report-role { line-height: 1.8; }.ir-report-policy-table td:nth-child(2), .ir-report-policy-table td:nth-child(3) { white-space: nowrap; }
.ir-report-market-copy p { margin: 0 0 16px; white-space: pre-line; text-align: justify; text-indent: 2em; }.ir-report-market-copy__label { margin-bottom: 0 !important; color: var(--xc-text-strong); font-weight: var(--xc-fw-semi); text-indent: 0 !important; }
.ir-report-operation-layout { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin: 16px 0 24px; break-inside: avoid; }
.ir-report-operation-group { min-width: 0; padding: 16px 18px; border: 1px solid var(--xc-report-border); border-radius: var(--xc-radius-sm); background: var(--xc-report-card); break-inside: avoid; }.ir-report-operation-group h4 { margin: 0; padding-bottom: 10px; border-bottom: 1px solid var(--xc-report-border); color: var(--xc-text-strong); font-size: 14px; }.ir-report-operation-group dl { margin: 8px 0 0; }.ir-report-operation-group dl div { display: grid; grid-template-columns: minmax(0, 1fr) max-content; gap: 8px; align-items: baseline; padding: 5px 0; }.ir-report-operation-group dt { min-width: 0; color: var(--xc-text-soft); line-height: var(--xc-lh-normal); }.ir-report-operation-group dd { margin: 0; color: var(--xc-text-strong); line-height: var(--xc-lh-normal); text-align: right; white-space: nowrap; }
.ir-report-revenue-layout { display: grid; grid-template-columns: minmax(0, 3fr) minmax(260px, 2fr); gap: 24px; align-items: stretch; break-inside: avoid; }.ir-report-revenue-table { align-self: stretch; }.ir-report-revenue-total th { color: var(--xc-text-strong); }.ir-report-revenue-total .xc-num { text-align: right; }
.ir-report-model-section { margin-top: 36px; }.ir-report-model-section:first-child { margin-top: 0; }
.ir-report-empty { width: min(700px, 90vw); margin: 120px auto; color: var(--xc-text-mute); text-align: center; }
@media (prefers-reduced-motion: reduce) { .ir-report-tool { transition: none; }.ir-report-tool:hover { transform: none; } }
@media screen and (max-width: 1000px) { .ir-report-page { padding: 16px 16px 80px; }.ir-report-tools { right: 16px; bottom: 16px; }.ir-report-document { width: 100%; }.ir-report-body { padding: 72px 24px; }.ir-report-operation-layout, .ir-report-revenue-layout { grid-template-columns: 1fr; }.ir-report-table { min-width: 680px; } }
@media screen and (max-width: 760px) { .ir-report-body { padding: 56px 16px; }.ir-report-operation-group { padding: 14px 16px; } }
</style>

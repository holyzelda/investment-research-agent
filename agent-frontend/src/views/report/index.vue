<template>
  <main class="ir-report-page">
    <nav class="ir-report-actions" aria-label="报告操作">
      <button class="ir-report-action" type="button" title="返回" @click="router.back()">返回</button>
      <button class="ir-report-action ir-report-action--primary" type="button" title="导出 PDF" @click="printReport">导出 PDF</button>
    </nav>

    <article v-if="report" class="ir-report-document">
      <header class="ir-report-cover">
        <div class="ir-report-cover__rule" />
        <p class="ir-report-cover__kicker">ENERGY STORAGE INVESTMENT REVIEW</p>
        <h1>{{ report.title }}</h1>
        <dl>
          <div><dt>编制单位</dt><dd>{{ report.project?.preparer || missing }}</dd></div>
          <div><dt>编制日期</dt><dd>{{ report.generatedDate }}</dd></div>
          <div><dt>测算版本</dt><dd>{{ report.source?.version || missing }}</dd></div>
        </dl>
      </header>

      <section class="ir-report-section">
        <SectionTitle chapter="第一章" title="项目基本信息" />
        <table class="ir-report-table ir-report-table--four">
          <tbody>
            <tr><th>项目名称</th><td>{{ report.title }}</td><th>并网节点</th><td>{{ project.nodeName }}</td></tr>
            <tr><th>装机功率</th><td>{{ withUnit(project.powerMw, 'MW') }}</td><th>储能容量</th><td>{{ withUnit(project.capacityMwh, 'MWh') }}</td></tr>
            <tr><th>储能时长</th><td>{{ withUnit(project.durationHours, 'h') }}</td><th>项目类型</th><td>{{ project.projectType }}</td></tr>
            <tr><th>业主单位</th><td>{{ project.owner || missing }}</td><th>预期投运时间</th><td>{{ project.expectedOperationDate || missing }}</td></tr>
            <tr><th>业主背景</th><td>{{ project.ownerBackground || missing }}</td><th>奇点能源定位</th><td>{{ project.singularityRole }}</td></tr>
          </tbody>
        </table>
      </section>

      <section class="ir-report-section">
        <SectionTitle chapter="第二章" title="市场供需与政策环境" />
        <h3>2.1 市场供需信息</h3>
        <div v-if="hasMarketSupply" class="ir-report-facts">
          <div v-for="(value, key) in report.marketSupplyDemand" :key="key"><span>{{ key }}</span><strong>{{ formatValue(value) }}</strong></div>
        </div>
        <p v-else class="ir-report-missing">{{ missing }}</p>
        <h3>2.2 政策环境清单</h3>
        <table class="ir-report-table">
          <thead><tr><th>政策类型</th><th>市场状态</th><th>对项目影响</th></tr></thead>
          <tbody>
            <tr v-for="item in policyRows" :key="item.name"><td>{{ item.name }}</td><td>{{ item.status }}</td><td>{{ item.impact }}</td></tr>
            <tr v-if="!policyRows.length"><td colspan="3">{{ missing }}</td></tr>
          </tbody>
        </table>
        <h3>2.3 现货基础运营信息</h3>
        <table class="ir-report-table">
          <tbody>
            <tr><th>现货充电价格</th><td>{{ price(operations.spotChargePrice) }}</td><th>现货放电价格</th><td>{{ price(operations.spotDischargePrice) }}</td></tr>
            <tr><th>现货价差</th><td>{{ price(operations.spotSpread) }}</td><th>输配电价</th><td>{{ price(operations.transmissionPrice) }}</td></tr>
            <tr><th>线损费用</th><td>{{ price(operations.lineLossFee) }}</td><th>系统运行费</th><td>{{ price(operations.systemOperationFee) }}</td></tr>
            <tr><th>政府基金及附加</th><td>{{ price(operations.governmentFundSurcharge) }}</td><th>实际充放价差</th><td>{{ price(operations.actualSpread) }}</td></tr>
          </tbody>
        </table>
        <ReportChart title="项目首年收益结构" unit="单位：万元" kind="revenue" :data="{ donut: calculation.advanced?.donut }" />
      </section>

      <section class="ir-report-section">
        <SectionTitle chapter="第三章" title="项目测算边界" />
        <h3>3.1 测算边界参数</h3>
        <table class="ir-report-table">
          <thead><tr><th>参数类别</th><th>参数名称</th><th>基准值</th></tr></thead>
          <tbody>
            <tr v-for="item in boundaryRows" :key="item.name"><td>{{ item.category }}</td><td>{{ item.name }}</td><td>{{ item.value }}</td></tr>
          </tbody>
        </table>
        <h3>3.2 基准方案测算结果</h3>
        <table class="ir-report-table">
          <thead><tr><th>指标名称</th><th>单位</th><th>数值</th><th>说明</th></tr></thead>
          <tbody>
            <tr v-for="item in financialRows" :key="item.name"><td>{{ item.name }}</td><td>{{ item.unit }}</td><td class="xc-num">{{ item.value }}</td><td>{{ item.note }}</td></tr>
          </tbody>
        </table>
      </section>

      <section class="ir-report-section">
        <SectionTitle chapter="第四章" title="主模型分析" />
        <div class="ir-report-chart-grid">
          <ReportChart title="现金流口径下偿债倍数" unit="单位：倍" kind="coverage" :data="{ coverage: charts.series?.debtServiceCoverage }" />
          <ReportChart title="经营性现金流对还本付息覆盖能力" unit="单位：万元" kind="cashflow" :data="charts.series" />
          <ReportChart title="会计净利润" unit="单位：万元" kind="profit" :data="charts.series" />
        </div>
        <AiSection v-for="key in ['debt_service_coverage', 'operating_cashflow', 'accounting_profit']" :key="key" :section="report.aiSections?.[key]" :fallback="aiFallback" />
      </section>

      <section class="ir-report-section">
        <SectionTitle chapter="第五章" title="敏感情景测试" />
        <ReportChart title="压力情景下的平均偿债覆盖倍数" unit="单位：倍" kind="sensitivity" :data="charts.sensitivity" />
        <AiSection :section="report.aiSections?.sensitivity" :fallback="aiFallback" />
      </section>

      <section class="ir-report-section">
        <SectionTitle chapter="第六章" title="结论与投资建议" />
        <ReportChart title="风险 - 收益决策矩阵" kind="matrix" :data="charts.sensitivity" />
        <h3>6.2 投资判断阈值</h3>
        <table class="ir-report-table">
          <thead><tr><th>判断条件</th><th>投资建议</th><th>后续动作</th></tr></thead>
          <tbody>
            <tr v-for="item in decisionRows" :key="item.advice"><td>{{ item.condition }}</td><td>{{ item.advice }}</td><td>{{ item.action }}</td></tr>
          </tbody>
        </table>
        <AiSection :section="report.aiSections?.investment_conclusion" :fallback="aiFallback" />
      </section>
    </article>

    <div v-else-if="loaded" class="ir-report-empty">报告不存在或当前用户无权查看。</div>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getReport } from '@/api/report'
import { formatNumber, formatPrice } from '@/utils/formatNumber'
import ReportChart from './components/ReportChart.vue'

const SectionTitle = { props: ['chapter', 'title'], template: '<div class="ir-report-section-title"><span>{{ chapter }}</span><h2>{{ title }}</h2></div>' }
const AiSection = { props: ['section', 'fallback'], template: '<div class="ir-report-ai"><p>{{ section?.text || fallback }}</p></div>' }
const route = useRoute()
const router = useRouter()
const report = ref(null)
const loaded = ref(false)
const missing = computed(() => report.value?.missingDataText || '需补充核实：____')
const aiFallback = '本节智能分析暂未生成，不影响测算数据、图表及规则化内容的展示。'
const project = computed(() => report.value?.project || {})
const operations = computed(() => report.value?.marketOperations || {})
const boundary = computed(() => report.value?.measurementBoundary || {})
const metrics = computed(() => report.value?.financialMetrics || {})
const calculation = computed(() => report.value?.calculation?.result || {})
const charts = computed(() => report.value?.charts || { series: {}, sensitivity: {} })
const hasMarketSupply = computed(() => Object.keys(report.value?.marketSupplyDemand || {}).length > 0)
const impactKeyByMarket = {
  '中长期市场': 'midLong', '现货市场': 'spot', '容量补偿': 'capacity', '调频市场': 'frequency',
  '租赁市场': 'lease', '补贴政策': 'subsidy', '干预补偿': 'intervention', '过网费优惠政策': 'collectGridFee',
}
const policyRows = computed(() => Object.entries(report.value?.policyEnvironment?.marketStatus || {}).map(([name, status]) => ({
  name,
  status,
  impact: report.value?.policyEnvironment?.projectImpact?.[name]
    || report.value?.policyEnvironment?.projectImpact?.[impactKeyByMarket[name]]
    || missing.value,
})))
const boundaryRows = computed(() => [
  ['投资类', 'EPC单位造价', boundary.value.epcUnitPrice, '元/Wh'], ['投资类', '第11年技改投资', boundary.value.batteryReplaceCost, '元/Wh'],
  ['投资类', '自有资金比例', boundary.value.equityRatio, '%'], ['收益类', '现货策略达成率', boundary.value.strategyAchievementRate, '%'],
  ['收益类', '年等效运行天数', boundary.value.annualOperationDays, '天'], ['财务类', '贷款利率', boundary.value.loanRate, '%'],
  ['财务类', '贷款年限', boundary.value.loanYears, '年'], ['财务类', '还款方式', boundary.value.repaymentMethod, ''],
  ['年限类', '经营期', boundary.value.operationYears, '年'], ['年限类', '折现率', boundary.value.discountRate, '%'],
].map(([category, name, value, unit]) => ({ category, name, value: typeof value === 'number' ? `${formatNumber(unit === '%' ? value * 100 : value)}${unit}` : (value || missing.value) })))
const financialRows = computed(() => [
  ['全投资财务内部收益率（IRR）', '%', metrics.value.projectIrr, '项目整体盈利能力'], ['资本金财务内部收益率（IRR）', '%', metrics.value.capitalIrr, '股东实际回报水平'],
  ['全投资静态回收期', '年', metrics.value.projectStaticPayback, '项目整体回本周期'], ['年均利润', '万元', metrics.value.averageProfit, '全周期年均利润'],
  ['年均收入', '万元', metrics.value.averageRevenue, '经营期年均不含税收入'], ['总投资收益率（ROI）', '%', metrics.value.totalInvestmentRoi, '年均利润÷动态总投资'],
].map(([name, unit, value, note]) => ({ name, unit, value: value == null ? missing.value : formatNumber(value), note })))
const decisionRows = [
  { condition: '基准平均偿债倍数 ≥ 1.50 且 悲观平均偿债倍数 ≥ 1.20', advice: '建议投资', action: '进入详细尽调、设备选型与商务条款固化' },
  { condition: '基准平均偿债倍数 ≥ 1.50，悲观平均偿债倍数为 1.00-1.20', advice: '可投但需锁定风险', action: '锁定EPC合同价、主要收入来源和政策保障边界' },
  { condition: '基准平均偿债倍数为 1.30-1.50 且 悲观平均偿债倍数 ≥ 1.00', advice: '观察', action: '等待收入政策明朗或寻找成本改善空间' },
  { condition: '基准平均偿债倍数为 1.20-1.30 或 悲观平均偿债倍数 < 1.00', advice: '暂缓', action: '重新校核收入假设、融资结构和还款节奏' },
  { condition: '基准平均偿债倍数 < 1.20，或贷款期内出现年度偿债缺口', advice: '不建议投资', action: '项目偿债安全边际不足，暂不具备投资价值' },
]

onMounted(async () => {
  try {
    const response = await getReport(route.params.reportId)
    report.value = response.data || null
  } finally { loaded.value = true }
})
function printReport() { window.print() }
function withUnit(value, unit) { return value == null ? missing.value : `${formatNumber(value)} ${unit}` }
function price(value) { return value == null ? missing.value : `${formatPrice(value)} 元/kWh` }
function formatValue(value) { return typeof value === 'number' ? formatNumber(value) : (value || missing.value) }
</script>

<style scoped>
.ir-report-page { min-height: 100%; overflow: auto; padding: 32px 96px 64px; background: var(--xc-surface-base); color: var(--xc-text-default); }
.ir-report-actions { position: fixed; z-index: 10; right: 32px; top: 32px; display: flex; gap: 8px; }
.ir-report-action { min-width: 82px; height: 34px; border: 1px solid var(--xc-border-card); border-radius: 4px; background: var(--xc-surface-raised); color: var(--xc-text-default); font-size: 13px; cursor: pointer; }
.ir-report-action--primary { border-color: var(--xc-accent-blue); background: var(--xc-accent-blue); color: var(--xc-text-inverse); }
.ir-report-document { width: 210mm; min-height: 297mm; box-sizing: border-box; margin: 0 auto; padding: 20mm 21mm 26mm; background: var(--xc-surface-raised); box-shadow: var(--xc-shadow-lg); font-family: var(--xc-font-zh); line-height: 1.65; }
.ir-report-cover { min-height: 235mm; display: flex; flex-direction: column; justify-content: center; padding: 0 12mm; }
.ir-report-cover__rule { width: 64px; height: 6px; background: var(--xc-accent-blue); margin-bottom: 24px; }
.ir-report-cover__kicker { margin: 0; font-family: var(--xc-font-mono); font-size: 11px; color: var(--xc-accent-blue); letter-spacing: 1.6px; }
.ir-report-cover h1 { max-width: 80%; margin: 16px 0 50px; color: var(--xc-text-strong); font-size: 36px; font-weight: var(--xc-fw-semi); line-height: 1.35; }
.ir-report-cover dl { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; padding-top: 20px; border-top: 1px solid var(--xc-border-line); }
.ir-report-cover dt { margin-bottom: 5px; color: var(--xc-text-mute); font-size: 12px; }.ir-report-cover dd { margin: 0; color: var(--xc-text-strong); font-size: 14px; }
.ir-report-section { margin-top: 32px; break-before: auto; }.ir-report-section + .ir-report-section { break-before: page; }
.ir-report-section-title { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid var(--xc-accent-blue); }.ir-report-section-title span { color: var(--xc-accent-blue); font-family: var(--xc-font-mono); font-size: 12px; }.ir-report-section-title h2 { margin: 0; color: var(--xc-text-strong); font-size: 22px; }
h3 { margin: 22px 0 10px; color: var(--xc-text-strong); font-size: 15px; font-weight: var(--xc-fw-semi); }.ir-report-missing { color: var(--xc-text-mute); }
.ir-report-facts { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px; border: 1px solid var(--xc-border-line); background: var(--xc-border-line); }.ir-report-facts div { padding: 10px; background: var(--xc-surface-raised); }.ir-report-facts span { display: block; color: var(--xc-text-mute); font-size: 11px; }.ir-report-facts strong { color: var(--xc-text-strong); font-size: 14px; }
.ir-report-table { width: 100%; border-collapse: collapse; font-size: 12px; }.ir-report-table th, .ir-report-table td { padding: 8px 10px; border: 1px solid var(--xc-border-line); text-align: left; vertical-align: top; }.ir-report-table th { background: var(--xc-surface-control); color: var(--xc-text-soft); font-weight: var(--xc-fw-medium); }.ir-report-table td { color: var(--xc-text-default); }.ir-report-table--four th { width: 16%; }.ir-report-table--four td { width: 34%; }
.ir-report-chart-grid { display: grid; gap: 16px; }.ir-report-ai { margin-top: 10px; padding: 12px 14px; border-left: 3px solid var(--xc-accent-blue); background: var(--xc-surface-control); color: var(--xc-text-soft); font-size: 13px; }.ir-report-ai p { margin: 0; }
.ir-report-empty { width: 700px; margin: 120px auto; color: var(--xc-text-mute); text-align: center; }
@media (max-width: 1000px) { .ir-report-page { padding: 16px; }.ir-report-actions { right: 16px; top: 16px; }.ir-report-document { width: 100%; min-height: auto; padding: 28px 20px; }.ir-report-cover { min-height: 65vh; padding: 0; }.ir-report-cover h1 { max-width: 100%; font-size: 28px; }.ir-report-cover dl { grid-template-columns: 1fr; }.ir-report-facts { grid-template-columns: 1fr 1fr; } }
</style>

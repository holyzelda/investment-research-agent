<template>
  <main class="ir-report-page">
    <nav class="ir-report-actions" aria-label="报告操作">
      <button class="ir-report-action" type="button" title="返回" @click="router.back()">返回</button>
      <button class="ir-report-action ir-report-action--primary" type="button" title="导出 PDF" @click="printReport">导出 PDF</button>
    </nav>

    <article v-if="report" class="ir-report-document">
      <header class="ir-report-cover">
        <h1><span>储能参与中国电力市场</span><span>前期项目测算方案</span></h1>
        <dl>
          <div><dt>项目名称：</dt><dd>{{ projectName }}</dd></div>
          <div><dt>编制单位：</dt><dd>{{ project.preparer || '西安奇点能源股份有限公司' }}</dd></div>
          <div><dt>编制日期：</dt><dd>{{ report.generatedDate }}</dd></div>
        </dl>
      </header>

      <section class="ir-report-section ir-report-section--chapter">
        <h2 class="ir-report-chapter-heading">第一章 项目基本信息</h2>
        <p class="ir-report-intro"></p>
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
      </section>

      <section class="ir-report-section ir-report-section--chapter">
        <h2 class="ir-report-chapter-heading">第二章：市场供需分析</h2>
        <div class="ir-report-market-copy">
          <p>该项目处于{{ project.province }}，目前该省（地区）电力市场处于现货连续结算试运行阶段，该省能源结构如下：</p>
          <p v-if="market.energyStructure">{{ market.energyStructure }}</p>
          <template v-for="item in marketSections" :key="item.label">
            <p v-if="item.value" class="ir-report-market-copy__label">{{ item.label }}</p>
            <p v-if="item.value">{{ item.value }}</p>
          </template>
        </div>
      </section>

      <section class="ir-report-section ir-report-section--chapter">
        <h2 class="ir-report-chapter-heading">第三章 政策环境分析</h2>
        <p class="ir-report-intro"></p>
        <h3>3.1 政策环境清单</h3>
        <table class="ir-report-table ir-report-policy-table">
          <thead><tr><th>政策类型</th><th>市场状态</th><th>对项目影响</th></tr></thead>
          <tbody>
            <tr v-for="item in policyRows" :key="item.name">
              <td>{{ item.name }}</td><td>{{ marketStatus(item.enabled) }}</td><td>{{ projectImpact(item.enabled) }}</td>
            </tr>
          </tbody>
        </table>

        <h3>3.2 现货基础运营信息</h3>
        <section v-for="group in operationGroups" :key="group.title" class="ir-report-operation-group">
          <h4>{{ group.title }}（单位：元/kWh）</h4>
          <dl>
            <div v-for="item in group.items" :key="item.label"><dt>{{ item.label }}：</dt><dd>{{ price(item.value) }}</dd></div>
          </dl>
        </section>

        <h3>3.3 项目首年收益结构</h3>
        <div class="ir-report-revenue-layout">
          <ReportChart title="项目首年收益结构" unit="单位：万元" kind="revenue" :data="{ donut: calculation.advanced?.donut }" />
          <table class="ir-report-table ir-report-revenue-table">
            <thead><tr><th>收益项</th><th>金额（万元）</th><th>占比</th></tr></thead>
            <tbody>
              <tr v-for="item in revenueRows" :key="item.name"><td>{{ item.name }}</td><td class="xc-num">{{ formatNumber(item.value) }}</td><td class="xc-num">{{ formatNumber(item.ratio * 100, 1) }}%</td></tr>
              <tr class="ir-report-revenue-total"><th>合计</th><th class="xc-num">{{ formatNumber(revenueTotal) }}</th><th class="xc-num">100.0%</th></tr>
              <tr v-if="!revenueRows.length"><td colspan="3">{{ missing }}</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="ir-report-section">
        <h2 class="ir-report-chapter-heading">第四章 项目测算边界</h2>
        <h3>4.1 测算边界参数</h3>
        <p class="ir-report-intro">本节固化所有输入参数的取值依据，确保不同项目间结果可比、可追溯。</p>
        <table class="ir-report-table ir-report-boundary-table">
          <thead><tr><th>参数类别</th><th>参数名称</th><th>基准值</th><th>取值依据</th></tr></thead>
          <tbody>
            <tr v-for="item in measurementBoundaryRows" :key="item.name">
              <td>{{ item.category }}</td><td>{{ item.name }}</td><td class="xc-num">{{ item.value }}</td><td>{{ item.rationale }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="ir-report-section">
        <h2 class="ir-report-chapter-heading">第五章 主模型分析</h2>
        <div class="ir-report-chart-grid">
          <ReportChart title="现金流口径下偿债倍数" unit="单位：倍" kind="coverage" :data="{ coverage: charts.series?.debtServiceCoverage }" />
          <ReportChart title="经营性现金流对还本付息覆盖能力" unit="单位：万元" kind="cashflow" :data="charts.series" />
          <ReportChart title="会计净利润" unit="单位：万元" kind="profit" :data="charts.series" />
        </div>
        <AiSection v-for="key in ['debt_service_coverage', 'operating_cashflow', 'accounting_profit']" :key="key" :section="report.aiSections?.[key]" :fallback="aiFallback" />
      </section>

      <section class="ir-report-section">
        <h2 class="ir-report-chapter-heading">第六章 敏感情景测试</h2>
        <ReportChart title="压力情景下的平均偿债覆盖倍数" unit="单位：倍" kind="sensitivity" :data="charts.sensitivity" />
        <AiSection :section="report.aiSections?.sensitivity" :fallback="aiFallback" />
      </section>

      <section class="ir-report-section">
        <h2 class="ir-report-chapter-heading">第七章 结论与投资建议</h2>
        <ReportChart title="风险 - 收益决策矩阵" kind="matrix" :data="charts.sensitivity" />
        <h3>6.2 投资判断阈值</h3>
        <table class="ir-report-table">
          <thead><tr><th>判断条件</th><th>投资建议</th><th>后续动作</th></tr></thead>
          <tbody><tr v-for="item in decisionRows" :key="item.advice"><td>{{ item.condition }}</td><td>{{ item.advice }}</td><td>{{ item.action }}</td></tr></tbody>
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

const AiSection = { props: ['section', 'fallback'], template: '<div class="ir-report-ai"><p>{{ section?.text || fallback }}</p></div>' }
const route = useRoute()
const router = useRouter()
const report = ref(null)
const loaded = ref(false)
const missing = computed(() => report.value?.missingDataText || '需补充核实：____')
const aiFallback = '本节智能分析暂未生成，不影响测算数据、图表及规则化内容的展示。'
const project = computed(() => report.value?.project || {})
const projectName = computed(() => project.value.name || String(report.value?.title || '').replace(/测算方案$/, ''))
const market = computed(() => report.value?.marketSupplyDemand || {})
const operations = computed(() => report.value?.marketOperations || {})
const boundary = computed(() => report.value?.measurementBoundary || {})
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
  ['年限类', '经营期', boundary.value.operationYears, 'years', '电池系统设计寿命'],
  ['年限类', '折现率', boundary.value.discountRate, 'percent', '财务部估算标准'],
  ['税率类', '电能量收入增值税', boundary.value.energyRevenueVatRate, 'percent', '国家税务总局规定'],
  ['税率类', '辅助服务收入增值税', boundary.value.ancillaryServiceVatRate, 'percent', ''],
  ['税率类', '容量补偿收入增值税', boundary.value.capacityCompensationVatRate, 'percent', ''],
  ['税率类', '容量租赁收入增值税', boundary.value.capacityLeaseVatRate, 'percent', ''],
  ['税率类', '补贴收入增值税', boundary.value.subsidyVatRate, 'percent', ''],
  ['税率类', '干预补偿收入增值税', boundary.value.interventionCompensationVatRate, 'percent', ''],
  ['税率类', '所得税', boundary.value.incomeTaxRate, 'percent', '西部大开发地区可适用15%'],
].map(([category, name, value, format, rationale]) => ({ category, name, value: formatBoundaryValue(value, format), rationale })))
const decisionRows = [
  { condition: '基准平均偿债倍数 ≥ 1.50 且 悲观平均偿债倍数 ≥ 1.20', advice: '建议投资', action: '进入详细尽调、设备选型与商务条款固化' },
  { condition: '基准平均偿债倍数 ≥ 1.50，悲观平均偿债倍数为 1.00-1.20', advice: '可投但需锁定风险', action: '锁定EPC合同价、主要收入来源和政策保障边界' },
  { condition: '基准平均偿债倍数为 1.30-1.50 且 悲观平均偿债倍数 ≥ 1.00', advice: '观察', action: '等待收入政策明朗或寻找成本改善空间' },
  { condition: '基准平均偿债倍数为 1.20-1.30 或 悲观平均偿债倍数 < 1.00', advice: '暂缓', action: '重新校核收入假设、融资结构和还款节奏' },
  { condition: '基准平均偿债倍数 < 1.20，或贷款期内出现年度偿债缺口', advice: '不建议投资', action: '项目偿债安全边际不足，暂不具备投资价值' },
]

onMounted(async () => { try { report.value = (await getReport(route.params.reportId)).data || null } finally { loaded.value = true } })
function printReport() { window.print() }
function blank(value) { return value == null ? '' : String(value) }
function blankUnit(value, unit) { return value == null ? '' : `${formatNumber(value)} ${unit}` }
function checkbox(checked, label) { return `${checked ? '☑' : '□'} ${label}` }
function marketStatus(enabled) { return `${checkbox(enabled, '已启动')}　${checkbox(!enabled, '未启动')}` }
function projectImpact(enabled) { return `${checkbox(enabled, '纳入测算')}　${checkbox(!enabled, '不纳入')}` }
function price(value) { return value == null ? missing.value : `${formatPrice(value)} 元/kWh` }
function formatBoundaryValue(value, format) {
  if (value == null || value === '') return missing.value
  if (format === 'percent') return `${formatNumber(Number(value) * 100, 2)}%`
  if (format === 'days') return `${formatNumber(value)}天`
  if (format === 'years') return `${formatNumber(value)}年`
  return format === 'text' ? String(value) : formatNumber(value)
}
</script>

<style scoped>
.ir-report-page { min-height: 100%; overflow: auto; padding: 32px 96px 64px; background: var(--xc-surface-base); color: var(--xc-text-default); }
.ir-report-actions { position: fixed; z-index: 10; right: 32px; top: 32px; display: flex; gap: 8px; }.ir-report-action { min-width: 82px; height: 34px; border: 1px solid var(--xc-border-card); border-radius: 4px; background: var(--xc-surface-raised); color: var(--xc-text-default); font-size: 13px; cursor: pointer; }.ir-report-action--primary { border-color: var(--xc-accent-blue); background: var(--xc-accent-blue); color: var(--xc-text-inverse); }
.ir-report-document { width: 210mm; min-height: 297mm; box-sizing: border-box; margin: 0 auto; padding: 20mm 21mm 26mm; background: var(--xc-surface-raised); box-shadow: var(--xc-shadow-lg); font-family: var(--xc-font-zh); line-height: 1.7; }
.ir-report-cover { min-height: 257mm; display: flex; flex-direction: column; justify-content: center; padding: 0 16mm; break-after: page; }.ir-report-cover h1 { margin: 0 0 72mm; color: var(--xc-text-strong); text-align: center; font-size: 30px; font-weight: var(--xc-fw-semi); line-height: 1.5; letter-spacing: 2px; }.ir-report-cover h1 span { display: block; }.ir-report-cover dl { width: 100%; margin: 0; font-size: 15px; }.ir-report-cover dl div { display: flex; margin: 14px 0; }.ir-report-cover dt { min-width: 86px; }.ir-report-cover dd { margin: 0; }
.ir-report-section { margin-top: 64px; padding-top: 18px; break-before: page; }.ir-report-section--chapter { margin-top: 0; padding-top: 0; }.ir-report-chapter-heading { display: block; margin: 0 0 26px; padding: 14px 0 12px; border-top: 2px solid var(--xc-text-strong); border-bottom: 1px solid var(--xc-border-line); color: var(--xc-text-strong); font-size: 22px; font-weight: var(--xc-fw-semi); letter-spacing: .5px; line-height: 1.4; }
h3 { margin: 24px 0 12px; color: var(--xc-text-strong); font-size: 15px; font-weight: var(--xc-fw-semi); } h4 { margin: 0; font-size: 14px; font-weight: var(--xc-fw-semi); }
.ir-report-table { width: 100%; border-collapse: collapse; font-size: 12px; break-inside: avoid; }.ir-report-table th, .ir-report-table td { padding: 8px 10px; border: 1px solid var(--xc-border-line); text-align: left; vertical-align: top; }.ir-report-table th { background: var(--xc-surface-control); color: var(--xc-text-soft); font-weight: var(--xc-fw-medium); }.ir-report-table td { color: var(--xc-text-default); }.ir-report-table--four th { width: 16%; }.ir-report-table--four td { width: 34%; }.ir-report-boundary-table th:nth-child(1) { width: 13%; }.ir-report-boundary-table th:nth-child(2) { width: 28%; }.ir-report-boundary-table th:nth-child(3) { width: 18%; }.ir-report-boundary-table th:nth-child(4) { width: 41%; }.ir-report-boundary-table th { white-space: nowrap; }.ir-report-boundary-table td { break-inside: avoid; }.ir-report-role { line-height: 1.8; }.ir-report-policy-table td:nth-child(2), .ir-report-policy-table td:nth-child(3) { white-space: nowrap; }
.ir-report-market-copy p { margin: 0 0 12px; white-space: pre-line; text-align: justify; text-indent: 2em; }.ir-report-market-copy__label { margin-bottom: 0 !important; font-weight: var(--xc-fw-semi); text-indent: 0 !important; }
.ir-report-operation-group { margin: 14px 0 18px; break-inside: avoid; }.ir-report-operation-group dl { margin: 8px 0 0; }.ir-report-operation-group dl div { display: flex; padding: 3px 0; }.ir-report-operation-group dt { min-width: 156px; }.ir-report-operation-group dd { margin: 0; }
.ir-report-revenue-layout { display: grid; grid-template-columns: minmax(0, 3fr) minmax(230px, 2fr); gap: 16px; align-items: stretch; break-inside: avoid; }.ir-report-revenue-layout :deep(.ir-report-chart) { min-height: 312px; }.ir-report-revenue-table { align-self: stretch; }.ir-report-revenue-total th { color: var(--xc-text-strong); }
.ir-report-chart-grid { display: grid; gap: 16px; }.ir-report-ai { margin-top: 10px; padding: 12px 14px; border-left: 3px solid var(--xc-accent-blue); background: var(--xc-surface-control); color: var(--xc-text-soft); font-size: 13px; }.ir-report-ai p { margin: 0; }.ir-report-empty { width: 700px; margin: 120px auto; color: var(--xc-text-mute); text-align: center; }
@media (max-width: 1000px) { .ir-report-page { padding: 16px; }.ir-report-actions { right: 16px; top: 16px; }.ir-report-document { width: 210mm; margin: 0; }.ir-report-cover { min-height: 257mm; }.ir-report-revenue-layout { grid-template-columns: minmax(0, 3fr) minmax(230px, 2fr); } }
</style>

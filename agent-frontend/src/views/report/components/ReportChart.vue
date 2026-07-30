<template>
  <section class="ir-report-chart">
    <div ref="el" class="ir-report-chart__canvas" />
    <img v-if="snapshot" class="ir-report-chart__print" :src="snapshot" alt="" />
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { formatNumber } from '@/utils/formatNumber'
import { useEcharts, xcChartColors, xcVar } from '@/views/home/composables/useEcharts'

const props = defineProps({
  kind: { type: String, required: true },
  data: { type: Object, default: () => ({}) },
})

const snapshot = ref('')

const numbers = (values) => (values || []).map((value) => (typeof value === 'number' ? value : null))
const years = (length) => Array.from({ length }, (_, index) => `第${index + 1}年`)
const seriesData = computed(() => props.data || {})

const option = () => {
  const d = seriesData.value
  const ink = xcVar('--xc-text-soft')
  const grid = xcVar('--xc-report-grid') || xcVar('--xc-border-soft')
  const colors = xcChartColors()
  const axis = { axisLine: { lineStyle: { color: grid } }, axisLabel: { color: ink }, splitLine: { lineStyle: { color: grid, type: 'dashed' } } }
  const tooltip = { trigger: 'axis', axisPointer: { type: 'cross' }, textStyle: { fontFamily: 'var(--xc-font-zh)' } }

  if (props.kind === 'revenue') {
    const donut = d.donut || {}
    const slices = [
      ['电能量', donut.energyRevenue], ['容量市场', donut.capacityRevenue], ['调频市场', donut.frequencyRevenue],
      ['租赁市场', donut.leaseRevenue], ['干预补偿', donut.interventionRevenue], ['补贴', donut.subsidyRevenue],
    ].map(([name, value], index) => ({ name, value, color: colors[index] }))
      .filter(({ value }) => typeof value === 'number' && value > 0)
      .map(({ name, value, color }) => ({ name, value, itemStyle: { color } }))
    return {
      color: colors,
      tooltip: { trigger: 'item', formatter: ({ name, value, percent }) => `${name}: ${formatNumber(value, 4)} 万元 (${formatNumber(percent, 2)}%)` },
      legend: {
        show: true,
        orient: 'vertical',
        right: 8,
        top: 'middle',
        itemWidth: 9,
        itemHeight: 9,
        itemGap: 12,
        icon: 'circle',
        selectedMode: false,
        textStyle: { color: ink },
        data: slices.map(({ name }) => name),
      },
      series: [{
        type: 'pie', radius: ['40%', '66%'], center: ['36%', '50%'],
        itemStyle: { borderColor: xcVar('--xc-surface-raised'), borderWidth: 2 },
        label: { show: false }, data: slices,
      }],
    }
  }
  if (props.kind === 'coverage') {
    const coverage = numbers(d.coverage)
    const lastDataIndex = coverage.reduce((lastIndex, value, index) => (
      value === null ? lastIndex : index
    ), -1)
    const ratios = lastDataIndex < 0 ? [] : coverage.slice(0, lastDataIndex + 1)
    const toDisplayValue = (value) => Math.round((value <= 1 ? value / 0.5 : 2 + (value - 1) / 0.2) * 10) / 10
    const toRatioValue = (value) => (value <= 2 ? value * 0.5 : 1 + (value - 2) * 0.2)
    const displayValues = ratios.map((value) => (value === null ? null : toDisplayValue(value)))
    const safetyAreaValues = ratios.map((value, index) => (
      value === null ? null : Math.max(2, displayValues[index])
    ))
    const maxRatio = Math.max(1, ...ratios.filter((value) => value !== null))
    const displayMax = Math.max(2, Math.ceil((maxRatio - 1) / 0.2) + 2)
    return {
      color: [colors[0]],
      tooltip: {
        ...tooltip,
        formatter: (params) => {
          const point = params.find((item) => ratios[item.dataIndex] !== null)
          return point ? `${point.axisValue}<br/>偿债倍数：${formatNumber(ratios[point.dataIndex])} 倍` : ''
        },
      },
      grid: { left: 52, right: 24, top: 26, bottom: 42 },
      xAxis: { type: 'category', boundaryGap: false, data: years(ratios.length), ...axis },
      yAxis: {
        type: 'value', name: '倍数', nameLocation: 'middle', nameGap: 38,
        min: 0, max: displayMax, interval: 1, ...axis,
        axisLabel: { color: ink, formatter: (value) => toRatioValue(value).toFixed(1) },
      },
      series: ratios.length ? [
        {
          name: '偿债覆盖倍数', type: 'line', data: displayValues, smooth: true,
          symbol: 'circle', symbolSize: 7, connectNulls: false, lineStyle: { width: 2 },
          markLine: {
            symbol: 'none', lineStyle: { color: xcVar('--xc-status-danger'), type: 'dashed' },
            label: { show: true, formatter: '警戒线 1.0', position: 'insideEndTop', color: xcVar('--xc-status-danger') },
            data: [{ yAxis: 2 }],
          },
          markArea: {
            silent: true,
            data: [[{ yAxis: 0, itemStyle: { color: xcVar('--xc-status-danger-soft') } }, { yAxis: 2 }]],
          },
        },
        {
          type: 'line', data: safetyAreaValues, showSymbol: false, lineStyle: { opacity: 0 },
          areaStyle: { color: xcVar('--xc-accent-blue-soft'), origin: 2 }, tooltip: { show: false },
          silent: true, z: 0,
        },
      ] : [],
    }
  }
  if (props.kind === 'cashflow') {
    const keys = ['principal', 'interest', 'freeCashflow', 'operatingCashflow']
    const rawSeries = Object.fromEntries(keys.map((key) => [key, numbers(d[key])]))
    const lastDataIndex = Math.max(-1, ...keys.map((key) => rawSeries[key].reduce((lastIndex, value, index) => (
      value === null ? lastIndex : index
    ), -1)))
    const count = lastDataIndex + 1
    const values = Object.fromEntries(keys.map((key) => [key, rawSeries[key].slice(0, count)]))
    return {
      color: [xcVar('--xc-accent-blue-2'), xcVar('--xc-status-warn'), xcVar('--xc-accent-blue'), xcVar('--xc-chart-7')],
      tooltip: {
        ...tooltip,
        formatter: (params) => `${params[0]?.axisValue || ''}${params.map((item) => (
          `<br/>${item.marker}${item.seriesName}：${formatNumber(item.value, 4)} 万元`
        )).join('')}`,
      },
      legend: { bottom: 0, textStyle: { color: ink } },
      grid: { left: 58, right: 24, top: 28, bottom: 48 },
      xAxis: { type: 'category', data: years(count), ...axis },
      yAxis: { type: 'value', name: '万元', nameLocation: 'middle', nameGap: 42, ...axis },
      series: [
        { name: '还本', type: 'bar', stack: 'debt', data: values.principal, itemStyle: { borderRadius: [2, 2, 0, 0] } },
        { name: '付息', type: 'bar', stack: 'debt', data: values.interest },
        { name: '偿债后自由现金流', type: 'bar', stack: 'debt', data: values.freeCashflow },
        { name: '经营性现金流', type: 'line', data: values.operatingCashflow, symbol: 'circle', symbolSize: 6, lineStyle: { width: 2.5 } },
      ],
    }
  }
  if (props.kind === 'profit') {
    const netProfit = numbers(d.netProfit)
    const depreciationAmortization = numbers(d.depreciationAmortization)
    return {
      color: [xcVar('--xc-accent-blue-2'), xcVar('--xc-chart-7')],
      tooltip: {
        ...tooltip,
        formatter: (params) => `${params[0]?.axisValue || ''}${params.map((item) => (
          `<br/>${item.marker}${item.seriesName}：${formatNumber(item.value, 4)} 万元`
        )).join('')}`,
      },
      legend: { bottom: 0, textStyle: { color: ink } },
      grid: { left: 58, right: 24, top: 28, bottom: 48 },
      xAxis: { type: 'category', data: years(Math.max(netProfit.length, depreciationAmortization.length)), ...axis },
      yAxis: { type: 'value', name: '万元', nameLocation: 'middle', nameGap: 42, ...axis },
      series: [
        { name: '净利润', type: 'bar', data: netProfit, itemStyle: { borderRadius: [3, 3, 0, 0] } },
        { name: '折旧摊销', type: 'line', data: depreciationAmortization, symbol: 'circle', symbolSize: 6, lineStyle: { width: 2.5 } },
      ],
    }
  }
  if (props.kind === 'sensitivity') {
    const values = [['基准场景', d.baseline], ['乐观场景', d.optimistic], ['悲观场景', d.pessimistic]]
    return {
      color: [xcVar('--xc-accent-blue-2')],
      tooltip: { show: false },
      grid: { left: 84, right: '18%', top: 24, bottom: 42 },
      xAxis: { type: 'value', show: false, min: 0, ...axis },
      yAxis: { type: 'category', data: values.map(([name]) => name), ...axis },
      series: [
        {
          type: 'bar',
          data: values.map(([, value]) => ({ value, itemStyle: { borderRadius: [0, 4, 4, 0], color: xcVar('--xc-accent-blue-2') } })),
          barWidth: 28,
          label: {
            show: true, position: 'right', color: ink,
            formatter: ({ value }) => `${formatNumber(value, 2)} 倍`,
          },
          z: 2, zlevel: 1,
        },
        {
          type: 'line', data: [], silent: true, symbol: 'none', z: 0, zlevel: 0,
          markLine: {
            silent: true, z: -1, zlevel: -1,
            symbol: 'none', lineStyle: { color: xcVar('--xc-status-danger'), type: 'dashed' },
            label: {
              show: true, formatter: '警戒线 1.0', position: 'end', distance: 8,
              color: xcVar('--xc-status-danger'), align: 'left', verticalAlign: 'top',
            },
            data: [{ xAxis: 1 }],
          },
        },
      ],
    }
  }
  const baseline = d.baseline
  const pessimistic = d.pessimistic
  const investmentAdvice = (() => {
    if (typeof baseline !== 'number' || typeof pessimistic !== 'number') return ''
    if (baseline < 1) return '不建议投资'
    if (pessimistic < 1) return '暂缓'
    if (baseline >= 1.1 && pessimistic >= 1.1) return '建议投资'
    if (baseline >= 1.1) return '可投但需锁定风险'
    if (baseline >= 1.05) return '观察'
    return '暂缓'
  })()
  const axisMax = (value, threshold) => Math.ceil(Math.max(value, threshold) * 1.1 / 0.5) * 0.5
  const projectPoint = typeof baseline === 'number' && typeof pessimistic === 'number'
    ? {
        value: [pessimistic, baseline],
        label: { show: true, formatter: investmentAdvice, position: 'right', distance: 10, color: ink },
      }
    : null
  return {
    color: [xcVar('--xc-accent-blue-2')],
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        const [pessimisticValue, baselineValue] = params.data?.value || params.value || []
        return `悲观情景平均偿债倍数：${formatNumber(pessimisticValue, 2)} 倍<br/>基准情景平均偿债倍数：${formatNumber(baselineValue, 2)} 倍`
      },
    },
    grid: { left: 94, right: 88, top: 28, bottom: 42 },
    xAxis: {
      type: 'value', name: '悲观情景平均偿债倍数', min: 0, interval: 0.5,
      max: typeof pessimistic === 'number' ? axisMax(pessimistic, 1) : undefined, ...axis,
    },
    yAxis: {
      type: 'value', name: '基准情景平均偿债倍数', min: 0, interval: 0.5,
      max: typeof baseline === 'number' ? axisMax(baseline, 1.1) : undefined, ...axis,
    },
    series: [{
      type: 'scatter', name: '本项目', data: projectPoint ? [projectPoint] : [], symbolSize: 16,
    }],
  }
}
const { el, getDataURL } = useEcharts(option, {
  // 每次重绘后缓存一张 PNG 快照。打印时用 <img> 替换 ECharts 的绝对定位 <canvas>，
  // 图片 width:100% 天然不会溢出边框，规避画布按屏幕宽度绘制导致的偏移/出框。
  onRendered: ({ getDataURL: snap }) => {
    snapshot.value = snap({ type: 'png', pixelRatio: 2, backgroundColor: xcVar('--xc-report-card') })
  },
})
defineExpose({
  toPrintImage: () => getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: xcVar('--xc-report-card') }),
})
</script>

<style scoped>
.ir-report-chart { width: 100%; min-height: 300px; break-inside: avoid; }
.ir-report-chart__canvas { width: 100%; height: 300px; }
.ir-report-chart__print { display: none; }
@media print {
  /* 打印态隐藏实时画布、改用等宽自适应的静态快照，杜绝出框 */
  .ir-report-chart__canvas { display: none !important; }
  .ir-report-chart__print { display: block !important; width: 100% !important; height: auto !important; }
}
</style>

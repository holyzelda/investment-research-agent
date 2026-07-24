<template>
  <section class="ir-report-chart">
    <div class="ir-report-chart__head">
      <h3>{{ title }}</h3>
      <span v-if="unit" class="ir-report-chart__unit">{{ unit }}</span>
    </div>
    <div ref="el" class="ir-report-chart__canvas" />
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useEcharts, xcChartColors, xcVar } from '@/views/home/composables/useEcharts'

const props = defineProps({
  title: { type: String, required: true },
  unit: { type: String, default: '' },
  kind: { type: String, required: true },
  data: { type: Object, default: () => ({}) },
})

const numbers = (values) => (values || []).map((value) => (typeof value === 'number' ? value : null))
const years = (length) => Array.from({ length }, (_, index) => `第${index + 1}年`)
const seriesData = computed(() => props.data || {})

const option = () => {
  const d = seriesData.value
  const ink = xcVar('--xc-text-soft')
  const grid = xcVar('--xc-border-soft')
  const colors = xcChartColors()
  const axis = { axisLine: { lineStyle: { color: grid } }, axisLabel: { color: ink }, splitLine: { lineStyle: { color: grid, type: 'dashed' } } }
  const tooltip = { trigger: 'axis', axisPointer: { type: 'cross' }, textStyle: { fontFamily: 'var(--xc-font-zh)' } }

  if (props.kind === 'revenue') {
    const donut = d.donut || {}
    const slices = [
      ['电能量', donut.energyRevenue], ['容量市场', donut.capacityRevenue], ['调频市场', donut.frequencyRevenue],
      ['租赁市场', donut.leaseRevenue], ['干预补偿', donut.interventionRevenue], ['补贴', donut.subsidyRevenue],
    ].filter(([, value]) => typeof value === 'number' && value > 0).map(([name, value]) => ({ name, value }))
    return { color: colors, tooltip: { trigger: 'item' }, legend: { bottom: 0, textStyle: { color: ink } }, series: [{ type: 'pie', radius: ['42%', '68%'], center: ['50%', '44%'], itemStyle: { borderColor: xcVar('--xc-surface-raised'), borderWidth: 2 }, label: { show: false }, data: slices }] }
  }
  if (props.kind === 'coverage') {
    const values = numbers(d.coverage)
    return { color: [colors[0]], tooltip, grid: { left: 52, right: 24, top: 26, bottom: 42 }, xAxis: { type: 'category', data: years(values.length), ...axis }, yAxis: { type: 'value', name: '倍数', ...axis }, series: [{ name: '偿债覆盖倍数', type: 'line', data: values, symbol: 'circle', symbolSize: 7, lineStyle: { width: 2 }, markLine: { symbol: 'none', lineStyle: { color: xcVar('--xc-status-danger'), type: 'dashed' }, label: { formatter: '1.0 警戒线' }, data: [{ yAxis: 1 }] } }] }
  }
  if (props.kind === 'cashflow') {
    const count = Math.max(...['principal', 'interest', 'freeCashflow', 'operatingCashflow'].map((key) => (d[key] || []).length), 0)
    return { color: [colors[1], colors[2], colors[4], colors[0]], tooltip, legend: { bottom: 0, textStyle: { color: ink } }, grid: { left: 58, right: 24, top: 28, bottom: 48 }, xAxis: { type: 'category', data: years(count), ...axis }, yAxis: { type: 'value', name: '万元', ...axis }, series: [
      { name: '还本', type: 'bar', stack: 'debt', data: numbers(d.principal) }, { name: '付息', type: 'bar', stack: 'debt', data: numbers(d.interest) },
      { name: '偿债后自由现金流', type: 'bar', stack: 'debt', data: numbers(d.freeCashflow) }, { name: '经营性现金流', type: 'line', data: numbers(d.operatingCashflow), symbol: 'circle', symbolSize: 6, lineStyle: { width: 2 } },
    ] }
  }
  if (props.kind === 'profit') {
    const count = Math.max((d.netProfit || []).length, (d.depreciationAmortization || []).length)
    return { color: [colors[1], colors[0]], tooltip, legend: { bottom: 0, textStyle: { color: ink } }, grid: { left: 58, right: 24, top: 28, bottom: 48 }, xAxis: { type: 'category', data: years(count), ...axis }, yAxis: { type: 'value', name: '万元', ...axis }, series: [{ name: '净利润', type: 'bar', data: numbers(d.netProfit), itemStyle: { borderRadius: [3, 3, 0, 0] } }, { name: '折旧摊销', type: 'line', data: numbers(d.depreciationAmortization), symbol: 'circle', symbolSize: 6, lineStyle: { width: 2 } }] }
  }
  if (props.kind === 'sensitivity') {
    const values = [['基准场景', d.baseline], ['乐观场景', d.optimistic], ['悲观场景', d.pessimistic]]
    return { color: [colors[0]], tooltip: { trigger: 'axis' }, grid: { left: 84, right: 28, top: 24, bottom: 30 }, xAxis: { type: 'value', name: '平均偿债倍数', ...axis }, yAxis: { type: 'category', data: values.map(([name]) => name), ...axis }, series: [{ type: 'bar', data: values.map(([, value]) => value), itemStyle: { borderRadius: [0, 4, 4, 0] }, markLine: { symbol: 'none', lineStyle: { color: xcVar('--xc-status-danger'), type: 'dashed' }, label: { formatter: '1.0 警戒线' }, data: [{ xAxis: 1 }] } }] }
  }
  const baseline = d.baseline
  const pessimistic = d.pessimistic
  return { color: [colors[0]], tooltip: { trigger: 'item' }, grid: { left: 52, right: 26, top: 28, bottom: 42 }, xAxis: { type: 'value', name: '悲观情景平均偿债倍数', ...axis }, yAxis: { type: 'value', name: '基准情景平均偿债倍数', ...axis }, series: [{ type: 'scatter', name: '本项目', data: typeof baseline === 'number' && typeof pessimistic === 'number' ? [[pessimistic, baseline]] : [], symbolSize: 16, markLine: { symbol: 'none', data: [{ xAxis: 1, lineStyle: { type: 'dashed', color: xcVar('--xc-status-danger') } }, { yAxis: 1.5, lineStyle: { type: 'dashed', color: xcVar('--xc-status-ok') } }] } }] }
}
const { el } = useEcharts(option)
</script>

<style scoped>
.ir-report-chart { min-height: 280px; padding: 18px; border: 1px solid var(--xc-border-line); background: var(--xc-surface-raised); break-inside: avoid; }
.ir-report-chart__head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 6px; }
.ir-report-chart__head h3 { margin: 0; font-size: 15px; color: var(--xc-text-strong); }
.ir-report-chart__unit { font-size: 12px; color: var(--xc-text-mute); }
.ir-report-chart__canvas { width: 100%; height: 245px; }
</style>

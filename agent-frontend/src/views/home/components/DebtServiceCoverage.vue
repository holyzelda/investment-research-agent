<template>
  <div class="ir-chart ir-chart--report">
    <div class="ir-chart__head">
      <span class="ir-chart__title">偿债覆盖倍数</span>
    </div>
    <div ref="el" class="ir-chart__canvas" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatNumber } from '@/utils/formatNumber'
import { useEcharts, xcVar } from '../composables/useEcharts'

const props = defineProps({ coverage: { type: Object, default: () => ({}) } })
const ratios = computed(() => (
  Array.isArray(props.coverage?.cashflowRatio) ? props.coverage.cashflowRatio : []
))

const accent = xcVar('--xc-accent-blue')
const accentSoft = xcVar('--xc-accent-blue-soft')
const danger = xcVar('--xc-status-danger')
const dangerSoft = xcVar('--xc-status-danger-soft')
const surface = xcVar('--xc-surface-raised')

const toDisplayValue = (value) => Math.round((value <= 1 ? value / 0.5 : 2 + (value - 1) / 0.2) * 10) / 10
const toRatioValue = (value) => (value <= 2 ? value * 0.5 : 1 + (value - 2) * 0.2)

const buildOption = () => {
  const data = ratios.value
  const displayData = data.map((value) => (value === null ? null : toDisplayValue(value)))
  const safetyAreaData = data.map((value, index) => {
    if (value === null) return null
    return Math.max(2, displayData[index])
  })
  const maxRatio = Math.max(1, ...data.filter((value) => value !== null))
  const displayMax = Math.max(2, Math.ceil((maxRatio - 1) / 0.2) + 2)
  const xAxis = Array.from({ length: data.length }, (_, index) => `第${index + 1}年`)
  const tooltipFormatter = (params) => {
    const point = params.find((item) => data[item.dataIndex] !== null)
    if (!point) return ''
    return `${point.axisValue}<br/>偿债倍数：${formatNumber(data[point.dataIndex])} 倍`
  }
  const series = data.length
    ? [{
        name: '偿债倍数',
        type: 'line',
        smooth: true,
        showSymbol: true,
        symbol: 'circle',
        symbolSize: 8,
        connectNulls: false,
        color: accent,
        lineStyle: { width: 2 },
        itemStyle: { color: accent, borderColor: surface, borderWidth: 2 },
        data: displayData,
        markLine: {
          symbol: 'none',
          lineStyle: { color: danger, type: 'dashed', width: 1.5 },
          label: {
            show: true,
            formatter: '警戒线 1.0',
            position: 'insideEndTop',
            color: danger,
            fontSize: 11,
          },
          data: [{ yAxis: 2 }],
        },
        markArea: {
          silent: true,
          data: [[
            { yAxis: 0, itemStyle: { color: dangerSoft } },
            { yAxis: 2 },
          ]],
        },
      }]
    : []

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: tooltipFormatter,
    },
    legend: {
      top: 0,
      textStyle: { color: xcVar('--xc-text-soft'), fontSize: 12 },
    },
    grid: { left: 8, right: 16, bottom: 8, top: 36, containLabel: true },
    xAxis: {
      type: 'category',
      name: '贷款年限',
      boundaryGap: false,
      data: xAxis,
      axisLabel: { color: xcVar('--xc-text-mute'), fontSize: 11 },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: xcVar('--xc-border-soft') } },
    },
    yAxis: {
      type: 'value',
      name: '偿债倍数',
      min: 0,
      max: displayMax,
      interval: 1,
      nameTextStyle: { color: xcVar('--xc-text-mute'), fontSize: 11 },
      axisLabel: {
        color: xcVar('--xc-text-mute'),
        fontSize: 11,
        formatter: (value) => toRatioValue(value).toFixed(1),
      },
      splitLine: { lineStyle: { color: xcVar('--xc-border-soft') } },
      axisTick: { show: false },
    },
    series: [
      ...series,
      ...(data.length ? [{
        type: 'line',
        data: safetyAreaData,
        showSymbol: false,
        lineStyle: { opacity: 0 },
        areaStyle: { color: accentSoft, origin: 2 },
        tooltip: { show: false },
        silent: true,
        z: 0,
      }] : []),
    ],
  }
}

const { el } = useEcharts(buildOption)
</script>

<style scoped>
.ir-chart--report {
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-lg);
  background: var(--xc-surface-control);
  box-shadow: var(--xc-shadow-sm);
  padding: var(--xc-space-7);
  margin-top: var(--xc-space-5);
}
.ir-chart__head { margin-bottom: var(--xc-space-2); }
.ir-chart__title { font-size: var(--xc-fs-sm); color: var(--xc-text-strong); }
.ir-chart__canvas { width: 100%; height: 260px; }
</style>

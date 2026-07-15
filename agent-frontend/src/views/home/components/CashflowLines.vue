<template>
  <div class="ir-chart">
    <div class="ir-chart__head">
      <span class="ir-chart__title">15 年现金流序列</span>
    </div>
    <div ref="el" class="ir-chart__canvas" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatNumber } from '@/utils/formatNumber'
import { useEcharts, xcChartColors, xcVar } from '../composables/useEcharts'

const props = defineProps({ lines: { type: Object, default: () => ({}) } })
const lines = computed(() => props.lines || {})

const SERIES = [
  { key: 'mainBusinessCost', name: '主营业务成本' },
  { key: 'currentPrincipalInterest', name: '当期还本付息' },
  { key: 'capitalNetCashflow', name: '资本金净现金流' },
  { key: 'totalInvestNetCashflowAfterTax', name: '全投资净现金流' },
]

const buildOption = () => {
  const l = lines.value
  const series = SERIES
    .filter((s) => Array.isArray(l[s.key]) && l[s.key].length)
    .map((s) => ({
      name: s.name,
      type: 'line',
      smooth: true,
      showSymbol: false,
      data: l[s.key],
    }))
  const maxLen = Math.max(0, ...series.map((s) => s.data.length))
  const xAxis = Array.from({ length: maxLen }, (_, i) => `第${i + 1}年`)
  return {
    color: xcChartColors(),
    tooltip: { trigger: 'axis' },
    legend: {
      type: 'scroll',
      top: 0,
      textStyle: { color: xcVar('--xc-text-soft'), fontSize: 12 },
    },
    grid: { left: 8, right: 16, bottom: 8, top: 36, containLabel: true },
    xAxis: {
      type: 'category',
      data: xAxis,
      axisLabel: { color: xcVar('--xc-text-mute'), fontSize: 11 },
      axisLine: { lineStyle: { color: xcVar('--xc-border-soft') } },
    },
    yAxis: {
      type: 'value',
      name: '万元',
      nameTextStyle: { color: xcVar('--xc-text-mute'), fontSize: 11 },
      axisLabel: {
        color: xcVar('--xc-text-mute'),
        fontSize: 11,
        formatter: (value) => formatNumber(value),
      },
      splitLine: { lineStyle: { color: xcVar('--xc-border-soft') } },
    },
    series,
  }
}

const { el } = useEcharts(buildOption)
</script>

<style scoped>
.ir-chart {
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--xc-radius-md);
  background: rgba(255, 255, 255, 0.04);
  padding: var(--xc-space-5);
  margin-top: var(--xc-space-4);
}
.ir-chart__head {
  margin-bottom: var(--xc-space-2);
}
.ir-chart__title {
  font-size: var(--xc-fs-sm);
  color: var(--xc-text-strong);
}
.ir-chart__canvas {
  width: 100%;
  height: 260px;
}
</style>

<template>
  <div class="ir-chart">
    <div class="ir-chart__head">
      <span class="ir-chart__title">首年收入结构</span>
      <span class="ir-chart__total xc-num">首年总收入 {{ formatNumber(donut.totalRevenue) }} 万元</span>
    </div>
    <div ref="el" class="ir-chart__canvas" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatNumber } from '@/utils/formatNumber'
import { useEcharts, xcChartColors, xcVar } from '../composables/useEcharts'

const props = defineProps({ donut: { type: Object, default: () => ({}) } })
const donut = computed(() => props.donut || {})

const SLICES = [
  { key: 'energyRevenue', name: '电能量' },
  { key: 'capacityRevenue', name: '容量市场' },
  { key: 'frequencyRevenue', name: '调频市场' },
  { key: 'leaseRevenue', name: '租赁市场' },
  { key: 'interventionRevenue', name: '干预补偿' },
  { key: 'subsidyRevenue', name: '补贴' },
]

const buildOption = () => {
  const d = donut.value
  // 环里为 0 的收益类别在视觉上不存在（0 角度扇区），图例也不应保留这类条目
  const data = SLICES
    .map((s) => ({ name: s.name, value: d[s.key] }))
    .filter((x) => typeof x.value === 'number' && x.value > 0)
  return {
    color: xcChartColors(),
    tooltip: {
      trigger: 'item',
      formatter: ({ name, value, percent }) => (
        `${name}: ${formatNumber(value)} 万元 (${formatNumber(percent)}%)`
      ),
    },
    legend: {
      type: 'scroll',
      orient: 'vertical',
      right: 8,
      top: 'center',
      textStyle: { color: xcVar('--xc-text-soft'), fontSize: 12 },
    },
    series: [
      {
        type: 'pie',
        radius: ['46%', '70%'],
        center: ['38%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: 'rgba(36, 36, 36, 0.9)', borderWidth: 2 },
        label: { show: false },
        data,
      },
    ],
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
}
.ir-chart__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: var(--xc-space-2);
}
.ir-chart__title {
  font-size: var(--xc-fs-sm);
  color: var(--xc-text-strong);
}
.ir-chart__total {
  font-size: var(--xc-fs-xs);
  color: var(--xc-text-soft);
}
.ir-chart__canvas {
  width: 100%;
  height: 240px;
}
</style>

<template>
  <div class="ir-chart ir-chart--report">
    <div class="ir-chart__head">
      <span class="ir-chart__title">首年收入结构</span>
    </div>
    <div class="ir-chart__body">
      <div ref="el" class="ir-chart__canvas" />
      <div class="ir-chart__center" aria-hidden="true">
        <span>首年总收入</span>
        <strong>{{ formatNumber(donut.totalRevenue) }}</strong>
      </div>
    </div>
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
  const baseOption = {
    color: xcChartColors(),
    tooltip: {
      trigger: 'item',
      appendToBody: true,
      formatter: ({ name, value, percent }) => (
        `${name}: ${formatNumber(value)} 万元 (${formatNumber(percent)}%)`
      ),
    },
    legend: {
      type: 'scroll',
      orient: 'vertical',
      right: 0,
      top: 'center',
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
      itemGap: 10,
      textStyle: { color: xcVar('--xc-text-soft'), fontSize: 11 },
    },
    series: [
      {
        type: 'pie',
        radius: ['48%', '68%'],
        center: ['34%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: 'rgba(36, 36, 36, 0.9)', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: false } },
        labelLine: { show: false },
        data,
      },
    ],
  }
  return {
    baseOption,
    media: [{
      query: { maxWidth: 420 },
      option: {
        legend: {
          orient: 'horizontal',
          left: 'center',
          right: 'auto',
          top: 'auto',
          bottom: 0,
        },
        series: [{ center: ['50%', '42%'], radius: ['42%', '60%'] }],
      },
    }],
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
.ir-chart__body {
  position: relative;
}
.ir-chart__canvas {
  width: 100%;
  height: 240px;
}
.ir-chart__center {
  position: absolute;
  top: 50%;
  left: 34%;
  display: flex;
  flex-direction: column;
  align-items: center;
  transform: translate(-50%, -50%);
  pointer-events: none;
  white-space: nowrap;
}
.ir-chart__center span {
  color: var(--xc-text-mute);
  font-size: 11px;
  line-height: 18px;
}
.ir-chart__center strong {
  color: var(--xc-text-strong);
  font-size: 16px;
  font-weight: 600;
  line-height: 24px;
}
@container (max-width: 480px) {
  .ir-chart--report { padding: var(--xc-space-5); }
  .ir-chart__canvas { height: 220px; }
  .ir-chart__center { top: 42%; left: 50%; }
}
</style>

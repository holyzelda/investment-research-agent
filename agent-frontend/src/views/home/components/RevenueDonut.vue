<template>
  <div class="ir-chart ir-chart--report">
    <div class="ir-chart__head">
      <span class="ir-chart__title">首年收入结构</span>
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
  const totalText = `{label|首年总收入}\n{value|${formatNumber(d.totalRevenue)}}`
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
        // 环心两行文本用 position:'center' 的标签渲染——由 ECharts 自动锚到环心，
        // 不依赖 graphic 的百分比定位，保证在任意容器尺寸下都居中。
        label: {
          show: true,
          position: 'center',
          formatter: totalText,
          rich: {
            label: { fontSize: 11, lineHeight: 18, color: xcVar('--xc-text-mute') },
            value: { fontSize: 16, lineHeight: 24, fontWeight: 600, color: xcVar('--xc-text-strong') },
          },
        },
        // 悬停某扇区时不放大标签、不覆盖环心文本
        emphasis: { label: { show: true, position: 'center', formatter: totalText } },
        labelLine: { show: false },
        data,
      },
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
.ir-chart__canvas {
  width: 100%;
  height: 240px;
}
</style>

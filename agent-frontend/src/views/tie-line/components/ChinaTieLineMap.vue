<template>
  <div ref="el" class="china-tie-line-map"></div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import chinaGeo from '@/assets/geo/china.json'
import { xcVar } from '@/views/home/composables/useEcharts'

// 中国省界底图 + 跨省联络线（lines 系列按起讫经纬度直接绘制，不依赖省名匹配）。
// 点击选中线路的事件需求使通用 useEcharts 封装不够用，故本组件自管理 ECharts 生命周期，
// 但严格对齐同一套 init / resize / dispose 语义。首版无功率方向数据，不加流动动画。
//
// 颜色一律经 xcVar 读取 --xc-* token 的运行时计算值（ECharts canvas 不解析 CSS 变量，
// 必须传具体色值），不写任何硬编码 hex/rgb 兜底。

const props = defineProps({
  lines: { type: Array, default: () => [] },
  selectedId: { type: [Number, String], default: null },
  voltageColors: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['select'])

const el = ref(null)
let chart = null

// registerMap 是进程内全局副作用，注册一次即可
let mapRegistered = false
function ensureMap() {
  if (!mapRegistered) {
    echarts.registerMap('china', chinaGeo)
    mapRegistered = true
  }
}

function fmtMw(v) {
  return v === null || v === undefined ? '—' : `${Number(v).toLocaleString('zh-CN')} MW`
}

function colorOf(voltageText) {
  return props.voltageColors[voltageText] || xcVar('--xc-chart-1')
}

// 线宽随额定容量温和增长（无容量给基础宽度），避免个别大容量线压过全图
function widthOf(cap) {
  if (!cap) return 1.6
  return 1.6 + Math.min(cap / 2000, 4)
}

function buildOption() {
  const selected = props.selectedId
  const hasSelection = selected !== null && selected !== undefined

  const lineData = props.lines.map((l) => {
    const isSel = hasSelection && l.id === selected
    return {
      id: l.id,
      name: l.name,
      coords: [
        [l.startLng, l.startLat],
        [l.endLng, l.endLat],
      ],
      lineStyle: {
        color: colorOf(l.voltageText),
        width: isSel ? widthOf(l.ratedCapacityMw) + 1.5 : widthOf(l.ratedCapacityMw),
        opacity: hasSelection ? (isSel ? 1 : 0.28) : 0.85,
      },
      info: l,
    }
  })

  // 端点（换流站）去重
  const pointMap = new Map()
  props.lines.forEach((l) => {
    const add = (lng, lat, label) => {
      const key = `${lng},${lat}`
      if (!pointMap.has(key)) pointMap.set(key, { value: [lng, lat], label })
    }
    add(l.startLng, l.startLat, l.startPoint)
    add(l.endLng, l.endLat, l.endPoint)
  })
  const pointData = Array.from(pointMap.values()).map((p) => ({ value: p.value, label: p.label }))

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: xcVar('--xc-surface-2'),
      borderColor: xcVar('--xc-border-soft'),
      textStyle: { color: xcVar('--xc-text-strong'), fontSize: 12 },
      formatter: (p) => {
        if (p.seriesType === 'lines') {
          const i = p.data.info
          return [
            `<b>${i.name}</b>`,
            `${i.startPoint} → ${i.endPoint}`,
            `电压：${i.voltageText || '—'}`,
            `容量：${fmtMw(i.ratedCapacityMw)}`,
          ].join('<br/>')
        }
        if (p.seriesType === 'scatter') return p.data.label || ''
        return ''
      },
    },
    geo: {
      map: 'china',
      roam: true,
      zoom: 1.2,
      scaleLimit: { min: 1, max: 8 },
      itemStyle: {
        areaColor: xcVar('--xc-surface-1'),
        borderColor: xcVar('--xc-border-soft'),
        borderWidth: 0.6,
      },
      emphasis: {
        itemStyle: { areaColor: xcVar('--xc-surface-tinted') },
        label: { show: false },
      },
      label: { show: false },
      regions: [
        { name: '南海诸岛', itemStyle: { areaColor: 'transparent', borderColor: 'transparent' } },
      ],
    },
    series: [
      {
        type: 'lines',
        coordinateSystem: 'geo',
        polyline: false,
        lineStyle: { curveness: 0.18 },
        emphasis: { lineStyle: { width: 4 }, focus: 'none' },
        data: lineData,
        zlevel: 2,
      },
      {
        type: 'scatter',
        coordinateSystem: 'geo',
        symbolSize: 4,
        itemStyle: { color: xcVar('--xc-text-soft'), opacity: 0.7 },
        data: pointData,
        zlevel: 3,
      },
    ],
  }
}

function onChartClick(p) {
  if (p.seriesType === 'lines' && p.data && p.data.id !== undefined) {
    emit('select', p.data.id)
  }
}
function resize() {
  chart && chart.resize()
}

onMounted(() => {
  ensureMap()
  chart = echarts.init(el.value)
  chart.setOption(buildOption())
  chart.on('click', onChartClick)
  window.addEventListener('resize', resize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  if (chart) {
    chart.off('click', onChartClick)
    chart.dispose()
    chart = null
  }
})

watch(
  () => [props.lines, props.selectedId, props.voltageColors],
  () => chart && chart.setOption(buildOption(), true),
  { deep: true },
)
</script>

<style scoped>
.china-tie-line-map {
  width: 100%;
  height: 100%;
  min-height: 0;
}
</style>

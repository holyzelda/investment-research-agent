<template>
  <div ref="el" class="china-tie-line-map"></div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import chinaGeo from '@/assets/geo/china.json'
import majorRivers from '@/assets/geo/china-major-rivers.json'
import { xcVar } from '@/views/home/composables/useEcharts'
import { buildVoltagePresentation } from '../voltagePresentation'
import { buildTieLineMapOption } from './tieLineMapOption'

// 中国省界底图 + 跨省联络线（lines 系列按起讫经纬度直接绘制，不依赖省名匹配）。
// 点击选中线路的事件需求使通用 useEcharts 封装不够用，故本组件自管理 ECharts 生命周期，
// 坐标固定按资料中的起点→终点排列；动态箭头仅提示该静态起讫方向，不代表实时潮流或功率方向。
//
// 颜色一律经 xcVar 读取 --xc-* token 的运行时计算值（ECharts canvas 不解析 CSS 变量，
// 必须传具体色值），不写任何硬编码 hex/rgb 兜底。

const props = defineProps({
  lines: { type: Array, default: () => [] },
  selectedId: { type: [Number, String], default: null },
  voltageOptions: { type: Array, default: () => [] },
})
const emit = defineEmits(['select'])

const voltageColors = computed(() => {
  const { tokenByText } = buildVoltagePresentation(props.voltageOptions)
  return Object.fromEntries(
    Object.entries(tokenByText).map(([text, token]) => [text, xcVar(token)]),
  )
})

const el = ref(null)
let chart = null
let resizeObserver = null

// registerMap 是进程内全局副作用，注册一次即可
let mapRegistered = false
function ensureMap() {
  if (!mapRegistered) {
    echarts.registerMap('china', chinaGeo)
    mapRegistered = true
  }
}

function buildOption() {
  return buildTieLineMapOption({
    lines: props.lines,
    selectedId: props.selectedId,
    voltageColors: voltageColors.value,
    unknownColor: xcVar('--xc-map-voltage-unknown'),
    rivers: majorRivers,
    theme: {
      tooltipBackground: xcVar('--xc-surface-2'),
      tooltipBorder: xcVar('--xc-border-soft'),
      tooltipText: xcVar('--xc-text-strong'),
      land: xcVar('--xc-map-land'),
      boundary: xcVar('--xc-map-boundary'),
      landHover: xcVar('--xc-map-land-hover'),
      mapLabel: xcVar('--xc-map-station'),
      station: xcVar('--xc-map-station'),
      river: xcVar('--xc-map-river'),
      riverOpacity: Number(xcVar('--xc-map-river-opacity')),
    },
  })
}

// 透明命中层承接线路 click、pointer 与 tooltip；视觉线和选中覆盖层均为静默图层。
function onChartClick(p) {
  if (
    p.seriesType === 'lines' &&
    typeof p.seriesId === 'string' &&
    p.seriesId.startsWith('tie-line-hit-') &&
    p.data?.id !== undefined
  ) {
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
  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(resize)
    resizeObserver.observe(el.value)
  }
  window.addEventListener('resize', resize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (chart) {
    chart.off('click', onChartClick)
    chart.dispose()
    chart = null
  }
})

watch(
  () => [props.lines, props.selectedId, props.voltageOptions],
  () => {
    if (!chart) return
    // 仅替换业务系列，避免选中/筛选更新时重置用户已缩放或拖拽的地图视角。
    chart.setOption(
      { series: buildOption().series },
      { notMerge: false, replaceMerge: ['series'] },
    )
  },
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

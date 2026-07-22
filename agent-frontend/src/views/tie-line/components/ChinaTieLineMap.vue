<template>
  <div ref="mapRoot" class="china-tie-line-map">
    <div ref="el" class="china-tie-line-map__canvas"></div>
    <MapToolbar
      class="china-tie-line-map__tools"
      :is-fullscreen="isFullscreen"
      :is-list-open="isListOpen"
      @zoom-in="zoomIn"
      @zoom-out="zoomOut"
      @reset="resetView"
      @toggle-fullscreen="toggleFullscreen"
      @toggle-list="toggleList"
    />
    <TieLineListPanel
      class="china-tie-line-map__list"
      :open="isListOpen"
      :lines="lines"
      :selected-id="selectedId"
      :voltage-options="voltageOptions"
      @select="emit('select', $event)"
      @close="closeList"
    />
    <div class="china-tie-line-map__note" aria-live="off">箭头表示线路资料起点至终点，不代表实时潮流或功率方向</div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import chinaGeo from '@/assets/geo/china.json'
import majorRivers from '@/assets/geo/china-major-rivers.json'
import { xcVar } from '@/views/home/composables/useEcharts'
import { buildVoltagePresentation } from '../voltagePresentation'
import MapToolbar from './MapToolbar.vue'
import TieLineListPanel from './TieLineListPanel.vue'
import {
  TIE_LINE_DEFAULT_ZOOM,
  TIE_LINE_ZOOM_LIMIT,
  buildTieLineMapOption,
} from './tieLineMapOption'

// 中国省界底图 + 跨省联络线。透明命中层承接线路 click、pointer 与 tooltip；
// 视觉线和选中覆盖层均为静默图层，动态箭头仅提示静态起讫方向。
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

const mapRoot = ref(null)
const el = ref(null)
const isListOpen = ref(true)
const isFullscreen = ref(false)
let chart = null
let resizeObserver = null
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
      lineUnderlay: xcVar('--xc-map-line-underlay'),
      flow: xcVar('--xc-map-flow'),
      landShadow: xcVar('--xc-map-land-shadow'),
    },
  })
}

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
function setZoom(factor) {
  if (!chart) return
  const current = Number(chart.getOption().geo?.[0]?.zoom) || TIE_LINE_DEFAULT_ZOOM
  const zoom = Math.min(TIE_LINE_ZOOM_LIMIT.max, Math.max(TIE_LINE_ZOOM_LIMIT.min, current * factor))
  chart.setOption({ geo: { zoom } })
}
function zoomIn() {
  setZoom(1.25)
}
function zoomOut() {
  setZoom(0.8)
}
function resetView() {
  if (!chart) return
  chart.setOption(buildOption(), true)
}
function focusListToggle() {
  nextTick(() => mapRoot.value?.querySelector('[data-action="list"]')?.focus())
}
function closeList() {
  isListOpen.value = false
  focusListToggle()
}
function toggleList() {
  isListOpen.value = !isListOpen.value
  if (!isListOpen.value) focusListToggle()
}
async function toggleFullscreen() {
  try {
    if (document.fullscreenElement === mapRoot.value) await document.exitFullscreen()
    else await mapRoot.value?.requestFullscreen?.()
  } catch (e) {
    // 浏览器权限或运行环境不支持全屏时维持实际状态，不伪造按钮状态。
  }
}
function onFullscreenChange() {
  isFullscreen.value = document.fullscreenElement === mapRoot.value
  nextTick(resize)
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
  document.addEventListener('fullscreenchange', onFullscreenChange)
  window.addEventListener('resize', resize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
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
.china-tie-line-map { position: relative; width: 100%; height: 100%; min-height: 0; background: var(--xc-map-ocean); box-shadow: inset 0 0 40px var(--xc-map-ocean-shade); }
.china-tie-line-map:fullscreen { width: 100%; height: 100%; background: var(--xc-map-ocean); box-shadow: inset 0 0 56px var(--xc-map-ocean-shade); }
.china-tie-line-map__canvas { width: 100%; height: 100%; min-height: 0; }
.china-tie-line-map__tools { position: absolute; top: var(--xc-space-4); right: var(--xc-space-4); z-index: var(--xc-z-raised); }
.china-tie-line-map__list { position: absolute; top: calc(var(--xc-space-4) + 44px); right: var(--xc-space-4); z-index: var(--xc-z-raised); }
.china-tie-line-map__note { position: absolute; left: var(--xc-space-4); bottom: var(--xc-space-4); z-index: var(--xc-z-raised); max-width: 260px; padding: var(--xc-space-2) var(--xc-space-3); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); background: var(--xc-surface-glass); box-shadow: var(--xc-shadow-sm); backdrop-filter: blur(var(--xc-blur-sm)); color: var(--xc-text-mute); font-size: var(--xc-fs-3xs); line-height: var(--xc-lh-snug); }
</style>

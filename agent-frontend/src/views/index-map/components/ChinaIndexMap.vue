<template>
  <div ref="root" class="china-index-map">
    <div ref="element" class="china-index-map__canvas" />
    <IndexMapToolbar class="china-index-map__tools" :is-fullscreen="isFullscreen" @zoom-in="zoomIn" @zoom-out="zoomOut" @reset="resetView" @toggle-fullscreen="toggleFullscreen" />
    <div class="china-index-map__legend" aria-label="指数等级图例">
      <span v-for="item in INDEX_GRADE_META" :key="item.grade"><i :style="{ background: `var(${item.token})` }" />{{ item.label }}</span>
      <span><i class="china-index-map__uncovered" />未覆盖</span>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import chinaGeo from '@/assets/geo/china.json'
import { xcVar } from '@/views/home/composables/useEcharts'
import { INDEX_GRADE_META, INDEX_MAP_DEFAULT_ZOOM, INDEX_MAP_ZOOM_LIMIT, buildIndexMapOption } from '../indexMapPresentation'
import IndexMapToolbar from './IndexMapToolbar.vue'

const props = defineProps({
  provinces: { type: Array, default: () => [] },
  selectedProvinceCode: { type: String, default: '' },
})
const emit = defineEmits(['select'])
const root = ref(null)
const element = ref(null)
const isFullscreen = ref(false)
let chart = null
let observer = null
let registered = false

// 自定义属性可能是嵌套 token（如 --xc-map-index-s: var(--xc-chart-3)），
// getComputedStyle 不会解析里层 var()，需在读色时再手动追一层，ECharts 才拿得到真实颜色值。
function resolveVar(name) {
  const raw = xcVar(name)
  const match = /^var\(\s*(--[\w-]+)\s*\)$/.exec(raw)
  return match ? resolveVar(match[1]) : raw
}
function theme() {
  return {
    tooltipBackground: resolveVar('--xc-surface-2'), tooltipBorder: resolveVar('--xc-border-soft'), tooltipText: resolveVar('--xc-text-strong'),
    boundary: resolveVar('--xc-map-boundary'), uncovered: resolveVar('--xc-surface-control'), hover: resolveVar('--xc-map-land-hover'), selected: resolveVar('--xc-accent-blue'),
    label: resolveVar('--xc-map-station'), labelActive: resolveVar('--xc-map-station'),
    gradeColors: Object.fromEntries(INDEX_GRADE_META.map((item) => [item.grade, resolveVar(item.token)])),
  }
}
function option() { return buildIndexMapOption({ provinces: props.provinces, selectedProvinceCode: props.selectedProvinceCode, theme: theme() }) }
function resize() { chart?.resize() }
function setZoom(factor) {
  if (!chart) return
  const current = Number(chart.getOption().series?.[0]?.zoom) || INDEX_MAP_DEFAULT_ZOOM
  chart.setOption({ series: [{ zoom: Math.min(INDEX_MAP_ZOOM_LIMIT.max, Math.max(INDEX_MAP_ZOOM_LIMIT.min, current * factor)) }] })
}
function zoomIn() { setZoom(1.25) }
function zoomOut() { setZoom(0.8) }
function resetView() { chart?.setOption(option(), true) }
async function toggleFullscreen() {
  if (document.fullscreenElement === root.value) await document.exitFullscreen()
  else await root.value?.requestFullscreen?.()
}
function onFullscreenChange() { isFullscreen.value = document.fullscreenElement === root.value; nextTick(resize) }
function onClick(params) {
  if (params.seriesType === 'map' && params.data?.provinceCode) emit('select', params.data.provinceCode)
}

onMounted(() => {
  if (!registered) { echarts.registerMap('china', chinaGeo); registered = true }
  chart = echarts.init(element.value, null, { renderer: 'svg' })
  chart.setOption(option())
  chart.on('click', onClick)
  observer = new ResizeObserver(resize)
  observer.observe(element.value)
  document.addEventListener('fullscreenchange', onFullscreenChange)
})
onBeforeUnmount(() => {
  observer?.disconnect()
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  chart?.off('click', onClick)
  chart?.dispose()
  chart = null
})
watch(() => [props.provinces, props.selectedProvinceCode], () => chart?.setOption(option(), true), { deep: true })
</script>

<style scoped>
.china-index-map { position: relative; width: 100%; height: 100%; min-height: 0; overflow: hidden; background: transparent; font-family: var(--xc-font-zh); }
.china-index-map:fullscreen { width: 100%; height: 100%; border: 0; border-radius: 0; }
.china-index-map__canvas { position: relative; z-index: 1; width: 100%; height: 100%; }
.china-index-map__tools { position: absolute; z-index: 3; top: 12px; right: 12px; }
.china-index-map__legend { position: absolute; z-index: 3; left: 12px; bottom: 12px; display: flex; flex-wrap: wrap; gap: 7px 12px; max-width: calc(100% - 24px); padding: 8px 10px; box-sizing: border-box; border: 1px solid var(--xc-border-soft); border-radius: 4px; background: rgba(255, 255, 255, 0.018); color: var(--xc-text-soft); font-size: 11px; }
.china-index-map__legend span { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }
.china-index-map__legend i { width: 9px; height: 9px; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 2px; }
.china-index-map__uncovered { background: var(--xc-surface-control); }
@media (max-width: 639px) { .china-index-map__tools { flex-direction: column; } .china-index-map__legend { right: 68px; max-width: none; } }
</style>

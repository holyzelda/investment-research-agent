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

function theme() {
  return {
    tooltipBackground: xcVar('--xc-surface-2'), tooltipBorder: xcVar('--xc-border-soft'), tooltipText: xcVar('--xc-text-strong'),
    boundary: xcVar('--xc-map-boundary'), uncovered: xcVar('--xc-surface-control'), hover: xcVar('--xc-map-land-hover'), selected: xcVar('--xc-accent-blue'),
    gradeColors: Object.fromEntries(INDEX_GRADE_META.map((item) => [item.grade, xcVar(item.token)])),
  }
}
function option() { return buildIndexMapOption({ provinces: props.provinces, selectedProvinceCode: props.selectedProvinceCode, theme: theme() }) }
function resize() { chart?.resize() }
function setZoom(factor) {
  if (!chart) return
  const current = Number(chart.getOption().geo?.[0]?.zoom) || INDEX_MAP_DEFAULT_ZOOM
  chart.setOption({ geo: { zoom: Math.min(INDEX_MAP_ZOOM_LIMIT.max, Math.max(INDEX_MAP_ZOOM_LIMIT.min, current * factor)) } })
}
function zoomIn() { setZoom(1.25) }
function zoomOut() { setZoom(0.8) }
function resetView() { chart?.setOption(option(), true) }
async function toggleFullscreen() {
  if (document.fullscreenElement === root.value) await document.exitFullscreen()
  else await root.value?.requestFullscreen?.()
}
function onFullscreenChange() { isFullscreen.value = document.fullscreenElement === root.value; nextTick(resize) }
function onClick(params) { if (params.seriesType === 'map' && params.data?.provinceCode) emit('select', params.data.provinceCode) }

onMounted(() => {
  if (!registered) { echarts.registerMap('china', chinaGeo); registered = true }
  chart = echarts.init(element.value)
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
.china-index-map { position: relative; width: 100%; height: 100%; min-height: 460px; background: var(--xc-surface-card); border: 1px solid var(--xc-border-card); border-radius: var(--xc-radius-lg); overflow: hidden; }
.china-index-map:fullscreen { width: 100%; height: 100%; border: 0; border-radius: 0; }
.china-index-map__canvas { width: 100%; height: 100%; }
.china-index-map__tools { position: absolute; top: var(--xc-space-4); right: var(--xc-space-4); }
.china-index-map__legend { position: absolute; left: var(--xc-space-4); bottom: var(--xc-space-4); display: grid; gap: var(--xc-space-2); padding: var(--xc-space-3); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); background: var(--xc-surface-raised); color: var(--xc-text-soft); font-size: var(--xc-fs-2xs); }
.china-index-map__legend span { display: inline-flex; align-items: center; gap: var(--xc-space-2); }
.china-index-map__legend i { width: 10px; height: 10px; border-radius: 50%; }
.china-index-map__uncovered { background: var(--xc-surface-control); }
</style>

<template>
  <div class="index-map-tools" role="toolbar" aria-label="地图工具">
    <button class="xc-btn xc-btn--icon" type="button" aria-label="放大地图" title="放大" @click="$emit('zoom-in')"><ZoomIn :size="17" aria-hidden="true" /></button>
    <button class="xc-btn xc-btn--icon" type="button" aria-label="缩小地图" title="缩小" @click="$emit('zoom-out')"><ZoomOut :size="17" aria-hidden="true" /></button>
    <button class="xc-btn xc-btn--icon" type="button" aria-label="复位全国视图" title="复位全国" @click="$emit('reset')"><LocateFixed :size="17" aria-hidden="true" /></button>
    <button class="xc-btn xc-btn--icon" type="button" :aria-label="isFullscreen ? '退出全屏地图' : '全屏地图'" :title="isFullscreen ? '退出全屏' : '全屏地图'" :aria-pressed="isFullscreen" @click="$emit('toggle-fullscreen')"><Minimize2 v-if="isFullscreen" :size="17" aria-hidden="true" /><Maximize2 v-else :size="17" aria-hidden="true" /></button>
  </div>
</template>

<script setup>
import { LocateFixed, Maximize2, Minimize2, ZoomIn, ZoomOut } from '@lucide/vue'
defineProps({ isFullscreen: { type: Boolean, default: false } })
defineEmits(['zoom-in', 'zoom-out', 'reset', 'toggle-fullscreen'])
</script>

<style scoped>
.index-map-tools { display: inline-flex; gap: 6px; }
.index-map-tools .xc-btn { display: inline-grid; width: 44px; height: 44px; place-items: center; padding: 0; border: 1px solid var(--xc-border-soft); border-radius: 4px; background: #283034; color: var(--xc-text-soft); transition: border-color var(--xc-dur-fast) var(--xc-ease-out), background var(--xc-dur-fast) var(--xc-ease-out), color var(--xc-dur-fast) var(--xc-ease-out); }
.index-map-tools .xc-btn:hover { border-color: var(--xc-accent-blue); background: #323b3f; color: var(--xc-text-strong); }
.index-map-tools .xc-btn:focus-visible { outline: 2px solid var(--xc-accent-blue); outline-offset: 2px; }
</style>

<template>
  <div class="index-map-tools" role="toolbar" aria-label="地图工具">
    <button class="xc-btn xc-btn--icon" type="button" aria-label="放大地图" @click="$emit('zoom-in')">＋</button>
    <button class="xc-btn xc-btn--icon" type="button" aria-label="缩小地图" @click="$emit('zoom-out')">－</button>
    <button class="xc-btn xc-btn--icon" type="button" aria-label="复位全国视图" @click="$emit('reset')">⌖</button>
    <button class="xc-btn xc-btn--icon" type="button" :aria-label="isFullscreen ? '退出全屏地图' : '全屏地图'" @click="$emit('toggle-fullscreen')">⛶</button>
  </div>
</template>

<script setup>
defineProps({ isFullscreen: { type: Boolean, default: false } })
defineEmits(['zoom-in', 'zoom-out', 'reset', 'toggle-fullscreen'])
</script>

<style scoped>
.index-map-tools { display: inline-flex; gap: var(--xc-space-2); padding: 0; border: 0; background: transparent; box-shadow: none; backdrop-filter: none; }
.index-map-tools .xc-btn { border: 1px solid var(--xc-border-soft); background: rgba(255, 255, 255, 0.08); color: var(--xc-text-strong); transition: border-color var(--xc-dur-base) var(--xc-ease-out), background var(--xc-dur-base) var(--xc-ease-out); }
.index-map-tools .xc-btn:hover { border-color: rgba(34, 177, 253, 0.68); background: rgba(34, 177, 253, 0.18); }
</style>

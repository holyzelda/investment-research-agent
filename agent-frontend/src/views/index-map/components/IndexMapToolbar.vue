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
.index-map-tools { display: inline-flex; gap: var(--xc-space-2); }
.index-map-tools .xc-btn { border: 1px solid var(--xc-border-soft); background: var(--xc-surface-raised); color: var(--xc-text-strong); }
</style>

<template>
  <div class="tl-map-tools" role="toolbar" aria-label="地图工具">
    <button class="xc-btn xc-btn--icon" type="button" data-action="zoom-in" aria-label="放大地图" title="放大" @click="$emit('zoom-in')">
      <ZoomIn :size="16" aria-hidden="true" />
    </button>
    <button class="xc-btn xc-btn--icon" type="button" data-action="zoom-out" aria-label="缩小地图" title="缩小" @click="$emit('zoom-out')">
      <ZoomOut :size="16" aria-hidden="true" />
    </button>
    <button class="xc-btn xc-btn--icon" type="button" data-action="reset" aria-label="复位全国视图" title="复位全国" @click="$emit('reset')">
      <LocateFixed :size="16" aria-hidden="true" />
    </button>
    <button
      class="xc-btn xc-btn--icon"
      type="button"
      data-action="fullscreen"
      :aria-label="isFullscreen ? '退出全屏地图' : '全屏地图'"
      :title="isFullscreen ? '退出全屏' : '全屏地图'"
      :aria-pressed="isFullscreen"
      @click="$emit('toggle-fullscreen')"
    >
      <Minimize2 v-if="isFullscreen" :size="16" aria-hidden="true" />
      <Maximize2 v-else :size="16" aria-hidden="true" />
    </button>
    <button
      class="xc-btn xc-btn--icon"
      type="button"
      data-action="list"
      aria-label="线路列表"
      title="线路列表"
      :aria-pressed="isListOpen"
      :class="{ 'is-active': isListOpen }"
      @click="$emit('toggle-list')"
    >
      <List :size="16" aria-hidden="true" />
    </button>
  </div>
</template>

<script setup>
import { List, LocateFixed, Maximize2, Minimize2, ZoomIn, ZoomOut } from '@lucide/vue'

defineProps({
  isFullscreen: { type: Boolean, default: false },
  isListOpen: { type: Boolean, default: false },
})
defineEmits(['zoom-in', 'zoom-out', 'reset', 'toggle-fullscreen', 'toggle-list'])
</script>

<style scoped>
.tl-map-tools {
  display: inline-flex;
  gap: var(--xc-space-2);
}
.tl-map-tools .xc-btn--icon {
  border: 1px solid rgba(9, 24, 43, 0.16);
  border-radius: var(--xc-radius-sm);
  background: rgba(245, 239, 220, 0.88);
  box-shadow: 0 8px 22px rgba(9, 24, 43, 0.22);
  backdrop-filter: blur(var(--xc-blur-lg));
  color: var(--xc-map-ocean);
}
.tl-map-tools .xc-btn--icon:hover,
.tl-map-tools .xc-btn--icon.is-active {
  color: var(--xc-map-ocean);
  background: rgba(255, 247, 223, 0.94);
  border-color: rgba(9, 24, 43, 0.24);
}
.tl-map-tools .xc-btn--icon:focus-visible {
  outline: 2px solid var(--xc-accent-blue);
  outline-offset: -2px;
}
</style>

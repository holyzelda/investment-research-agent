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
  overflow: hidden;
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-md);
  background: var(--xc-surface-glass);
  box-shadow: var(--xc-shadow-glass);
  backdrop-filter: blur(var(--xc-blur-lg));
}
.tl-map-tools .xc-btn--icon {
  border: 0;
  border-right: 1px solid var(--xc-border-soft);
  border-radius: 0;
  color: var(--xc-text-soft);
}
.tl-map-tools .xc-btn--icon:last-child { border-right: 0; }
.tl-map-tools .xc-btn--icon:hover,
.tl-map-tools .xc-btn--icon.is-active {
  color: var(--xc-text-strong);
  background: var(--xc-accent-blue-soft);
}
.tl-map-tools .xc-btn--icon:focus-visible {
  outline: 2px solid var(--xc-border-accent);
  outline-offset: -2px;
}
</style>

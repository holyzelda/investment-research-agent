<template>
  <div class="tl-map-tools" role="toolbar" aria-label="地图工具">
    <button type="button" data-action="zoom-in" aria-label="放大地图" title="放大" @click="$emit('zoom-in')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="11" cy="11" r="6" /><path d="M11 8v6M8 11h6M16 16l4 4" stroke-linecap="round" /></svg>
    </button>
    <button type="button" data-action="zoom-out" aria-label="缩小地图" title="缩小" @click="$emit('zoom-out')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="11" cy="11" r="6" /><path d="M8 11h6M16 16l4 4" stroke-linecap="round" /></svg>
    </button>
    <button type="button" data-action="reset" aria-label="复位全国视图" title="复位全国" @click="$emit('reset')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M4 12a8 8 0 1 0 2.3-5.65" stroke-linecap="round" /><path d="M4 4v4h4" stroke-linecap="round" stroke-linejoin="round" /></svg>
    </button>
    <button
      type="button"
      data-action="fullscreen"
      :aria-label="isFullscreen ? '退出全屏地图' : '全屏地图'"
      :title="isFullscreen ? '退出全屏' : '全屏地图'"
      :aria-pressed="isFullscreen"
      @click="$emit('toggle-fullscreen')"
    >
      <svg v-if="!isFullscreen" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M8 4H4v4M16 4h4v4M20 16v4h-4M4 16v4h4" stroke-linecap="round" stroke-linejoin="round" /></svg>
      <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M9 4v5H4M15 4v5h5M20 15h-5v5M4 15h5v5" stroke-linecap="round" stroke-linejoin="round" /></svg>
    </button>
    <button
      ref="listButton"
      type="button"
      data-action="list"
      aria-label="线路列表"
      title="线路列表"
      :aria-pressed="isListOpen"
      :class="{ 'is-active': isListOpen }"
      @click="$emit('toggle-list')"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M9 6h11M9 12h11M9 18h11" stroke-linecap="round" /><circle cx="4" cy="6" r="1" fill="currentColor" /><circle cx="4" cy="12" r="1" fill="currentColor" /><circle cx="4" cy="18" r="1" fill="currentColor" /></svg>
    </button>
  </div>
</template>

<script setup>
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
  border: 1px solid var(--xc-map-legend-border);
  border-radius: var(--xc-radius-sm, 8px);
  background: var(--xc-map-legend-bg);
  box-shadow: var(--xc-shadow-sm);
}
.tl-map-tools button {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border: 0;
  border-right: 1px solid var(--xc-map-legend-border);
  background: transparent;
  color: var(--xc-text-soft);
  cursor: pointer;
}
.tl-map-tools button:last-child { border-right: 0; }
.tl-map-tools button:hover,
.tl-map-tools button.is-active { background: var(--xc-surface-frosted); color: var(--xc-text-strong); }
.tl-map-tools button:focus-visible { outline: 2px solid var(--xc-accent-blue); outline-offset: -2px; }
.tl-map-tools svg { width: 18px; height: 18px; }
</style>

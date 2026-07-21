<template>
  <div class="tl-filter">
    <label class="tl-filter__field">
      <span class="tl-filter__label">起点区域</span>
      <select class="xc-select tl-filter__select" :value="startRegion" @change="$emit('update:start-region', $event.target.value)">
        <option value="">全部</option>
        <option v-for="r in regionOptions" :key="r" :value="r">{{ r }}</option>
      </select>
    </label>
    <button class="xc-btn xc-btn--icon tl-filter__swap" type="button" aria-label="交换起点和终点区域" title="交换起终点" @click="$emit('swap-regions')">
      <ArrowLeftRight :size="16" aria-hidden="true" />
    </button>
    <label class="tl-filter__field">
      <span class="tl-filter__label">终点区域</span>
      <select class="tl-filter__select" :value="endRegion" @change="$emit('update:end-region', $event.target.value)">
        <option value="">全部</option>
        <option v-for="r in regionOptions" :key="r" :value="r">{{ r }}</option>
      </select>
    </label>
    <label class="tl-filter__field">
      <span class="tl-filter__label">额定容量</span>
      <span class="tl-filter__capacity xc-num">
        <input class="xc-input tl-filter__input" type="number" min="0" step="1" inputmode="numeric" aria-label="额定容量下限（MW）" placeholder="最小" :value="minCapacityMw ?? ''" @change="$emit('update:min-capacity-mw', $event.target.value)" />
        <span>—</span>
        <input class="xc-input tl-filter__input" type="number" min="0" step="1" inputmode="numeric" aria-label="额定容量上限（MW）" placeholder="最大" :value="maxCapacityMw ?? ''" @change="$emit('update:max-capacity-mw', $event.target.value)" />
        <span>MW</span>
      </span>
    </label>
    <button class="xc-btn xc-btn--ghost tl-filter__reset" type="button" @click="$emit('reset-filters')">
      <RotateCcw :size="14" aria-hidden="true" />
      <span>重置筛选</span>
    </button>
  </div>
</template>

<script setup>
import { ArrowLeftRight, RotateCcw } from '@lucide/vue'

defineProps({
  startRegion: { type: String, default: '' },
  endRegion: { type: String, default: '' },
  minCapacityMw: { type: Number, default: null },
  maxCapacityMw: { type: Number, default: null },
  regionOptions: { type: Array, default: () => [] },
})
defineEmits(['update:start-region', 'update:end-region', 'update:min-capacity-mw', 'update:max-capacity-mw', 'swap-regions', 'reset-filters'])
</script>

<style scoped>
.tl-filter {
  display: flex;
  align-items: center;
  gap: var(--xc-space-3);
  min-height: 44px;
  padding: 0 var(--xc-space-4);
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-md);
  background: var(--xc-surface-1);
  box-sizing: border-box;
}
.tl-filter__field { display: inline-flex; align-items: center; gap: var(--xc-space-2); }
.tl-filter__label { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); white-space: nowrap; }
.tl-filter__select,
.tl-filter__input { min-height: 28px; box-sizing: border-box; }
.tl-filter__capacity { display: inline-flex; align-items: center; gap: var(--xc-space-1); color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.tl-filter__input { width: 72px; }
.tl-filter__swap { flex: 0 0 auto; }
.tl-filter__reset { margin-left: auto; }
.tl-filter__select:focus-visible,
.tl-filter__input:focus-visible,
.tl-filter__swap:focus-visible,
.tl-filter__reset:focus-visible { outline: 2px solid var(--xc-border-accent); outline-offset: 2px; }
</style>

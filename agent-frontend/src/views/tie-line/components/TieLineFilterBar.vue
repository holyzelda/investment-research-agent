<template>
  <div class="tl-filter">
    <label class="tl-filter__field">
      <span class="tl-filter__label">起点区域</span>
      <select class="tl-filter__select" :value="startRegion" @change="$emit('update:start-region', $event.target.value)">
        <option value="">全部</option>
        <option v-for="r in regionOptions" :key="r" :value="r">{{ r }}</option>
      </select>
    </label>
    <button class="tl-filter__swap" type="button" aria-label="交换起点和终点区域" title="交换起终点" @click="$emit('swap-regions')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M7 7h11l-3-3M17 17H6l3 3" stroke-linecap="round" stroke-linejoin="round" /></svg>
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
      <span class="tl-filter__capacity">
        <input class="tl-filter__input" type="number" min="0" step="1" inputmode="numeric" aria-label="额定容量下限（MW）" placeholder="最小" :value="minCapacityMw ?? ''" @change="$emit('update:min-capacity-mw', $event.target.value)" />
        <span>—</span>
        <input class="tl-filter__input" type="number" min="0" step="1" inputmode="numeric" aria-label="额定容量上限（MW）" placeholder="最大" :value="maxCapacityMw ?? ''" @change="$emit('update:max-capacity-mw', $event.target.value)" />
        <span>MW</span>
      </span>
    </label>
    <button class="tl-filter__reset" type="button" @click="$emit('reset-filters')">重置筛选</button>
  </div>
</template>

<script setup>
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
.tl-filter { display: flex; align-items: center; gap: var(--xc-space-3, 12px); flex-wrap: wrap; }
.tl-filter__field { display: inline-flex; align-items: center; gap: var(--xc-space-2, 8px); }
.tl-filter__label { font-size: var(--xc-fs-2xs, 12px); color: var(--xc-text-mute); }
.tl-filter__select, .tl-filter__input { background: var(--xc-surface-2); color: var(--xc-text-strong); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm, 6px); padding: 4px 10px; font-size: var(--xc-fs-xs, 13px); outline: none; }
.tl-filter__select:focus-visible, .tl-filter__input:focus-visible, .tl-filter__swap:focus-visible, .tl-filter__reset:focus-visible { outline: 2px solid var(--xc-accent-blue); outline-offset: 2px; }
.tl-filter__capacity { display: inline-flex; align-items: center; gap: 5px; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs, 12px); }
.tl-filter__input { width: 70px; }
.tl-filter__swap, .tl-filter__reset { border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm, 6px); background: var(--xc-surface-2); color: var(--xc-text-soft); cursor: pointer; }
.tl-filter__swap { width: 30px; height: 30px; display: grid; place-items: center; padding: 0; }
.tl-filter__swap svg { width: 17px; height: 17px; }
.tl-filter__reset { padding: 5px 10px; font-size: var(--xc-fs-xs, 13px); }
.tl-filter__swap:hover, .tl-filter__reset:hover { color: var(--xc-text-strong); border-color: var(--xc-border-accent); }
</style>

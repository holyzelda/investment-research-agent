<template>
  <div class="tl-filter">
    <!-- 起点 / 终点区域筛选（真实可用） -->
    <label class="tl-filter__field">
      <span class="tl-filter__label">起点区域</span>
      <select
        class="tl-filter__select"
        :value="startRegion"
        @change="$emit('update:start-region', $event.target.value)"
      >
        <option value="">全部</option>
        <option v-for="r in regionOptions" :key="r" :value="r">{{ r }}</option>
      </select>
    </label>
    <label class="tl-filter__field">
      <span class="tl-filter__label">终点区域</span>
      <select
        class="tl-filter__select"
        :value="endRegion"
        @change="$emit('update:end-region', $event.target.value)"
      >
        <option value="">全部</option>
        <option v-for="r in regionOptions" :key="r" :value="r">{{ r }}</option>
      </select>
    </label>
  </div>
</template>

<script setup>
defineProps({
  startRegion: { type: String, default: '' },
  endRegion: { type: String, default: '' },
  regionOptions: { type: Array, default: () => [] },
})
defineEmits(['update:start-region', 'update:end-region'])
</script>

<style scoped>
.tl-filter {
  display: flex;
  align-items: center;
  gap: var(--xc-space-4, 16px);
  flex-wrap: wrap;
}
.tl-filter__field {
  display: inline-flex;
  align-items: center;
  gap: var(--xc-space-2, 8px);
}
.tl-filter__label {
  font-size: var(--xc-fs-2xs, 12px);
  color: var(--xc-text-mute);
}
.tl-filter__select {
  background: var(--xc-surface-2);
  color: var(--xc-text-strong);
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-sm, 6px);
  padding: 4px 10px;
  font-size: var(--xc-fs-xs, 13px);
  outline: none;
}
.tl-filter__select:focus-visible {
  border-color: var(--xc-accent-blue);
}
</style>

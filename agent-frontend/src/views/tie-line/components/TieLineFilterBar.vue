<template>
  <div class="tl-filter">
    <!-- 电压 / 区域筛选（真实可用） -->
    <label class="tl-filter__field">
      <span class="tl-filter__label">电压</span>
      <select
        class="tl-filter__select"
        :value="voltage"
        @change="$emit('update:voltage', $event.target.value)"
      >
        <option value="">全部</option>
        <option v-for="v in voltageOptions" :key="v" :value="v">{{ v }}</option>
      </select>
    </label>
    <label class="tl-filter__field">
      <span class="tl-filter__label">区域</span>
      <select
        class="tl-filter__select"
        :value="region"
        @change="$emit('update:region', $event.target.value)"
      >
        <option value="">全部</option>
        <option v-for="r in regionOptions" :key="r" :value="r">{{ r }}</option>
      </select>
    </label>

    <!-- 时间范围切换：依赖功率时序数据，首版禁用占位 -->
    <div class="tl-filter__ranges" aria-hidden="true">
      <span
        v-for="r in rangePlaceholder"
        :key="r"
        class="tl-filter__range is-disabled"
        :class="{ 'is-active': r === '30日' }"
        title="功率时序数据接入后可用"
      >{{ r }}</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  voltage: { type: String, default: '' },
  region: { type: String, default: '' },
  voltageOptions: { type: Array, default: () => [] },
  regionOptions: { type: Array, default: () => [] },
})
defineEmits(['update:voltage', 'update:region'])

// 时间范围仅占位（灰显不可点），对齐原型但当前无时序数据源
const rangePlaceholder = ['昨日', '7日', '30日', '90日', '自定义']
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
.tl-filter__ranges {
  display: inline-flex;
  gap: 4px;
  margin-left: auto;
}
.tl-filter__range {
  font-size: var(--xc-fs-2xs, 12px);
  padding: 3px 10px;
  border-radius: var(--xc-radius-sm, 6px);
  color: var(--xc-text-mute);
}
.tl-filter__range.is-disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.tl-filter__range.is-active {
  background: var(--xc-surface-2);
  color: var(--xc-text-soft);
}
</style>

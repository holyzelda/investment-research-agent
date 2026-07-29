<template>
  <el-select class="index-period-select" :model-value="modelValue" :loading="loading" :disabled="loading || !periods.length" placeholder="选择期次" aria-label="指数期次" @update:model-value="$emit('update:modelValue', $event)">
    <el-option v-for="item in periods" :key="item.period" :label="item.label" :value="item.period" />
  </el-select>
</template>
<script setup>
defineProps({ periods: { type: Array, default: () => [] }, modelValue: { type: String, default: '' }, loading: Boolean })
defineEmits(['update:modelValue'])
</script>
<style scoped>
.index-period-select { width: 100%; }
.index-period-select :deep(.el-select__wrapper) { min-height: 36px; border: 1px solid var(--xc-border-soft); border-radius: 4px; background: #283034; box-shadow: none; }
.index-period-select :deep(.el-select__wrapper.is-focused) { border-color: var(--xc-accent-blue); box-shadow: 0 0 0 1px var(--xc-accent-blue); }
.index-period-select :deep(.el-select__selected-item), .index-period-select :deep(.el-select__placeholder) { color: var(--xc-text-soft); font-size: 12px; }
</style>

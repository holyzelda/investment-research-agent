<template>
  <el-select :model-value="modelValue" :loading="loading" placeholder="选择期次" @update:model-value="$emit('update:modelValue', $event)">
    <el-option v-for="item in periods" :key="item.period" :label="item.label" :value="item.period" />
  </el-select>
</template>
<script setup>
defineProps({ periods: { type: Array, default: () => [] }, modelValue: { type: String, default: '' }, loading: Boolean })
defineEmits(['update:modelValue'])
</script>

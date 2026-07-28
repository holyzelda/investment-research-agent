<template>
  <section class="index-ranking">
    <h3>{{ title }}</h3>
    <button v-for="item in items.slice(0, 5)" :key="item.provinceCode" :class="{ 'is-active': item.provinceCode === selectedProvinceCode }" type="button" @click="$emit('select', item.provinceCode)">
      <span>{{ item.rank }} · {{ item.provinceName }}</span><strong class="xc-num">{{ formatNumber(item[valueKey]) }}{{ suffix }}</strong>
    </button>
  </section>
</template>
<script setup>
import { formatNumber } from '@/utils/formatNumber'
defineProps({ title: String, items: { type: Array, default: () => [] }, valueKey: String, suffix: { type: String, default: '' }, selectedProvinceCode: String })
defineEmits(['select'])
</script>
<style scoped>
.index-ranking { display: grid; gap: var(--xc-space-2); padding: var(--xc-space-4); border: 1px solid var(--xc-border-card); border-radius: var(--xc-radius-md); background: var(--xc-surface-card); }
h3 { margin: 0; color: var(--xc-text-strong); font-size: var(--xc-fs-sm); }
button { display: flex; justify-content: space-between; padding: var(--xc-space-2) var(--xc-space-3); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); background: transparent; color: var(--xc-text-soft); cursor: pointer; text-align: left; }
button.is-active, button:hover { border-color: var(--xc-accent-blue); color: var(--xc-text-strong); }
</style>

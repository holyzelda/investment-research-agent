<template>
  <section class="index-ranking">
    <h3>{{ title }}</h3>
    <button v-for="item in items.slice(0, 5)" :key="item.provinceCode" :class="{ 'is-active': item.provinceCode === selectedProvinceCode }" type="button" @click="$emit('select', item.provinceCode)">
      <span>{{ item.rank }} · {{ item.provinceName }}</span><strong v-if="valueKey" class="xc-num">{{ formatNumber(item[valueKey]) }}{{ suffix }}</strong>
    </button>
  </section>
</template>
<script setup>
import { formatNumber } from '@/utils/formatNumber'
defineProps({ title: String, items: { type: Array, default: () => [] }, valueKey: String, suffix: { type: String, default: '' }, selectedProvinceCode: String })
defineEmits(['select'])
</script>
<style scoped>
.index-ranking { display: grid; grid-template-columns: 1fr; gap: 3px; padding: var(--xc-space-2); border: 1px solid rgba(120, 198, 255, 0.18); border-radius: var(--xc-radius-md); background: linear-gradient(145deg, rgba(255, 255, 255, 0.078), rgba(255, 255, 255, 0.032)); box-shadow: var(--xc-shadow-md); }
h3 { margin: 0 0 1px; color: var(--xc-text-strong); font-size: var(--xc-fs-xs); line-height: var(--xc-lh-tight); }
button { display: flex; align-items: center; justify-content: space-between; gap: var(--xc-space-2); min-width: 0; min-height: 22px; padding: 2px var(--xc-space-2); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); background: rgba(255, 255, 255, 0.035); color: var(--xc-text-soft); font-size: var(--xc-fs-2xs); cursor: pointer; text-align: left; transition: border-color var(--xc-dur-base) var(--xc-ease-out), background var(--xc-dur-base) var(--xc-ease-out), transform var(--xc-dur-base) var(--xc-ease-out); }
button span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
button strong { color: var(--xc-text-strong); }
button.is-active, button:hover { border-color: rgba(34, 177, 253, 0.72); background: linear-gradient(90deg, rgba(34, 177, 253, 0.2), rgba(255, 170, 0, 0.08)); color: var(--xc-text-strong); transform: translateX(2px); }
@media (max-width: 900px) { .index-ranking { gap: 2px; padding: 4px 5px; }.index-ranking button { min-height: 20px; padding: 1px 5px; } }
</style>

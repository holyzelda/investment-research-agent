<template>
  <section class="index-ranking">
    <h3>{{ title }}</h3>
    <div v-if="!items.length" class="index-ranking__empty">暂无排行数据</div>
    <button v-for="item in items.slice(0, 5)" v-else :key="item.provinceCode" :class="{ 'is-active': item.provinceCode === selectedProvinceCode }" :aria-pressed="item.provinceCode === selectedProvinceCode" type="button" @click="$emit('select', item.provinceCode)">
      <span class="index-ranking__rank xc-num">{{ item.rank }}</span><span class="index-ranking__name">{{ item.provinceName }}</span><strong v-if="valueKey" class="xc-num">{{ formatNumber(item[valueKey]) }}{{ suffix }}</strong>
    </button>
  </section>
</template>
<script setup>
import { formatNumber } from '@/utils/formatNumber'
defineProps({ title: String, items: { type: Array, default: () => [] }, valueKey: String, suffix: { type: String, default: '' }, selectedProvinceCode: String })
defineEmits(['select'])
</script>
<style scoped>
.index-ranking { display: grid; grid-template-columns: 1fr; align-content: start; min-width: 0; padding: 8px 10px 9px; }
h3 { margin: 0; padding: 2px 4px 7px; color: var(--xc-text-strong); font-size: 12px; font-weight: 600; line-height: 1.2; }
button { position: relative; display: grid; grid-template-columns: 24px minmax(0, 1fr) auto; align-items: center; gap: 7px; min-width: 0; min-height: 28px; padding: 3px 6px; border: 0; border-top: 1px solid rgba(255, 255, 255, 0.065); background: transparent; color: var(--xc-text-soft); font-size: 11px; cursor: pointer; text-align: left; transition: background var(--xc-dur-fast) var(--xc-ease-out), color var(--xc-dur-fast) var(--xc-ease-out); }
button::before { content: ''; position: absolute; inset: 4px auto 4px 0; width: 2px; background: transparent; }
button:hover, button.is-active { background: rgba(84, 198, 214, 0.09); color: var(--xc-text-strong); }
button.is-active::before { background: var(--xc-accent-blue); }
button:focus-visible { outline: 2px solid var(--xc-accent-blue); outline-offset: -2px; }
.index-ranking__rank { color: var(--xc-text-mute); text-align: center; }
.index-ranking__name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
button strong { color: var(--xc-text-strong); font-size: 11px; }
.index-ranking__empty { display: grid; min-height: 84px; place-items: center; color: var(--xc-text-mute); font-size: 11px; }
</style>

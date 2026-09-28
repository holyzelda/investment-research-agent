<template>
  <section class="index-ranking">
    <h3>
      <Flame v-if="title === '投资热力榜'" aria-hidden="true" />
      <ShieldCheck v-else aria-hidden="true" />
      <span>{{ title }}</span>
    </h3>
    <div v-if="!items.length" class="index-ranking__empty">暂无排行数据</div>
    <button v-for="item in items.slice(0, 5)" v-else :key="item.provinceCode" :class="{ 'is-active': item.provinceCode === selectedProvinceCode }" :aria-pressed="item.provinceCode === selectedProvinceCode" type="button" @click="$emit('select', item.provinceCode)">
      <span :class="['index-ranking__rank', 'xc-num', `is-rank-${item.rank}`]">{{ item.rank }}</span><span class="index-ranking__name">{{ item.provinceName }}</span><strong v-if="valueKey" class="xc-num">{{ formatNumber(item[valueKey]) }}{{ suffix }}</strong>
    </button>
  </section>
</template>
<script setup>
import { Flame, ShieldCheck } from '@lucide/vue'
import { formatNumber } from '@/utils/formatNumber'
defineProps({ title: String, items: { type: Array, default: () => [] }, valueKey: String, suffix: { type: String, default: '' }, selectedProvinceCode: String })
defineEmits(['select'])
</script>
<style scoped>
.index-ranking { display: grid; grid-template-columns: 1fr; align-content: start; min-width: 0; padding: 9px 14px 10px; }
h3 { display: flex; align-items: center; gap: 7px; margin: 0; padding: 2px 6px 7px; color: var(--xc-text-strong); font-size: 16px; font-weight: 600; line-height: 1.2; }
h3 svg { width: 16px; height: 16px; color: var(--xc-accent-blue); stroke-width: 2; }
button { position: relative; display: grid; grid-template-columns: 20px minmax(0, 1fr) auto; align-items: center; gap: 11px; min-width: 0; min-height: 32px; padding: 6px 11px; border: 0; border-top: 1px solid rgba(255, 255, 255, 0.065); border-radius: 10px; background: transparent; color: var(--xc-text-soft); font-size: 13px; cursor: pointer; text-align: left; transition: background var(--xc-dur-fast) var(--xc-ease-out), color var(--xc-dur-fast) var(--xc-ease-out); }
button::before { content: ''; position: absolute; inset: 5px auto 5px 0; width: 2px; background: transparent; }
button:hover { background: var(--xc-surface-control); color: var(--xc-text-strong); }
button.is-active { background: var(--xc-surface-control); color: var(--xc-text-strong); }
button.is-active::before { background: var(--xc-accent-blue); }
button:focus-visible { outline: 2px solid var(--xc-accent-blue); outline-offset: -2px; }
.index-ranking__rank { display: grid; width: 20px; height: 20px; place-items: center; border: 1px solid transparent; border-radius: 5px; background: rgba(255, 255, 255, 0.045); color: var(--xc-text-mute); font-size: 11px; font-weight: 700; text-align: center; }
.index-ranking__rank.is-rank-1 { border-color: rgba(243, 198, 111, 0.34); background: rgba(243, 166, 74, 0.18); color: #f3c66f; }
.index-ranking__rank.is-rank-2 { border-color: rgba(84, 198, 214, 0.32); background: rgba(84, 198, 214, 0.16); color: #79dbe3; }
.index-ranking__rank.is-rank-3 { border-color: rgba(167, 139, 250, 0.32); background: rgba(139, 92, 246, 0.17); color: #b8a4ff; }
.index-ranking__name { overflow: hidden; color: var(--xc-text-strong); font-size: 13px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
button strong { color: var(--xc-text-strong); font-size: 14px; font-weight: 700; }
.index-ranking__empty { display: grid; min-height: 100px; place-items: center; color: var(--xc-text-mute); font-size: 12px; }
</style>

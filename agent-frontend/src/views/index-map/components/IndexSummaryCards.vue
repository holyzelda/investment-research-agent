<template>
  <section class="index-summary-cards" aria-label="全国指数摘要">
    <article><span>全国均值</span><strong class="xc-num">{{ formatNumber(summary?.nationalAverage) }}</strong><em>分</em></article>
    <article><span>领跑省份</span><strong>{{ summary?.leader?.provinceName || '—' }}</strong><em class="xc-num">{{ formatNumber(summary?.leader?.indexScore) }} 分</em></article>
    <article><span>已开通区域</span><strong class="xc-num">{{ summary?.openedProvinceCount ?? '—' }}</strong><em>省 · S {{ summary?.openedGradeCounts?.S ?? 0 }} / A {{ summary?.openedGradeCounts?.A ?? 0 }} / B {{ summary?.openedGradeCounts?.B ?? 0 }} / C {{ summary?.openedGradeCounts?.C ?? 0 }}</em></article>
    <article><span>高潜待挖掘</span><strong class="xc-num">{{ 6 }}</strong><em>省 · 机制培育中</em></article>
  </section>
</template>
<script setup>
import { formatNumber } from '@/utils/formatNumber'
defineProps({ summary: { type: Object, default: null } })
</script>
<style scoped>
.index-summary-cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; min-height: 0; }
article { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-content: center; align-items: baseline; gap: 3px 8px; min-width: 0; min-height: 60px; padding: 7px 14px; box-sizing: border-box; border: 1px solid var(--xc-border-soft); border-radius: 12px; background: var(--xc-surface-raised); overflow: hidden; }
article > span { grid-column: 1 / -1; }
span, em { overflow: hidden; color: var(--xc-text-mute); font-size: 12px; font-style: normal; line-height: 1.35; text-overflow: ellipsis; white-space: nowrap; }
strong { overflow: hidden; color: var(--xc-text-strong); font-size: 19px; font-weight: 700; line-height: 1.15; text-overflow: ellipsis; white-space: nowrap; }
em { justify-self: end; }
@media (max-width: 1180px) { article { padding-inline: 16px 12px; } }
@media (max-width: 639px) { .index-summary-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>

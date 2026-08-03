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
.index-summary-cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); min-height: 64px; border: 1px solid var(--xc-border-soft); border-radius: 8px; background: rgba(40, 48, 52, 0.72); overflow: hidden; }
article { display: grid; grid-template-columns: auto 1fr auto; align-content: center; align-items: baseline; gap: 6px; min-width: 0; padding: 10px 12px; }
article + article { border-left: 1px solid var(--xc-border-soft); }
span, em { overflow: hidden; color: var(--xc-text-mute); font-size: 11px; font-style: normal; text-overflow: ellipsis; white-space: nowrap; }
strong { overflow: hidden; color: var(--xc-text-strong); font-size: 18px; font-weight: 600; line-height: 1.2; text-overflow: ellipsis; white-space: nowrap; }
em { justify-self: end; }
@media (max-width: 1180px) { article { grid-template-columns: 1fr auto; } article span { grid-column: 1 / -1; } }
@media (max-width: 639px) { .index-summary-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); } article:nth-child(3) { border-left: 0; } article:nth-child(n + 3) { border-top: 1px solid var(--xc-border-soft); } }
</style>

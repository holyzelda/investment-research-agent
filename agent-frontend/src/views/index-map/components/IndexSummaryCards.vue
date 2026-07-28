<template>
  <div class="index-summary-cards">
    <article class="index-summary-card"><span>全国均值</span><strong class="xc-num">{{ formatNumber(summary?.nationalAverage) }}分</strong></article>
    <article class="index-summary-card"><span>领跑省份</span><strong>{{ summary?.leader?.provinceName || '—' }}</strong><em class="xc-num">{{ formatNumber(summary?.leader?.indexScore) }}分</em></article>
    <article class="index-summary-card"><span>已开通区域</span><strong class="xc-num">{{ summary?.openedProvinceCount ?? '—' }}省</strong><em>S {{ summary?.openedGradeCounts?.S ?? 0 }} · A {{ summary?.openedGradeCounts?.A ?? 0 }} · B {{ summary?.openedGradeCounts?.B ?? 0 }}</em></article>
    <article class="index-summary-card"><span>高潜待挖掘</span><strong class="xc-num">{{ summary?.highPotentialCount ?? '—' }}省</strong><em>C 类待开通</em></article>
  </div>
</template>
<script setup>
import { formatNumber } from '@/utils/formatNumber'
defineProps({ summary: { type: Object, default: null } })
</script>
<style scoped>
.index-summary-cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--xc-space-3); }
.index-summary-card { display: grid; gap: var(--xc-space-1); padding: var(--xc-space-4); border: 1px solid var(--xc-border-card); border-radius: var(--xc-radius-md); background: var(--xc-surface-card); }
.index-summary-card span, .index-summary-card em { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); font-style: normal; }
.index-summary-card strong { color: var(--xc-text-strong); font-size: var(--xc-fs-xl); }
</style>

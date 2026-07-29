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
.index-summary-cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--xc-space-2); }
.index-summary-card { position: relative; display: grid; align-content: center; gap: 1px; min-height: 50px; padding: var(--xc-space-2) var(--xc-space-3); border: 1px solid rgba(120, 198, 255, 0.18); border-radius: var(--xc-radius-md); background: linear-gradient(145deg, rgba(255, 255, 255, 0.09), rgba(255, 255, 255, 0.035)); box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08), 0 12px 34px rgba(0, 0, 0, 0.22); overflow: hidden; }
.index-summary-card::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: linear-gradient(180deg, var(--xc-accent-blue), var(--xc-status-warn)); box-shadow: var(--xc-glow-blue); }
.index-summary-card span, .index-summary-card em { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); font-style: normal; }
.index-summary-card strong { color: var(--xc-text-strong); font-size: var(--xc-fs-md); line-height: var(--xc-lh-tight); }
.index-summary-card .xc-num { text-shadow: 0 0 18px rgba(34, 177, 253, 0.22); }
</style>

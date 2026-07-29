<template>
  <div class="ir-report-chart-card">
    <div v-if="unit" class="ir-report-chart-card__unit">{{ unit }}</div>
    <slot />
    <div v-if="$slots.interpretation" class="ir-report-chart-card__interpretation">
      <ReportSectionHeading title="如何解读" :level="3" />
      <slot name="interpretation" />
    </div>
  </div>
</template>

<script setup>
import ReportSectionHeading from './ReportSectionHeading.vue'
defineProps({ unit: { type: String, default: '' } })
</script>

<style scoped>
.ir-report-chart-card { position: relative; padding: 24px; border: 1px solid var(--xc-report-border); border-radius: var(--xc-radius-sm); background: var(--xc-report-card); break-inside: avoid; }
.ir-report-chart-card__unit { position: absolute; z-index: 1; top: 20px; right: 24px; color: var(--xc-text-mute); font-size: 12px; }
.ir-report-chart-card__interpretation { margin-top: 16px; padding: 16px 18px; border-left: 3px solid var(--xc-accent-blue); border-radius: 0 var(--xc-radius-xs) var(--xc-radius-xs) 0; background: var(--xc-report-note); color: var(--xc-text-soft); font-size: 13px; line-height: var(--xc-lh-loose); }
.ir-report-chart-card__interpretation :deep(p) { margin: 0; }
</style>

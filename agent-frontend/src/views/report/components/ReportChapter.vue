<template>
  <section class="ir-report-section" :data-chapter="chapterLabel">
    <header class="ir-report-chapter-heading" :data-chapter="chapterLabel">
      <component :is="icon" class="ir-report-chapter-heading__icon" aria-hidden="true" />
      <div>
        <p>CHAPTER {{ String(number).padStart(2, '0') }}</p>
        <h2>{{ title }}</h2>
        <span aria-hidden="true" />
      </div>
    </header>
    <slot />
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { DataAnalysis, Document, Files, Histogram, InfoFilled, List, TrendCharts } from '@element-plus/icons-vue'

const props = defineProps({
  number: { type: Number, required: true },
  title: { type: String, required: true },
})
const icons = [InfoFilled, TrendCharts, Document, List, DataAnalysis, Histogram, Files]
const icon = computed(() => icons[props.number - 1] || Document)
const chapterLabel = computed(() => props.title.replace('：', ' '))
</script>

<style scoped>
.ir-report-section { margin-top: 72px; }
.ir-report-section:first-of-type { margin-top: 0; }
.ir-report-chapter-heading { display: flex; align-items: flex-start; gap: 16px; margin: 0 0 36px; break-after: avoid; string-set: chapter attr(data-chapter); }
.ir-report-chapter-heading__icon { flex: 0 0 auto; width: 20px; height: 20px; margin-top: 4px; color: var(--xc-accent-blue); }
.ir-report-chapter-heading p { margin: 0 0 8px; color: var(--xc-text-mute); font-family: var(--xc-font-en); font-size: 11px; font-weight: var(--xc-fw-medium); letter-spacing: .15em; }
.ir-report-chapter-heading h2 { margin: 0; color: var(--xc-text-strong); font-size: 24px; font-weight: var(--xc-fw-semi); line-height: 1.35; letter-spacing: .02em; }
.ir-report-chapter-heading span { display: block; width: 42px; height: 2px; margin-top: 14px; background: var(--xc-accent-blue); }
</style>

<template>
  <section class="ir-block">
    <h4 class="ir-block__title">
      <svg class="ir-block__title-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
        <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      核心投资收益指标
    </h4>
    <div class="ir-fin" :class="{ 'ir-fin--comparison': hasComparison }">
      <div v-for="kpi in kpis" :key="kpi.label" class="ir-fin__kpi" :class="{ 'ir-fin__kpi--signature': kpi.key === 'projectIrr' }">
        <div class="ir-fin__val xc-num">
          {{ formatNumber(kpi.value) }}<span class="ir-fin__unit">{{ kpi.unit }}</span>
        </div>
        <div class="ir-fin__label">{{ kpi.label }}</div>
        <div v-if="hasComparison" class="ir-fin__delta" :class="[
          kpi.delta && kpi.delta.direction !== 'flat' ? `ir-fin__delta--${kpi.delta.tone}` : 'ir-fin__delta--placeholder',
        ]">
          <svg v-if="kpi.delta && kpi.delta.direction === 'up'" viewBox="0 0 18 18" aria-hidden="true"><path d="M3 13l4-4 3 3 5-6"/><path d="M11 6h4v4"/></svg>
          <svg v-else-if="kpi.delta && kpi.delta.direction !== 'flat'" viewBox="0 0 18 18" aria-hidden="true"><path d="M3 5l4 4 3-3 5 6"/><path d="M11 12h4V8"/></svg>
          <span v-if="kpi.delta && kpi.delta.direction !== 'flat'">{{ kpi.delta.text }}</span>
          <span v-else>— 与{{ comparisonVersion }}持平</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { formatNumber } from '@/utils/formatNumber'

import { getMetricDelta } from '@/utils/versionComparison'

const props = defineProps({
  financial: { type: Object, default: () => ({}) },
  comparisonFinancial: { type: Object, default: null },
  comparisonVersion: { type: String, default: '' },
})
const f = computed(() => props.financial || {})
const hasComparison = computed(() => Boolean(props.comparisonFinancial))
const kpis = computed(() => [
  { key: 'projectIrr', label: '项目全投资IRR', value: f.value.projectIrr, unit: '%', delta: getMetricDelta('projectIrr', f.value.projectIrr, props.comparisonFinancial?.projectIrr) },
  { key: 'projectStaticPayback', label: '全投资静态回收期', value: f.value.projectStaticPayback, unit: '年', delta: getMetricDelta('projectStaticPayback', f.value.projectStaticPayback, props.comparisonFinancial?.projectStaticPayback) },
  { key: 'capitalIrr', label: '资本金IRR', value: f.value.capitalIrr, unit: '%', delta: getMetricDelta('capitalIrr', f.value.capitalIrr, props.comparisonFinancial?.capitalIrr) },
  { key: 'capitalStaticPayback', label: '资本金静态回收期', value: f.value.capitalStaticPayback, unit: '年', delta: getMetricDelta('capitalStaticPayback', f.value.capitalStaticPayback, props.comparisonFinancial?.capitalStaticPayback) },
  { key: 'averageProfit', label: '年均利润', value: f.value.averageProfit, unit: '万元', delta: getMetricDelta('averageProfit', f.value.averageProfit, props.comparisonFinancial?.averageProfit) },
])
</script>

<style scoped>
.ir-block {
  padding: var(--xc-space-7);
}
.ir-block__title {
  display: flex;
  align-items: center;
  gap: var(--xc-space-2);
  font-size: var(--xc-fs-md);
  color: var(--xc-text-strong);
  font-weight: var(--xc-fw-semi);
  margin: 0 0 var(--xc-space-6);
}
.ir-block__title-icon {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
  color: var(--xc-accent-blue);
}
.ir-fin {
  display: grid;
  grid-template-columns: minmax(180px, 1.1fr) repeat(2, minmax(0, 1fr));
  grid-template-areas:
    'signature support-a support-b'
    'signature support-c support-d';
  gap: var(--xc-space-6) var(--xc-space-7);
  align-items: stretch;
}
.ir-fin__kpi {
  min-width: 0;
  min-height: 72px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  gap: var(--xc-space-2);
  text-align: start;
  padding: var(--xc-space-2) 0;
}
.ir-fin__kpi:nth-child(1) { grid-area: signature; }
.ir-fin__kpi:nth-child(2) { grid-area: support-a; }
.ir-fin__kpi:nth-child(3) { grid-area: support-b; }
.ir-fin__kpi:nth-child(4) { grid-area: support-c; }
.ir-fin__kpi:nth-child(5) { grid-area: support-d; }
.ir-fin__kpi--signature {
  position: relative;
  align-items: center;
  justify-content: center;
  min-height: 164px;
  padding: var(--xc-space-6);
  border-radius: var(--xc-radius-lg);
  background: var(--xc-surface-tinted);
  box-shadow: inset 0 1px 0 var(--xc-border-soft);
  text-align: center;
  overflow: hidden;
}
.ir-fin__kpi--signature::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: var(--xc-grad-brand);
  opacity: 0.08;
  pointer-events: none;
}
.ir-fin__val {
  display: inline-flex;
  align-items: baseline;
  max-width: 100%;
  white-space: nowrap;
  font-size: var(--xc-fs-kpi-md);
  font-weight: var(--xc-fw-semi);
  color: var(--xc-text-strong);
  line-height: var(--xc-lh-tight);
}
.ir-fin__kpi--signature .ir-fin__val {
  font-size: var(--xc-fs-kpi-lg);
  background: var(--xc-grad-brand);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.ir-fin__unit {
  font-size: var(--xc-fs-xs);
  color: var(--xc-text-soft);
  margin-left: 2px;
}
.ir-fin__label {
  min-height: 0;
  font-size: var(--xc-fs-sm);
  line-height: var(--xc-lh-normal);
  color: var(--xc-text-soft);
}
.ir-fin__delta {
  display: flex;
  align-items: center;
  gap: 4px;
  min-height: 22px;
  font-size: var(--xc-fs-xs);
  line-height: var(--xc-lh-normal);
}
.ir-fin__delta svg {
  width: 15px;
  height: 15px;
  flex: 0 0 auto;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.ir-fin__delta--good { color: var(--xc-status-ok); }
.ir-fin__delta--bad { color: var(--xc-status-danger); }
.ir-fin__delta--neutral { color: var(--xc-text-mute); }
@container (max-width: 980px) {
  .ir-fin {
    grid-template-columns: minmax(150px, 1fr) repeat(2, minmax(0, 1fr));
    gap: var(--xc-space-5) var(--xc-space-6);
  }
  .ir-fin__kpi--signature { min-height: 148px; }
}
@container (max-width: 680px) {
  .ir-fin {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    grid-template-areas:
      'signature signature'
      'support-a support-b'
      'support-c support-d';
    gap: var(--xc-space-5) var(--xc-space-6);
  }
  .ir-fin__kpi--signature { min-height: 132px; }
}
@container (max-width: 520px) {
  .ir-fin {
    grid-template-columns: 1fr;
    grid-template-areas:
      'signature'
      'support-a'
      'support-b'
      'support-c'
      'support-d';
    gap: var(--xc-space-5);
  }
  .ir-fin__kpi,
  .ir-fin__kpi--signature {
    min-height: 0;
    align-items: center;
    padding: var(--xc-space-2) 0;
    text-align: center;
  }
  .ir-fin__kpi--signature {
    padding: var(--xc-space-5);
  }
}
@container (max-width: 480px) {
  .ir-block { padding: var(--xc-space-5); }
  .ir-fin { gap: var(--xc-space-4); }
  .ir-fin__kpi--signature { padding: var(--xc-space-4); }
  .ir-fin__val { font-size: var(--xc-fs-kpi-sm); }
  .ir-fin__kpi--signature .ir-fin__val { font-size: var(--xc-fs-kpi-md); }
}
</style>

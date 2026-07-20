<template>
  <section class="ir-block">
    <h4 class="ir-block__title">
      <svg class="ir-block__title-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
        <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      核心投资收益指标
    </h4>
    <div class="ir-fin">
      <div v-for="kpi in kpis" :key="kpi.label" class="ir-fin__kpi" :class="{ 'ir-fin__kpi--signature': kpi.key === 'projectIrr' }">
        <div class="ir-fin__val xc-num">
          {{ formatNumber(kpi.value) }}<span class="ir-fin__unit">{{ kpi.unit }}</span>
        </div>
        <div class="ir-fin__label">{{ kpi.label }}</div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { formatNumber } from '@/utils/formatNumber'

const props = defineProps({ financial: { type: Object, default: () => ({}) } })
const f = computed(() => props.financial || {})
const kpis = computed(() => [
  { key: 'projectIrr', label: '项目全投资IRR', value: f.value.projectIrr, unit: '%' },
  { key: 'projectStaticPayback', label: '全投资静态回收期', value: f.value.projectStaticPayback, unit: '年' },
  { key: 'capitalIrr', label: '资本金IRR', value: f.value.capitalIrr, unit: '%' },
  { key: 'capitalStaticPayback', label: '资本金静态回收期', value: f.value.capitalStaticPayback, unit: '年' },
  { key: 'averageProfit', label: '年均利润', value: f.value.averageProfit, unit: '万元' },
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
  margin: 0 0 var(--xc-space-5);
}
.ir-block__title-icon {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
  color: var(--xc-accent-blue);
}
.ir-fin {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--xc-space-4);
}
.ir-fin__kpi {
  min-width: 0;
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-md);
  background: var(--xc-surface-control);
  padding: var(--xc-space-5);
}
.ir-fin__kpi--signature {
  border-color: var(--xc-border-accent);
  box-shadow: inset 0 1px 0 var(--xc-border-card), var(--xc-glow-blue);
}
.ir-fin__val {
  font-size: var(--xc-fs-kpi-md);
  font-weight: var(--xc-fw-semi);
  color: var(--xc-text-strong);
  line-height: var(--xc-lh-tight);
}
.ir-fin__kpi--signature .ir-fin__val {
  background: var(--xc-grad-brand);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.ir-fin__unit {
  font-size: var(--xc-fs-2xs);
  color: var(--xc-text-mute);
  margin-left: 2px;
}
.ir-fin__label {
  font-size: var(--xc-fs-xs);
  color: var(--xc-text-soft);
  margin-top: var(--xc-space-2);
}
@media (max-width: 980px) {
  .ir-fin { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 520px) {
  .ir-fin { grid-template-columns: 1fr; }
}
</style>

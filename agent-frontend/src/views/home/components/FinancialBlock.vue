<template>
  <section class="ir-block">
    <h4 class="ir-block__title">
      <svg class="ir-block__title-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
        <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      核心投资收益指标
    </h4>
    <div class="ir-fin">
      <div v-for="kpi in kpis" :key="kpi.label" class="ir-fin__kpi">
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
  { label: '项目全投资IRR', value: f.value.projectIrr, unit: '%' },
  { label: '全投资静态回收期', value: f.value.projectStaticPayback, unit: '年' },
  { label: '资本金IRR', value: f.value.capitalIrr, unit: '%' },
  { label: '资本金静态回收期', value: f.value.capitalStaticPayback, unit: '年' },
  { label: '年均利润', value: f.value.averageProfit, unit: '万元' },
])
</script>

<style scoped>
.ir-block {
  padding: var(--xc-space-6);
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
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: var(--xc-space-4);
}
.ir-fin__kpi {
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--xc-radius-md);
  background: rgba(255, 255, 255, 0.04);
  padding: var(--xc-space-5);
}
.ir-fin__val {
  font-size: var(--xc-fs-kpi-sm);
  font-weight: var(--xc-fw-semi);
  color: var(--xc-accent-blue);
  line-height: var(--xc-lh-tight);
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
</style>

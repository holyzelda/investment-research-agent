<template>
  <p class="ir-disclaimer" :class="`ir-disclaimer--${variant}`" role="note">
    <Info class="ir-disclaimer__icon" :size="14" aria-hidden="true" />
    <span>{{ DISCLAIMER_TEXT }}</span>
  </p>
</template>

<script setup>
import { Info } from '@lucide/vue'

const DISCLAIMER_TEXT = '测算结果基于输入参数及模型假设，仅供项目研判参考，不构成投资承诺或建议。'

defineProps({
  variant: { type: String, default: 'compact', validator: (value) => ['compact', 'report'].includes(value) },
})
</script>

<style scoped>
.ir-disclaimer {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin: 0;
  color: var(--xc-text-soft);
  font-weight: var(--xc-fw-regular);
  line-height: var(--xc-lh-normal);
}
.ir-disclaimer__icon { flex: 0 0 auto; margin-top: 2px; color: currentColor; stroke-width: 1.8; }
.ir-disclaimer span { min-width: 0; overflow-wrap: anywhere; }
.ir-disclaimer--compact { font-size: max(12px, var(--xc-fs-xs)); }
.ir-disclaimer--report { font-size: 9pt; }
@media print {
  .ir-disclaimer { break-inside: avoid; page-break-inside: avoid; }
}
</style>

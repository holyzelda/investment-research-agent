<template>
  <div class="ir-result">
    <div class="ir-result__head">
      <span class="ir-result__ok">测算完成 ✓</span>
      <span v-if="version" class="ir-result__ver">{{ version }}</span>
    </div>

    <BasicInfoBlock :basic-info="result.basicInfo" />
    <div class="ir-result__divider" />
    <FinancialBlock :financial="result.financial" />
    <div class="ir-result__divider" />

    <section class="ir-block">
      <h4 class="ir-block__title">③ 进阶图形结果</h4>
      <RevenueDonut :donut="advanced.donut" />
      <CashflowLines :lines="advanced.lines" />
    </section>

    <div v-if="warnings.length" class="ir-result__warn">
      <span v-for="(w, i) in warnings" :key="i">⚠ {{ w }}</span>
    </div>

    <div class="ir-result__footer">
      <button class="ir-result__act" disabled>▸ 调整参数并重新测算（Batch 5）</button>
      <button class="ir-result__act ir-result__act--ghost" @click="showReportPlaceholder">生成报告*</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import BasicInfoBlock from './BasicInfoBlock.vue'
import FinancialBlock from './FinancialBlock.vue'
import RevenueDonut from './RevenueDonut.vue'
import CashflowLines from './CashflowLines.vue'

const props = defineProps({
  result: { type: Object, required: true },
  version: { type: String, default: '' },
})
const advanced = computed(() => props.result.advanced || { donut: {}, lines: {} })
const warnings = computed(() => props.result.warnings || [])
const showReportPlaceholder = () => ElMessage.info('报告功能将在后续开放')
</script>

<style scoped>
.ir-result {
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--xc-radius-lg);
  background: rgba(255, 255, 255, 0.025);
  overflow: hidden;
}
.ir-result__head {
  display: flex;
  align-items: center;
  gap: var(--xc-space-3);
  padding: var(--xc-space-5) var(--xc-space-6);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.035);
}
.ir-result__ok {
  font-size: var(--xc-fs-sm);
  color: var(--xc-status-ok);
  font-weight: var(--xc-fw-semi);
}
.ir-result__ver {
  font-size: var(--xc-fs-2xs);
  color: var(--xc-text-inverse);
  background: var(--xc-accent-blue);
  border-radius: var(--xc-radius-full);
  padding: 1px var(--xc-space-3);
}
.ir-result__divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.08);
  margin: 0 var(--xc-space-6);
}
.ir-block {
  padding: var(--xc-space-6);
}
.ir-block__title {
  font-size: var(--xc-fs-md);
  color: var(--xc-text-strong);
  font-weight: var(--xc-fw-semi);
  margin: 0 0 var(--xc-space-5);
}
.ir-result__warn {
  display: flex;
  flex-direction: column;
  gap: var(--xc-space-2);
  padding: 0 var(--xc-space-6) var(--xc-space-5);
  font-size: var(--xc-fs-xs);
  color: var(--xc-status-warn);
}
.ir-result__footer {
  display: flex;
  align-items: center;
  gap: var(--xc-space-4);
  padding: var(--xc-space-5) var(--xc-space-6);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
.ir-result__act {
  font-size: var(--xc-fs-xs);
  color: var(--xc-text-soft);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--xc-radius-md);
  padding: var(--xc-space-2) var(--xc-space-4);
  cursor: not-allowed;
}
.ir-result__act--ghost {
  background: transparent;
}
</style>

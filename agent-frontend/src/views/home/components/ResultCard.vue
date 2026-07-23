<template>
  <div class="ir-result">
    <div class="ir-result__head ir-result__head--complete">
      <span class="ir-result__ok">测算完成 ✓</span>
      <span v-if="version" class="ir-result__ver">{{ version }}</span>
    </div>

    <section class="ir-report-module">
      <BasicInfoBlock :basic-info="result.basicInfo" />
    </section>
    <section class="ir-report-module">
      <FinancialBlock :financial="result.financial" />
    </section>

    <section class="ir-report-module ir-block">
      <h4 class="ir-block__title">
        <svg class="ir-block__title-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
          <path d="M3 3v18h18" stroke-linecap="round" />
          <path d="m7 15 4-4 3 3 4-6" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        收益数据深度分析
      </h4>
      <RevenueDonut :donut="advanced.donut" />
      <DebtServiceCoverage :coverage="advanced.debtServiceCoverage" />
    </section>

    <div v-if="warnings.length" class="ir-result__warn">
      <span v-for="(w, i) in warnings" :key="i">⚠ {{ w }}</span>
    </div>

    <ParamAdjustPanel
      v-if="paramDict.length"
      :param-dict="paramDict"
      :switches="switches"
      :seed-input="seedInput"
      :station-options="stationOptions"
      :version="version"
      :responding="responding"
      :advanced-overrides="advancedOverrides"
      @recalculate="$emit('recalculate', $event)"
      @open-advanced="advancedOpen = true"
    />

    <AdvancedParamDialog
      v-model="advancedOpen"
      :param-dict="paramDict"
      :seed-input="seedInput"
      @save="saveAdvancedDraft"
    />

    <div class="ir-result__footer">
      <button
        v-if="report?.status === 'completed'"
        class="ir-result__act ir-result__act--ghost"
        @click="$emit('view-report', report.reportId)"
      >已生成报告</button>
      <button
        v-else
        class="ir-result__act ir-result__act--ghost"
        :disabled="report?.status === 'generating'"
        @click="$emit('generate-report')"
      >{{ report?.status === 'generating' ? '报告生成中' : report?.status === 'failed' ? '重新生成报告' : '生成报告' }}</button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import BasicInfoBlock from './BasicInfoBlock.vue'
import FinancialBlock from './FinancialBlock.vue'
import RevenueDonut from './RevenueDonut.vue'
import DebtServiceCoverage from './DebtServiceCoverage.vue'
import ParamAdjustPanel from './ParamAdjustPanel.vue'
import AdvancedParamDialog from './AdvancedParamDialog.vue'

const props = defineProps({
  result: { type: Object, required: true },
  version: { type: String, default: '' },
  seedInput: { type: Object, default: () => ({}) },
  paramDict: { type: Array, default: () => [] },
  switches: { type: Object, default: () => ({}) },
  stationOptions: { type: Array, default: () => [] },
  responding: { type: Boolean, default: false },
  report: { type: Object, default: null },
})
defineEmits(['recalculate', 'generate-report', 'view-report'])
const advanced = computed(() => props.result.advanced || { donut: {}, debtServiceCoverage: {} })
const warnings = computed(() => props.result.warnings || [])
const advancedOpen = ref(false)
const advancedOverrides = ref({})

// 高级参数仅是当前结果卡的未提交草稿：新版本/历史版本切换到其他入参时自动清空。
watch(() => [props.version, props.seedInput], () => { advancedOverrides.value = {} }, { deep: true })
function saveAdvancedDraft(overrides) {
  advancedOverrides.value = overrides
}
</script>

<style scoped>
.ir-result {
  display: flex;
  flex-direction: column;
  gap: var(--xc-space-5);
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-xl);
  background: var(--xc-surface-raised);
  box-shadow: var(--xc-shadow-raised);
  overflow: hidden;
}
.ir-result__head {
  display: flex;
  align-items: center;
  gap: var(--xc-space-3);
  padding: var(--xc-space-5) var(--xc-space-7);
  border-bottom: 1px solid var(--xc-border-soft);
  background: var(--xc-surface-control);
}
.ir-result__head--complete { box-shadow: inset 3px 0 0 var(--xc-accent-blue); }
.ir-result__ok { font-size:var(--xc-fs-sm); color:var(--xc-status-ok); font-weight:var(--xc-fw-semi); }
.ir-result__ver { font-size:var(--xc-fs-2xs); color:var(--xc-text-inverse); background:var(--xc-accent-blue); border-radius:var(--xc-radius-full); padding:1px var(--xc-space-3); }
.ir-report-module {
  margin: 0 var(--xc-space-6);
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-lg);
  background: var(--xc-surface-card);
  box-shadow: var(--xc-shadow-sm);
  overflow: hidden;
}
.ir-block { padding:var(--xc-space-7); }
.ir-block__title { display:flex; align-items:center; gap:var(--xc-space-2); font-size:var(--xc-fs-md); color:var(--xc-text-strong); font-weight:var(--xc-fw-semi); margin:0 0 var(--xc-space-5); }
.ir-block__title-icon { width:18px; height:18px; flex:0 0 auto; color:var(--xc-accent-blue); }
.ir-result__warn { display:flex; flex-direction:column; gap:var(--xc-space-2); padding:0 var(--xc-space-6); font-size:var(--xc-fs-xs); color:var(--xc-status-warn); }
.ir-result__footer { display:flex; align-items:center; gap:var(--xc-space-4); padding:var(--xc-space-5) var(--xc-space-6); border-top:1px solid var(--xc-border-soft); }
.ir-result__act { font-size:var(--xc-fs-xs); color:var(--xc-text-soft); background:var(--xc-surface-card); border:1px solid var(--xc-border-card); border-radius:var(--xc-radius-md); padding:var(--xc-space-2) var(--xc-space-4); cursor:not-allowed; }
.ir-result__act--ghost { background:transparent; }
</style>

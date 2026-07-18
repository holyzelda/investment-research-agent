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
      <button class="ir-result__act ir-result__act--ghost" @click="showReportPlaceholder">生成报告*</button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
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
})
defineEmits(['recalculate'])
const advanced = computed(() => props.result.advanced || { donut: {}, debtServiceCoverage: {} })
const warnings = computed(() => props.result.warnings || [])
const advancedOpen = ref(false)
const advancedOverrides = ref({})

// 高级参数仅是当前结果卡的未提交草稿：新版本/历史版本切换到其他入参时自动清空。
watch(() => [props.version, props.seedInput], () => { advancedOverrides.value = {} }, { deep: true })
function saveAdvancedDraft(overrides) {
  advancedOverrides.value = overrides
}
const showReportPlaceholder = () => ElMessage.info('报告功能将在后续开放')
</script>

<style scoped>
.ir-result { border: 1px solid rgba(255,255,255,.1); border-radius: var(--xc-radius-lg); background: rgba(255,255,255,.025); overflow:hidden; }
.ir-result__head { display:flex; align-items:center; gap:var(--xc-space-3); padding:var(--xc-space-5) var(--xc-space-6); border-bottom:1px solid rgba(255,255,255,.08); background:rgba(255,255,255,.035); }
.ir-result__ok { font-size:var(--xc-fs-sm); color:var(--xc-status-ok); font-weight:var(--xc-fw-semi); }
.ir-result__ver { font-size:var(--xc-fs-2xs); color:var(--xc-text-inverse); background:var(--xc-accent-blue); border-radius:var(--xc-radius-full); padding:1px var(--xc-space-3); }
.ir-result__divider { height:1px; background:rgba(255,255,255,.08); margin:0 var(--xc-space-6); }
.ir-block { padding:var(--xc-space-6); }
.ir-block__title { display:flex; align-items:center; gap:var(--xc-space-2); font-size:var(--xc-fs-md); color:var(--xc-text-strong); font-weight:var(--xc-fw-semi); margin:0 0 var(--xc-space-5); }
.ir-block__title-icon { width:18px; height:18px; flex:0 0 auto; color:var(--xc-accent-blue); }
.ir-result__warn { display:flex; flex-direction:column; gap:var(--xc-space-2); padding:0 var(--xc-space-6) var(--xc-space-5); font-size:var(--xc-fs-xs); color:var(--xc-status-warn); }
.ir-result__footer { display:flex; align-items:center; gap:var(--xc-space-4); padding:var(--xc-space-5) var(--xc-space-6); border-top:1px solid rgba(255,255,255,.08); }
.ir-result__act { font-size:var(--xc-fs-xs); color:var(--xc-text-soft); background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.1); border-radius:var(--xc-radius-md); padding:var(--xc-space-2) var(--xc-space-4); cursor:not-allowed; }
.ir-result__act--ghost { background:transparent; }
</style>

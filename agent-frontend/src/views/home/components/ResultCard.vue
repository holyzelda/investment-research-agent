<template>
  <div class="ir-result ir-result--complete">
    <div class="ir-result__banner" :style="{ backgroundImage: `url(${welcomeBackgroundSrc})` }">
      <div class="ir-result__banner-mask" />
      <!-- 状态胶囊叠在横幅左上角内部：测算完成 + 版本 -->
      <div class="ir-result__banner-status">
        <span class="ir-result__ok">测算完成 ✓</span>
        <span v-if="version" class="ir-result__ver">{{ version }}</span>
      </div>
      <div class="ir-result__banner-body">
        <h3 class="ir-result__banner-title">{{ bannerTitle }}</h3>
        <p class="ir-result__banner-sub">
          <span>测算时间 {{ calculatedAtText }}</span>
          <span v-if="version" class="ir-result__banner-dot">·</span>
          <span v-if="version">测算版本 {{ version }}</span>
        </p>
      </div>
    </div>

    <section class="ir-report-module">
      <BasicInfoBlock :basic-info="result.basicInfo" />
    </section>
    <section class="ir-report-module">
      <FinancialBlock :financial="result.financial" />
    </section>

    <section class="ir-report-module ir-report-module--bare">
      <div class="ir-result__charts">
        <RevenueDonut :donut="advanced.donut" />
        <DebtServiceCoverage :coverage="advanced.debtServiceCoverage" />
      </div>
    </section>

    <div v-if="warnings.length" class="ir-result__warn">
      <span v-for="(w, i) in warnings" :key="i">⚠ {{ w }}</span>
    </div>

    <ParamAdjustPanel
      v-if="paramDict.length"
      ref="paramAdjustPanel"
      :param-dict="paramDict"
      :switches="switches"
      :seed-input="seedInput"
      :station-options="stationOptions"
      :version="version"
      :responding="responding"
      :advanced-overrides="advancedOverrides"
      :advanced-override-count="advancedOverrideCount"
      @recalculate="$emit('recalculate', $event)"
      @open-advanced="openAdvanced"
    />

    <AdvancedParamDialog
      v-model="advancedOpen"
      :param-dict="paramDict"
      :seed-input="seedInput"
      :draft-input="advancedOverrides"
      @update:model-value="handleAdvancedOpenChange"
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
import { computed, nextTick, ref, watch } from 'vue'
import BasicInfoBlock from './BasicInfoBlock.vue'
import FinancialBlock from './FinancialBlock.vue'
import RevenueDonut from './RevenueDonut.vue'
import DebtServiceCoverage from './DebtServiceCoverage.vue'
import ParamAdjustPanel from './ParamAdjustPanel.vue'
import AdvancedParamDialog from './AdvancedParamDialog.vue'
import welcomeBackgroundSrc from '@/assets/home-welcome-background.png'
import { roundToStep } from '@/utils/paramAdjust'

const props = defineProps({
  result: { type: Object, required: true },
  version: { type: String, default: '' },
  calculatedAt: { type: String, default: '' },
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

const bannerTitle = computed(() => {
  const province = props.result.basicInfo?.province || ''
  const node = props.result.basicInfo?.nodeName || ''
  return `${province}${node}储能项目测算结果`.trim()
})
// 直接从 ISO 串取分量拼成本地展示，避免 new Date 引入时区偏移；缺失时展示占位
const calculatedAtText = computed(() => {
  const m = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})/.exec(props.calculatedAt || '')
  if (!m) return '—'
  const [, y, mo, d, hh, mm, ss] = m
  return `${y}年${mo}月${d}日 ${hh}:${mm}:${ss}`
})
const advancedOpen = ref(false)
const advancedOverrides = ref({})
const paramAdjustPanel = ref(null)
const ADVANCED_IDS = new Set([
  'operation_years', 'mid_long_charge_avg', 'mid_long_discharge_avg',
  'strategy_achievement_rate', 'capacity_achievement_rate',
  'battery_replace_cost', 'maint_cost', 'opex_cost',
])
const advancedOverrideCount = computed(() => props.paramDict.reduce((count, spec) => {
  if (!ADVANCED_IDS.has(spec.id) || spec.g !== 1 || !['slider', 'dynamic_slider', 'select'].includes(spec.control)) return count
  if (!(spec.id in advancedOverrides.value)) return count
  const draft = normalizeAdvancedValue(advancedOverrides.value[spec.id], spec.step)
  const baselineValue = spec.id in props.seedInput ? props.seedInput[spec.id] : spec.default
  const baseline = normalizeAdvancedValue(baselineValue, spec.step)
  return draft === baseline ? count : count + 1
}, 0))

// 高级参数仅是当前结果卡的未提交草稿：新版本/历史版本切换到其他入参时自动清空。
watch(() => [props.version, props.seedInput], () => { advancedOverrides.value = {} }, { deep: true })
function normalizeAdvancedValue(value, step) {
  return typeof value === 'number' && step ? roundToStep(value, step) : value
}
function openAdvanced() {
  advancedOpen.value = true
}
async function handleAdvancedOpenChange(open) {
  advancedOpen.value = open
  if (open) return
  await nextTick()
  paramAdjustPanel.value?.focusAdvancedTrigger()
}
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
  /* 底层不再用灰色毛玻璃，改用贴近横幅底部（采样 #000516）的深蓝黑，
     让横幅图与下方内容区连成同一块深色面；轻微竖向渐变给一点纵深。 */
  background: linear-gradient(180deg, rgba(3, 8, 22, 0.97) 0%, rgba(8, 14, 30, 0.97) 100%);
  box-shadow: var(--xc-shadow-raised);
  overflow: hidden;
}
.ir-result__ok { font-size:var(--xc-fs-base); color:var(--xc-status-ok); font-weight:var(--xc-fw-semi); }
.ir-result__ver { font-size:var(--xc-fs-2xs); color:var(--xc-text-inverse); background:var(--xc-accent-blue); border-radius:var(--xc-radius-full); padding:1px var(--xc-space-3); }
/* 顶部图靠右对齐占 66% 宽，高度压短；图垂直方向居中裁剪（上下各裁一点），
   左侧 34% 为深蓝黑填充，放标题/时间内容。 */
.ir-result__banner {
  position: relative;
  display: flex;
  align-items: center;
  margin: 0;
  height: clamp(160px, 18vw, 220px);
  border-radius: var(--xc-radius-xl) var(--xc-radius-xl) 0 0;
  background-color: #010515;
  background-position: right center;
  background-size: 66% auto;
  background-repeat: no-repeat;
  overflow: hidden;
}
/* 状态胶囊叠在横幅左上角内部 */
.ir-result__banner-status {
  position: absolute;
  z-index: 1;
  top: var(--xc-space-5);
  left: var(--xc-space-7);
  display: flex;
  align-items: center;
  gap: var(--xc-space-4);
}
/* 左深右透遮罩：左侧压暗保证标题可读，右侧图面保持清晰 */
.ir-result__banner-mask {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, rgba(3, 8, 22, 0.85) 0%, rgba(3, 8, 22, 0.45) 42%, rgba(3, 8, 22, 0) 68%);
}
.ir-result__banner-body {
  position: relative;
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: var(--xc-space-2);
  padding: var(--xc-space-7);
}
.ir-result__banner-title {
  margin: 0;
  font-size: var(--xc-fs-h3);
  font-weight: var(--xc-fw-bold);
  color: var(--xc-text-strong);
}
.ir-result__banner-sub {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--xc-space-2);
  margin: 0;
  font-size: var(--xc-fs-2xs);
  color: var(--xc-text-soft);
}
.ir-result__banner-dot { color: var(--xc-text-mute); }
.ir-report-module {
  margin: 0 var(--xc-space-6);
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-lg);
  background: var(--xc-surface-card);
  box-shadow: var(--xc-shadow-sm);
  overflow: hidden;
}
/* 双图并排容器不套外层卡片外观，两图各自成卡直接铺在结果卡上 */
.ir-report-module--bare { border:0; background:transparent; box-shadow:none; overflow:visible; }
.ir-block { padding:var(--xc-space-7); }
.ir-block__title { display:flex; align-items:center; gap:var(--xc-space-2); font-size:var(--xc-fs-md); color:var(--xc-text-strong); font-weight:var(--xc-fw-semi); margin:0 0 var(--xc-space-5); }
.ir-block__title-icon { width:18px; height:18px; flex:0 0 auto; color:var(--xc-accent-blue); }
/* 收益环形(占 1/3) + 微债折线(占 2/3) 左右并排；窄屏回退为上下堆叠 */
.ir-result__charts { display:grid; grid-template-columns:1fr 2fr; gap:var(--xc-space-6); align-items:stretch; }
.ir-result__charts > * { min-width:0; }
@media (max-width:900px) { .ir-result__charts { grid-template-columns:1fr; } }
.ir-result__warn { display:flex; flex-direction:column; gap:var(--xc-space-2); padding:0 var(--xc-space-6); font-size:var(--xc-fs-xs); color:var(--xc-status-warn); }
.ir-result__footer { display:flex; align-items:center; gap:var(--xc-space-4); padding:var(--xc-space-5) var(--xc-space-6); border-top:1px solid var(--xc-border-soft); }
.ir-result__act { font-size:var(--xc-fs-xs); color:var(--xc-text-soft); background:var(--xc-surface-card); border:1px solid var(--xc-border-card); border-radius:var(--xc-radius-md); padding:var(--xc-space-2) var(--xc-space-4); cursor:not-allowed; }
.ir-result__act--ghost { background:transparent; }
</style>

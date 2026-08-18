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
        <label v-if="availableVersions.length" class="ir-result__compare">
          <span>对比基准</span>
          <div class="ir-result__compare-wrap">
            <select :value="comparisonVersion" @change="$emit('compare-version-change', $event.target.value)" aria-label="选择对比版本">
              <option v-for="item in availableVersions" :key="item.version" :value="item.version">
                {{ item.version }}{{ item.isPrevious ? ' · 上一版' : '' }}
              </option>
            </select>
            <ChevronDown class="ir-result__compare-chevron" :size="14" aria-hidden="true" />
          </div>
        </label>
      </div>
    </div>

    <section v-if="comparisonVersion" class="ir-report-module ir-version-diff">
      <header class="ir-version-diff__head">
        <h4>版本变化</h4>
        <span>较 {{ comparisonVersion }} · {{ versionDiff.totalCount }} 项变化</span>
      </header>
      <div v-if="versionDiff.totalCount" class="ir-version-diff__body">
        <div v-for="group in versionDiff.groups" :key="group.category" class="ir-version-diff__group">
          <h5>{{ group.label }} <span>{{ group.items.length }} 项</span></h5>
          <div v-for="item in group.items" :key="item.id" class="ir-version-diff__row">
            <span class="ir-version-diff__name">{{ item.label }}</span>
            <span class="ir-version-diff__old xc-num">{{ displayParam(item.oldValue) }}</span>
            <span class="ir-version-diff__arrow">→</span>
            <span class="ir-version-diff__new xc-num">{{ displayParam(item.newValue) }}</span>
            <span class="ir-version-diff__source" :class="`is-${item.source}`">{{ item.source === 'explicit' ? '主动调整' : '联动更新' }}</span>
          </div>
        </div>
      </div>
      <div v-else class="ir-version-diff__empty">与 {{ comparisonVersion }} 相比，测算参数未发生变化</div>
    </section>

    <section class="ir-report-module">
      <BasicInfoBlock :basic-info="result.basicInfo" />
    </section>
    <section class="ir-report-module">
      <FinancialBlock :financial="result.financial" :comparison-financial="comparisonResult?.financial" :comparison-version="comparisonVersion" />
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
      v-if="adjustable && paramDict.length"
      :param-dict="paramDict"
      :switches="switches"
      :seed-input="seedInput"
      :comparison-input="comparisonInput"
      :station-options="stationOptions"
      :station-loading="stationLoading"
      :station-has-more="stationHasMore"
      :station-error="stationError"
      :version="version"
      :responding="responding"
      :advanced-overrides="advancedOverrides"
      :advanced-override-count="advancedOverrideCount"
      :advanced-validation-error="advancedValidationError"
      @recalculate="$emit('recalculate', $event)"
      @dirty-change="regularParametersDirty = $event"
      @discard-all-changes="discardAllParameterChanges"
      @station-open="$emit('station-open', $event)"
      @station-search="$emit('station-search', $event)"
      @station-load-more="$emit('station-load-more', $event)"
    >
      <template #advanced>
        <AdvancedParamDialog
          embedded
          :param-dict="paramDict"
          :seed-input="seedInput"
          :comparison-input="comparisonInput"
          :draft-input="advancedOverrides"
          :disabled="responding"
          @save="saveAdvancedDraft"
          @validation-change="advancedValidationError = $event"
        />
      </template>
    </ParamAdjustPanel>

    <div v-if="report?.status !== 'completed'" class="ir-result__footer">
      <span v-if="hasPendingParameterChanges" id="ir-result-report-hint" class="ir-result__report-hint">
        参数修改尚未形成新版本，请先重新测算
      </span>
      <span v-else class="ir-result__report-hint">确认当前测算结果后，可生成正式投资报告</span>
      <div class="ir-result__footer-actions">
        <button
          type="button"
          class="ir-result__act"
          aria-label="分享此测算结果"
          @click="shareDialogVisible = true"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
            <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" stroke-linecap="round" stroke-linejoin="round" />
            <path d="m16 6-4-4-4 4" stroke-linecap="round" stroke-linejoin="round" />
            <path d="M12 2v13" stroke-linecap="round" />
          </svg>
          分享
        </button>
        <button
          type="button"
          class="ir-result__act"
          data-testid="report-btn"
          :disabled="report?.status === 'generating' || hasPendingParameterChanges"
          :aria-describedby="hasPendingParameterChanges ? 'ir-result-report-hint' : undefined"
          @click="$emit('generate-report')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
            <path d="M6 2.75h8l4 4V21.25H6z" stroke-linejoin="round" />
            <path d="M14 2.75v4h4M9 11h6M9 14.5h6M9 18h4" stroke-linecap="round" />
          </svg>
          {{ hasPendingParameterChanges ? '请先重新测算' : report?.status === 'generating' ? '报告生成中' : report?.status === 'failed' ? '重新生成报告' : '生成报告' }}
        </button>
      </div>
    </div>

    <ShareDialog
      v-model:visible="shareDialogVisible"
      :conversation-id="conversationId"
      :task-id="taskId"
      :version="version"
    />
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
import ShareDialog from './ShareDialog.vue'
import welcomeBackgroundSrc from '@/assets/home-welcome-background.png'
import { resolveVariant, roundToStep } from '@/utils/paramAdjust'
import { buildResultTitle } from '@/utils/projectTitle'
import { ChevronDown } from '@lucide/vue'
import { diffVersionInputs } from '@/utils/versionComparison'

const props = defineProps({
  result: { type: Object, required: true },
  version: { type: String, default: '' },
  calculatedAt: { type: String, default: '' },
  seedInput: { type: Object, default: () => ({}) },
  comparisonInput: { type: Object, default: null },
  paramDict: { type: Array, default: () => [] },
  switches: { type: Object, default: () => ({}) },
  stationOptions: { type: Array, default: () => [] },
  stationLoading: { type: Boolean, default: false },
  stationHasMore: { type: Boolean, default: false },
  stationError: { type: String, default: '' },
  responding: { type: Boolean, default: false },
  report: { type: Object, default: null },
  comparisonVersion: { type: String, default: '' },
  displayComparisonInput: { type: Object, default: null },
  comparisonResult: { type: Object, default: null },
  availableVersions: { type: Array, default: () => [] },
  changeMeta: { type: Object, default: () => ({}) },
  adjustable: { type: Boolean, default: true },
  conversationId: { type: String, default: '' },
  taskId: { type: [Number, String], default: null },
})
defineEmits([
  'recalculate',
  'generate-report',
  'compare-version-change',
  'station-open',
  'station-search',
  'station-load-more',
])
const advanced = computed(() => props.result.advanced || { donut: {}, debtServiceCoverage: {} })
const warnings = computed(() => props.result.warnings || [])
const versionDiff = computed(() => diffVersionInputs(
  props.seedInput,
  props.displayComparisonInput || {},
  props.changeMeta,
  props.paramDict,
))
function displayParam(value) {
  if (value === null || value === undefined || value === '') return '无'
  if (typeof value === 'number') return Number(value.toFixed(4)).toString()
  return String(value)
}

const bannerTitle = computed(() => buildResultTitle(
  props.result.basicInfo?.province,
  props.result.basicInfo?.nodeName,
))
// 直接从 ISO 串取分量拼成本地展示，避免 new Date 引入时区偏移；缺失时展示占位
const calculatedAtText = computed(() => {
  const m = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})/.exec(props.calculatedAt || '')
  if (!m) return '—'
  const [, y, mo, d, hh, mm, ss] = m
  return `${y}年${mo}月${d}日 ${hh}:${mm}:${ss}`
})
const advancedOverrides = ref({})
const advancedValidationError = ref(false)
const regularParametersDirty = ref(false)
const shareDialogVisible = ref(false)
const ADVANCED_IDS = new Set([
  'operation_years', 'mid_long_charge_avg', 'mid_long_discharge_avg',
  'strategy_achievement_rate', 'capacity_achievement_rate',
  'battery_replace_cost', 'maint_cost', 'opex_cost',
])
const advancedOverrideCount = computed(() => props.paramDict.reduce((count, spec) => {
  if (!ADVANCED_IDS.has(spec.id) || spec.g !== 1) return count
  // 控件形态/步长/默认值按当前版本运营期解析 variants（换电成本 20 年档才是可编辑 slider）
  const resolved = resolveVariant(spec, props.seedInput?.operation_years)
  if (!['slider', 'dynamic_slider', 'select'].includes(resolved.control)) return count
  if (!(spec.id in advancedOverrides.value)) return count
  const draft = normalizeAdvancedValue(advancedOverrides.value[spec.id], resolved.step)
  const baselineValue = spec.id in props.seedInput ? props.seedInput[spec.id] : resolved.default
  const baseline = normalizeAdvancedValue(baselineValue, resolved.step)
  return draft === baseline ? count : count + 1
}, 0))
const hasPendingParameterChanges = computed(() => regularParametersDirty.value || advancedOverrideCount.value > 0 || advancedValidationError.value)

// 高级参数仅是当前结果卡的未提交草稿：新版本/历史版本切换到其他入参时自动清空。
watch(() => [props.version, props.seedInput], () => {
  advancedOverrides.value = {}
  advancedValidationError.value = false
  regularParametersDirty.value = false
}, { deep: true })
function normalizeAdvancedValue(value, step) {
  return typeof value === 'number' && step ? roundToStep(value, step) : value
}
function saveAdvancedDraft(overrides) {
  advancedOverrides.value = overrides
}
function discardAllParameterChanges() {
  advancedOverrides.value = {}
  advancedValidationError.value = false
}
</script>

<style scoped>
.ir-result {
  container-type: inline-size;
  display: flex;
  flex-direction: column;
  gap: var(--xc-space-5);
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-sm);
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
  border-radius: var(--xc-radius-sm) var(--xc-radius-sm) 0 0;
  background-color: #010515;
  background-position: center center;
  background-size: cover;
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
  background:
    linear-gradient(90deg, rgba(3, 8, 22, 0.9) 0%, rgba(3, 8, 22, 0.58) 44%, rgba(3, 8, 22, 0.14) 82%),
    linear-gradient(180deg, rgba(3, 8, 22, 0.12), rgba(3, 8, 22, 0.46));
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
.ir-result__compare {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: var(--xc-space-3);
  margin-top: var(--xc-space-4);
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-2xs);
  font-weight: var(--xc-fw-medium);
  white-space: nowrap;
}
.ir-result__compare span { flex-shrink: 0; }
.ir-result__compare-wrap {
  position: relative;
  display: flex;
  align-items: center;
  min-width: 148px;
}
.ir-result__compare-wrap select {
  width: 100%;
  height: 30px;
  padding: 0 var(--xc-space-7) 0 var(--xc-space-3);
  border: 1px solid var(--xc-border-accent);
  border-radius: var(--xc-radius-sm);
  outline: none;
  background: var(--xc-surface-control);
  color: var(--xc-text-strong);
  font-family: var(--xc-font-zh);
  font-size: var(--xc-fs-xs);
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  transition: border-color var(--xc-dur-fast) var(--xc-ease-out),
              background-color var(--xc-dur-fast) var(--xc-ease-out),
              box-shadow var(--xc-dur-fast) var(--xc-ease-out);
}
.ir-result__compare-wrap select:hover {
  border-color: var(--xc-accent-blue);
  background: var(--xc-accent-blue-soft);
}
.ir-result__compare-wrap select:focus-visible {
  border-color: var(--xc-accent-blue);
  box-shadow: 0 0 0 2px var(--xc-accent-blue-soft);
}
.ir-result__compare-wrap select option {
  background: var(--xc-surface-raised);
  color: var(--xc-text-strong);
}
.ir-result__compare-chevron {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: var(--xc-text-mute);
}
@media (prefers-reduced-motion: reduce) {
  .ir-result__compare-wrap select { transition: none; }
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
.ir-version-diff__head { min-height: 48px; display: flex; align-items: center; justify-content: space-between; gap: var(--xc-space-4); padding: 0 var(--xc-space-5); border-bottom: 1px solid var(--xc-border-soft); }
.ir-version-diff__head h4 { margin: 0; color: var(--xc-text-strong); font-size: var(--xc-fs-md); }
.ir-version-diff__head span { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.ir-version-diff__body { padding: var(--xc-space-2) var(--xc-space-5) var(--xc-space-5); }
.ir-version-diff__group { padding-top: var(--xc-space-4); }
.ir-version-diff__group + .ir-version-diff__group { margin-top: var(--xc-space-3); border-top: 1px solid var(--xc-border-soft); }
.ir-version-diff__group h5 { margin: 0 0 var(--xc-space-2); color: var(--xc-text-soft); font-size: var(--xc-fs-2xs); }
.ir-version-diff__group h5 span { color: var(--xc-text-mute); font-weight: var(--xc-fw-regular); }
.ir-version-diff__row { min-height: 36px; display: grid; grid-template-columns: minmax(150px, 1fr) minmax(80px, 120px) 24px minmax(80px, 120px) 72px; align-items: center; gap: var(--xc-space-2); font-size: var(--xc-fs-xs); }
.ir-version-diff__old { color: var(--xc-text-mute); text-align: right; }
.ir-version-diff__arrow { color: var(--xc-text-mute); text-align: center; }
.ir-version-diff__new { color: var(--xc-text-strong); }
.ir-version-diff__source { justify-self: end; padding: 2px 7px; border-radius: var(--xc-radius-full); font-size: var(--xc-fs-3xs); white-space: nowrap; }
.ir-version-diff__source.is-explicit { color: var(--xc-accent-blue); background: var(--xc-status-info-soft); }
.ir-version-diff__source.is-derived { color: var(--xc-status-warn); background: var(--xc-status-warn-soft); }
.ir-version-diff__empty { padding: var(--xc-space-5); color: var(--xc-text-mute); font-size: var(--xc-fs-xs); }
.ir-block { padding:var(--xc-space-7); }
.ir-block__title { display:flex; align-items:center; gap:var(--xc-space-2); font-size:var(--xc-fs-md); color:var(--xc-text-strong); font-weight:var(--xc-fw-semi); margin:0 0 var(--xc-space-5); }
.ir-block__title-icon { width:18px; height:18px; flex:0 0 auto; color:var(--xc-accent-blue); }
/* 收益环形(占 1/3) + 微债折线(占 2/3) 左右并排；窄屏回退为上下堆叠 */
.ir-result__charts { display:grid; grid-template-columns:1fr 2fr; gap:var(--xc-space-6); align-items:stretch; }
.ir-result__charts > * { min-width:0; }
@container (max-width: 900px) { .ir-result__charts { grid-template-columns:1fr; } }
.ir-result__warn { display:flex; flex-direction:column; gap:var(--xc-space-2); padding:0 var(--xc-space-6); font-size:var(--xc-fs-xs); color:var(--xc-status-warn); }
.ir-result__footer { display:flex; align-items:center; justify-content:space-between; gap:var(--xc-space-4); min-height:58px; padding:var(--xc-space-4) var(--xc-space-6); border-top:1px solid var(--xc-border-soft); background:var(--xc-surface-tinted); }
.ir-result__footer-actions { display:flex; align-items:center; gap:var(--xc-space-3); flex-shrink:0; }
.ir-result__footer-actions .ir-result__act:first-child svg { transform:translateY(-1px); }
.ir-result__report-hint { color:var(--xc-text-mute); font-size:var(--xc-fs-2xs); line-height:var(--xc-lh-normal); }
.ir-result__act { display:inline-flex; align-items:center; justify-content:center; gap:var(--xc-space-2); min-height:38px; flex:0 0 auto; padding:0 var(--xc-space-5); border:1px solid var(--xc-border-accent); border-radius:var(--xc-radius-sm); background:var(--xc-accent-blue-soft); color:var(--xc-accent-blue); font:inherit; font-size:var(--xc-fs-xs); font-weight:var(--xc-fw-medium); cursor:pointer; transition:border-color var(--xc-dur-fast),background var(--xc-dur-fast),color var(--xc-dur-fast),box-shadow var(--xc-dur-fast); }
.ir-result__act svg { width:16px; height:16px; }
.ir-result__act:hover:not(:disabled) { border-color:var(--xc-accent-blue); color:var(--xc-text-strong); box-shadow:var(--xc-glow-blue); }
.ir-result__act:focus-visible { outline:2px solid var(--xc-accent-blue); outline-offset:2px; }
.ir-result__act:disabled { border-color:var(--xc-border-soft); background:var(--xc-surface-control); color:var(--xc-text-mute); cursor:not-allowed; opacity:.72; box-shadow:none; }
@media (max-width:640px) { .ir-result__footer { align-items:stretch; flex-direction:column; } .ir-result__act { width:100%; } }
@container (max-width: 760px) {
  .ir-result__banner {
    height: 220px;
    align-items: flex-end;
    background-position: 60% center;
  }
  .ir-result__banner-mask {
    background: linear-gradient(180deg, rgba(3, 8, 22, 0.18) 0%, rgba(3, 8, 22, 0.14) 34%, rgba(3, 8, 22, 0.94) 100%);
  }
  .ir-result__banner-body { padding: var(--xc-space-5); }
  .ir-result__compare { flex-direction:column; align-items:flex-start; width:180px; }
  .ir-result__compare-wrap { width:100%; }
  .ir-version-diff__row { grid-template-columns:minmax(100px,1fr) 72px 18px 72px; }
  .ir-version-diff__source { grid-column:2 / -1; justify-self:start; }
}
@container (max-width: 480px) {
  .ir-result { gap: var(--xc-space-4); }
  .ir-result__banner-status { top: var(--xc-space-4); left: var(--xc-space-4); }
  .ir-result__banner-title { font-size: var(--xc-fs-h4); line-height: var(--xc-lh-snug); }
  .ir-result__compare { width: 100%; }
  .ir-report-module { margin-inline: var(--xc-space-4); border-radius: var(--xc-radius-md); }
  .ir-result__charts { gap: var(--xc-space-4); }
  .ir-result__warn { padding-inline: var(--xc-space-4); }
  .ir-result__footer { padding-inline: var(--xc-space-4); }
  .ir-result__footer-actions { width: 100%; flex-direction: column; }
}
</style>

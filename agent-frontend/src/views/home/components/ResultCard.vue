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
        <DisclaimerNotice variant="compact" />
        <button
          v-if="availableVersions.length"
          type="button"
          class="ir-result__comparison-toggle"
          :class="{ 'is-open': comparisonExpanded }"
          :aria-expanded="comparisonExpanded"
          :aria-controls="comparisonPanelId"
          @click="toggleComparison"
        >
          <span>{{ comparisonExpanded ? '收起版本对比' : '查看版本对比' }}</span>
          <ChevronDown :size="18" aria-hidden="true" />
        </button>
      </div>
    </div>

    <section
      v-if="comparisonExpanded && comparisonVersion"
      :id="comparisonPanelId"
      class="ir-report-module ir-version-diff"
    >
      <header class="ir-version-diff__head">
        <div class="ir-version-diff__heading">
          <h4>版本对比</h4>
          <span>当前版本 {{ version }}（固定）</span>
        </div>
        <label class="ir-result__compare">
          <span>对比基准</span>
          <div class="ir-result__compare-wrap">
            <select :value="comparisonVersion" @change="$emit('compare-version-change', $event.target.value)" aria-label="选择对比版本">
              <option v-for="item in availableVersions" :key="item.version" :value="item.version">
                {{ item.version }}{{ item.isPrevious ? ' · 上一版' : '' }}
              </option>
            </select>
            <ChevronDown class="ir-result__compare-chevron" :size="16" aria-hidden="true" />
          </div>
        </label>
      </header>
      <div v-if="comparisonLoading" class="ir-version-diff__empty" role="status">正在加载版本参数…</div>
      <div v-else-if="comparisonError || !comparisonInputsReady" class="ir-version-diff__empty" role="alert">
        {{ comparisonError || '版本参数尚未加载' }}
        <button type="button" class="ir-version-diff__retry" @click="$emit('comparison-open')">重新加载</button>
      </div>
      <template v-else>
      <div class="ir-version-diff__summary">{{ version }} 较 {{ comparisonVersion }} · {{ versionDiff.totalCount }} 项参数变化</div>
      <div v-if="versionDiff.totalCount" class="ir-version-diff__body">
        <div v-for="group in versionDiff.groups" :key="group.category" class="ir-version-diff__group">
          <h5>{{ group.label }} <span>{{ group.items.length }} 项</span></h5>
          <div v-for="item in group.items" :key="item.id" class="ir-version-diff__row">
            <span class="ir-version-diff__name">{{ item.label }}</span>
            <span class="ir-version-diff__change">
              <span class="ir-version-diff__old xc-num">{{ displayParam(item.oldValue) }}</span>
              <span class="ir-version-diff__arrow">→</span>
              <span class="ir-version-diff__new xc-num">{{ displayParam(item.newValue) }}</span>
            </span>
            <span class="ir-version-diff__source" :class="`is-${item.source}`">{{ item.source === 'explicit' ? '主动调整' : '联动更新' }}</span>
          </div>
        </div>
      </div>
      <div v-else class="ir-version-diff__empty">与 {{ comparisonVersion }} 相比，测算参数未发生变化</div>
      </template>
    </section>

    <section class="ir-report-module">
      <BasicInfoBlock :basic-info="result.basicInfo" />
    </section>
    <section class="ir-report-module">
      <FinancialBlock
        :financial="result.financial"
        :comparison-financial="comparisonExpanded ? comparisonResult?.financial : null"
        :comparison-version="comparisonExpanded ? comparisonVersion : ''"
      />
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
      :seed-input="seedInputForAdjustment"
      :comparison-input="comparisonInput"
      :station-options="stationOptions"
      :station-loading="stationLoading"
      :station-has-more="stationHasMore"
      :station-error="stationError"
      :version="version"
      :responding="responding"
      :loading="adjustmentLoading"
      :load-error="adjustmentError"
      :advanced-overrides="advancedOverrides"
      :advanced-override-count="advancedOverrideCount"
      :advanced-validation-error="advancedValidationError"
      @recalculate="$emit('recalculate', $event)"
      @open-request="emit('adjustment-open')"
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

    <div class="ir-result__footer">
      <span v-if="hasPendingParameterChanges" id="ir-result-report-hint" class="ir-result__report-hint">
        参数修改尚未形成新版本，请先重新测算
      </span>
      <span v-else-if="report?.status === 'completed'" class="ir-result__report-hint">正式投资报告已生成，可从报告记录查看</span>
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
          v-if="report?.status === 'completed'"
          type="button"
          class="ir-result__act"
          data-testid="report-btn"
          aria-label="查看正式投资报告"
          @click="$emit('view-report', report.reportId)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
            <path d="M6 2.75h8l4 4V21.25H6z" stroke-linejoin="round" />
            <path d="M14 2.75v4h4M9 11h6M9 14.5h6M9 18h4" stroke-linecap="round" />
          </svg>
          查看报告
        </button>
        <button
          v-else
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
import DisclaimerNotice from '@/components/DisclaimerNotice.vue'
import welcomeBackgroundSrc from '@/assets/home-welcome-background.png'
import { resolveVariant, roundToStep } from '@/utils/paramAdjust'
import { buildResultTitle } from '@/utils/projectTitle'
import { ChevronDown } from '@lucide/vue'
import { diffVersionInputs } from '@/utils/versionComparison'

const props = defineProps({
  result: { type: Object, required: true },
  version: { type: String, default: '' },
  calculatedAt: { type: String, default: '' },
  seedInput: { type: Object, default: null },
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
  comparisonLoading: { type: Boolean, default: false },
  comparisonError: { type: String, default: '' },
  adjustmentLoading: { type: Boolean, default: false },
  adjustmentError: { type: String, default: '' },
  availableVersions: { type: Array, default: () => [] },
  changeMeta: { type: Object, default: () => ({}) },
  adjustable: { type: Boolean, default: true },
  conversationId: { type: String, default: '' },
  taskId: { type: [Number, String], default: null },
})
const emit = defineEmits([
  'recalculate',
  'generate-report',
  'view-report',
  'compare-version-change',
  'comparison-open',
  'adjustment-open',
  'station-open',
  'station-search',
  'station-load-more',
])
const advanced = computed(() => props.result.advanced || { donut: {}, debtServiceCoverage: {} })
const warnings = computed(() => props.result.warnings || [])
const comparisonInputsReady = computed(() => Boolean(props.seedInput && props.displayComparisonInput))
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

const seedInputForAdjustment = computed(() => props.seedInput)

const bannerTitle = computed(() => buildResultTitle(
  props.result.basicInfo?.province ?? props.seedInput?.province,
  props.result.basicInfo?.nodeName ?? props.seedInput?.node_name,
  props.result.basicInfo?.city ?? props.seedInput?.city,
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
const comparisonExpanded = ref(false)
function toggleComparison() {
  comparisonExpanded.value = !comparisonExpanded.value
  if (comparisonExpanded.value) emit('comparison-open')
}
const comparisonPanelId = computed(() => `ir-version-comparison-${String(props.taskId ?? (props.version || 'result')).replace(/[^a-zA-Z0-9_-]/g, '-')}`)
const ADVANCED_IDS = new Set([
  'operation_years', 'mid_long_charge_avg', 'mid_long_discharge_avg',
  'strategy_achievement_rate', 'capacity_achievement_rate',
  'battery_replace_cost', 'maint_cost', 'opex_cost',
])
const advancedOverrideCount = computed(() => {
  const draftOperationYears = advancedOverrides.value.operation_years
    ?? props.seedInput?.operation_years
    ?? 15
  return props.paramDict.reduce((count, spec) => {
    if (!ADVANCED_IDS.has(spec.id) || spec.g !== 1) return count
    // 控件形态/步长/默认值按草稿中的运营期解析 variants。
    const resolved = resolveVariant(spec, draftOperationYears)
    if (!['slider', 'dynamic_slider', 'select'].includes(resolved.control)) return count
    if (!(spec.id in advancedOverrides.value)) return count
    const draft = normalizeAdvancedValue(advancedOverrides.value[spec.id], resolved.step)
    const baselineValue = spec.variants
      ? resolved.default
      : spec.id in (props.seedInput || {})
        ? props.seedInput[spec.id]
        : resolved.default
    const baseline = normalizeAdvancedValue(baselineValue, resolved.step)
    return draft === baseline ? count : count + 1
  }, 0)
})
const hasPendingParameterChanges = computed(() => regularParametersDirty.value || advancedOverrideCount.value > 0 || advancedValidationError.value)

// 高级参数仅是当前结果卡的未提交草稿：新版本切换到其他结果时自动清空。
// 输入懒加载会让 seedInput 从 null 变为完整快照，但不应收起已经打开的版本对比面板。
watch(() => props.version, () => {
  advancedOverrides.value = {}
  advancedValidationError.value = false
  regularParametersDirty.value = false
  comparisonExpanded.value = false
})
watch(() => props.seedInput, () => {
  advancedOverrides.value = {}
  advancedValidationError.value = false
  regularParametersDirty.value = false
}, { deep: true })
watch(() => props.availableVersions.length, (count) => {
  if (!count) comparisonExpanded.value = false
})
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
.ir-result__ver { font-size:var(--xc-fs-xs); color:var(--xc-text-inverse); background:var(--xc-accent-blue); border-radius:var(--xc-radius-full); padding:2px var(--xc-space-3); line-height:var(--xc-lh-normal); }
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
.ir-result__comparison-toggle {
  position: relative;
  z-index: 1;
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--xc-space-2);
  min-height: 44px;
  margin-top: var(--xc-space-3);
  padding: 0 var(--xc-space-5);
  border: 1px solid var(--xc-border-accent);
  border-radius: var(--xc-radius-sm);
  background: rgba(3, 8, 22, 0.54);
  color: var(--xc-text-default);
  font: inherit;
  font-size: var(--xc-fs-sm);
  font-weight: var(--xc-fw-semi);
  cursor: pointer;
  transition: border-color var(--xc-dur-fast) var(--xc-ease-out),
              background-color var(--xc-dur-fast) var(--xc-ease-out),
              color var(--xc-dur-fast) var(--xc-ease-out);
}
.ir-result__comparison-toggle svg {
  flex: 0 0 auto;
  transition: transform var(--xc-dur-base) var(--xc-ease-out);
}
.ir-result__comparison-toggle:hover,
.ir-result__comparison-toggle.is-open {
  border-color: var(--xc-accent-blue);
  background: var(--xc-accent-blue-soft);
  color: var(--xc-text-strong);
}
.ir-result__comparison-toggle.is-open svg { transform: rotate(180deg); }
.ir-result__comparison-toggle:focus-visible { outline: 2px solid var(--xc-accent-blue); outline-offset: 2px; }
.ir-result__compare {
  display: flex;
  align-items: center;
  gap: var(--xc-space-3);
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-sm);
  font-weight: var(--xc-fw-medium);
  white-space: nowrap;
}
.ir-result__compare > span { flex-shrink: 0; }
.ir-result__compare-wrap {
  position: relative;
  display: flex;
  align-items: center;
  min-width: 176px;
}
.ir-result__compare-wrap select {
  width: 100%;
  min-height: 44px;
  padding: 0 var(--xc-space-7) 0 var(--xc-space-4);
  border: 1px solid var(--xc-border-accent);
  border-radius: var(--xc-radius-sm);
  outline: none;
  background: var(--xc-surface-control);
  color: var(--xc-text-strong);
  font-family: var(--xc-font-zh);
  font-size: var(--xc-fs-sm);
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
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: var(--xc-text-soft);
}
@media (prefers-reduced-motion: reduce) {
  .ir-result__comparison-toggle,
  .ir-result__comparison-toggle svg,
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
.ir-version-diff__head {
  min-height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--xc-space-5);
  padding: var(--xc-space-4) var(--xc-space-5);
  border-bottom: 1px solid var(--xc-border-soft);
}
.ir-version-diff__heading { display: flex; flex-direction: column; gap: var(--xc-space-1); min-width: 0; }
.ir-version-diff__heading h4 { margin: 0; color: var(--xc-text-strong); font-size: var(--xc-fs-h4); line-height: var(--xc-lh-snug); }
.ir-version-diff__heading span { color: var(--xc-text-soft); font-size: var(--xc-fs-sm); line-height: var(--xc-lh-normal); }
.ir-version-diff__summary {
  padding: var(--xc-space-4) var(--xc-space-5) 0;
  color: var(--xc-text-default);
  font-size: var(--xc-fs-sm);
  font-weight: var(--xc-fw-medium);
  line-height: var(--xc-lh-normal);
}
.ir-version-diff__body { padding: var(--xc-space-2) var(--xc-space-5) var(--xc-space-5); }
.ir-version-diff__group { padding-top: var(--xc-space-4); }
.ir-version-diff__group + .ir-version-diff__group { margin-top: var(--xc-space-3); border-top: 1px solid var(--xc-border-soft); }
.ir-version-diff__group h5 { margin: 0 0 var(--xc-space-3); color: var(--xc-text-default); font-size: var(--xc-fs-sm); line-height: var(--xc-lh-normal); }
.ir-version-diff__group h5 span { color: var(--xc-text-soft); font-weight: var(--xc-fw-regular); }
.ir-version-diff__row { min-height: 44px; display: grid; grid-template-columns: minmax(140px, 240px) minmax(240px, 320px) 96px; width: 100%; align-items: center; column-gap: var(--xc-space-6); font-size: var(--xc-fs-sm); line-height: var(--xc-lh-normal); }
.ir-version-diff__name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--xc-text-default); }
.ir-version-diff__change { min-width: 0; display: grid; grid-template-columns: minmax(88px, 1fr) 24px minmax(88px, 1fr); align-items: center; }
.ir-version-diff__old { min-width: 0; color: var(--xc-text-soft); text-align: right; white-space: nowrap; }
.ir-version-diff__arrow { color: var(--xc-text-soft); text-align: center; }
.ir-version-diff__new { min-width: 0; color: var(--xc-text-strong); white-space: nowrap; }
.ir-version-diff__source { justify-self: end; padding: 3px 8px; border-radius: var(--xc-radius-full); font-size: var(--xc-fs-xs); line-height: var(--xc-lh-normal); white-space: nowrap; }
.ir-version-diff__source.is-explicit { color: var(--xc-accent-blue); background: var(--xc-status-info-soft); }
.ir-version-diff__source.is-derived { color: var(--xc-status-warn); background: var(--xc-status-warn-soft); }
.ir-version-diff__empty { padding: var(--xc-space-5); color: var(--xc-text-soft); font-size: var(--xc-fs-sm); line-height: var(--xc-lh-normal); }
.ir-version-diff__retry { min-height:36px; margin-left:var(--xc-space-3); padding:0 var(--xc-space-3); border:1px solid var(--xc-border-soft); border-radius:var(--xc-radius-sm); background:transparent; color:var(--xc-accent-blue); cursor:pointer; }
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
.ir-result__report-hint { color:var(--xc-text-soft); font-size:var(--xc-fs-xs); line-height:var(--xc-lh-normal); }
.ir-result__act { display:inline-flex; align-items:center; justify-content:center; gap:var(--xc-space-2); min-height:44px; flex:0 0 auto; padding:0 var(--xc-space-5); border:1px solid var(--xc-border-accent); border-radius:var(--xc-radius-sm); background:var(--xc-accent-blue-soft); color:var(--xc-accent-blue); font:inherit; font-size:var(--xc-fs-xs); font-weight:var(--xc-fw-medium); cursor:pointer; transition:border-color var(--xc-dur-fast),background var(--xc-dur-fast),color var(--xc-dur-fast),box-shadow var(--xc-dur-fast); }
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
  .ir-result__comparison-toggle { width: 100%; }
  .ir-version-diff__head { align-items: flex-start; flex-direction: column; }
  .ir-result__compare { width: 100%; }
  .ir-result__compare-wrap { flex: 1 1 auto; min-width: 0; }
  .ir-version-diff__row { grid-template-columns:minmax(100px,180px) minmax(220px,300px) 80px; column-gap:var(--xc-space-4); }
  .ir-version-diff__change { grid-template-columns:minmax(76px,1fr) 20px minmax(76px,1fr); }
}
@container (max-width: 480px) {
  .ir-result { gap: var(--xc-space-4); }
  .ir-result__banner-status { top: var(--xc-space-4); left: var(--xc-space-4); }
  .ir-result__banner-title { font-size: var(--xc-fs-h4); line-height: var(--xc-lh-snug); }
  .ir-result__compare { width: 100%; }
  .ir-report-module { margin-inline: var(--xc-space-4); border-radius: var(--xc-radius-md); }
  .ir-version-diff__row { grid-template-columns:minmax(0,1fr) auto; row-gap:var(--xc-space-2); column-gap:var(--xc-space-4); padding-block:var(--xc-space-2); }
  .ir-version-diff__source { grid-column:2; grid-row:1; justify-self:end; }
  .ir-version-diff__change { grid-column:1 / -1; grid-row:2; width:min(100%,280px); grid-template-columns:minmax(56px,1fr) 20px minmax(56px,1fr); }
  .ir-result__charts { gap: var(--xc-space-4); }
  .ir-result__warn { padding-inline: var(--xc-space-4); }
  .ir-result__footer { padding-inline: var(--xc-space-4); }
  .ir-result__footer-actions { width: 100%; flex-direction: column; }
}
</style>

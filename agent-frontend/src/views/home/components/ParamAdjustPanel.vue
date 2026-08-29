<template>
  <div class="ir-adjust">
    <div class="ir-adjust__header">
      <button
        class="ir-adjust__toggle"
        type="button"
        :disabled="responding"
        :aria-expanded="expanded"
        aria-controls="ir-adjust-panel-body"
        @click="expanded = !expanded"
      >
        <span class="ir-adjust__heading-copy">
          <strong>调整参数并重新测算</strong>
          <small>可修改项目、财务、收益及运营参数</small>
        </span>
        <span class="ir-adjust__toggle-action">
          {{ expanded ? '收起' : '调整参数' }}
          <ChevronDown class="ir-adjust__caret" :class="{ 'is-open': expanded }" aria-hidden="true" />
        </span>
      </button>
    </div>

    <div v-if="!expanded && hasPendingChanges" class="ir-adjust__pending-bar">
      <span class="ir-adjust__pending-copy" aria-live="polite">{{ pendingChangesText }}</span>
      <div class="ir-adjust__pending-actions">
        <button class="ir-adjust__reset" type="button" :disabled="responding" @click="discardChanges">
          放弃全部修改
        </button>
        <button class="ir-adjust__submit" type="button" :disabled="responding || !hasPendingChanges || hasValidationErrors" @click="onSubmit">
          {{ responding ? '测算中…' : '重新测算' }}
        </button>
      </div>
    </div>

    <div v-if="expanded" id="ir-adjust-panel-body" class="ir-adjust__body">
      <div class="ir-adjust__tabs" role="tablist" aria-label="参数类型">
        <button type="button" role="tab" :aria-selected="activeTab === 'common'" :class="{ 'is-active': activeTab === 'common' }" @click="activeTab = 'common'">
          常用参数
          <span v-if="localChangeCount > 0" class="ir-adjust__draft-count xc-num">{{ localChangeCount }}</span>
        </button>
        <button type="button" role="tab" :aria-selected="activeTab === 'advanced'" :class="{ 'is-active': activeTab === 'advanced' }" @click="activeTab = 'advanced'">
          高级参数
          <span v-if="advancedOverrideCount > 0" class="ir-adjust__draft-count xc-num">{{ advancedOverrideCount }}</span>
        </button>
      </div>
      <div v-show="activeTab === 'common'" class="ir-adjust__tab-panel" role="tabpanel">
      <div class="ir-adjust__tab-toolbar">
        <span>{{ localChangeCount > 0 ? `已修改 ${localChangeCount} 项常用参数` : '常用参数暂无修改' }}</span>
        <button class="ir-adjust__scope-reset" type="button" :disabled="responding || !hasLocalChanges" @click="resetCommonChanges">
          撤销常用参数修改
        </button>
      </div>
      <section
        v-for="group in zoneGroups"
        :key="group.zone"
        class="ir-adjust__zone"
        :class="`ir-adjust__zone--${group.zone}`"
      >
        <h5 class="ir-adjust__zone-title">
          <svg class="ir-adjust__zone-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true" v-html="zoneIcon(group.zone)" />
          {{ group.label }}
        </h5>
        <div class="ir-adjust__rows">
          <div
            v-for="(row, idx) in rowsFor(group)"
            :key="idx"
            class="ir-adjust__row"
            :class="{
              'ir-adjust__row--single': row.length === 1 && group.zone !== 'project_definition',
              'ir-adjust__row--project': group.zone === 'project_definition',
            }"
          >
            <div
              v-for="spec in row"
              :key="spec.id"
              class="ir-adjust__field"
              :class="{ 'ir-adjust__project-item': group.zone === 'project_definition' }"
            >
              <span v-if="group.zone === 'project_definition'" class="ir-adjust__project-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" v-html="projectFieldIcon(spec.id)" />
              </span>
              <div class="ir-adjust__field-content">
              <!-- 河南按城市定位项目，不展示节点搜索；其他省份保持节点搜索。 -->
              <template v-if="spec.id === 'node_name' && isHenan">
                <span class="ir-adjust__label">{{ spec.cn || spec.id }}</span>
                <span class="ir-adjust__pending">河南项目按城市测算</span>
              </template>
              <!-- 节点候选按需从 ir_spot_station 远程搜索，历史已选节点始终可见。 -->
              <template v-else-if="spec.id === 'node_name'">
                <span class="ir-adjust__label">{{ spec.cn || spec.id }}</span>
                <el-popover
                  v-model:visible="nodeEditorOpen"
                  placement="bottom-start"
                  trigger="click"
                  :show-arrow="false"
                  popper-class="ir-adjust__node-editor"
                >
                  <template #reference>
                    <button
                      ref="nodeTrigger"
                      class="ir-adjust__node-trigger"
                      type="button"
                      :disabled="responding"
                      :aria-expanded="nodeEditorOpen"
                      :aria-label="`更改节点名称，当前为 ${localValues.node_name || '未选择'}`"
                    >
                      <span class="ir-adjust__node-name-tooltip">
                        <el-tooltip
                          :content="localValues.node_name || ''"
                          placement="top"
                          :disabled="!localValues.node_name"
                        >
                          <span class="ir-adjust__node-name" :title="localValues.node_name || ''">
                            {{ localValues.node_name || '选择节点' }}
                          </span>
                        </el-tooltip>
                      </span>
                      <span class="ir-adjust__node-action" aria-hidden="true">更改</span>
                    </button>
                  </template>
                  <div class="ir-adjust__node-editor-body" @keydown.esc.stop.prevent="closeNodeEditor(true)">
                    <el-select
                      v-if="nodeEditorOpen"
                      ref="nodeSelect"
                      v-model="localValues.node_name"
                      class="ir-adjust__node-select"
                      filterable
                      remote
                      :remote-method="searchNodes"
                      :loading="stationLoading && props.stationOptions.length === 0"
                      :suffix-icon="null"
                      :teleported="false"
                      placeholder="搜索或选择节点"
                      :no-data-text="stationError || '暂无节点'"
                      no-match-text="未找到匹配节点"
                      :popper-class="nodePopperClass"
                      @popup-scroll="handleNodePopupScroll"
                      @change="selectNode"
                    >
                      <template #footer>
                        <div v-if="stationLoading && props.stationOptions.length" class="ir-adjust__node-load-more" role="status">
                          加载更多节点…
                        </div>
                      </template>
                      <el-option v-for="station in nodeOptions" :key="station" :label="station" :value="station" />
                    </el-select>
                  </div>
                </el-popover>
              </template>

              <!-- 河南项目城市可编辑，作为城市定位提交；其他省份不显示该字段。 -->
              <template v-else-if="spec.id === 'city' && isHenan">
                <span class="ir-adjust__label">{{ spec.cn || '所在城市' }}</span>
                <input v-model.trim="localValues.city" class="ir-adjust__text" :disabled="responding" placeholder="请输入所在城市" />
              </template>
              <template v-else-if="isLocked(spec)">
                <span class="ir-adjust__label">{{ spec.cn || spec.id }}</span>
                <span class="ir-adjust__ro xc-num">
                  {{ formatSpecValue(spec, localValues[spec.id]) }}<template v-if="displayUnit(spec)"> {{ displayUnit(spec) }}</template>
                </span>
              </template>

              <!-- 数字输入（装机功率/装机容量等） -->
              <template v-else-if="spec.control === 'number'">
                <span class="ir-adjust__label">{{ spec.cn || spec.id }}</span>
                <span class="ir-adjust__number-value">
                  <input
                    :value="numberInputValues[spec.id]"
                    type="number"
                    class="ir-adjust__number"
                    :class="{ 'is-invalid': validationErrors[spec.id] }"
                    :style="{ width: projectNumberWidth(numberInputValues[spec.id]) }"
                    :disabled="responding"
                    :aria-invalid="Boolean(validationErrors[spec.id])"
                    :aria-describedby="validationErrors[spec.id] ? `ps-error-${spec.id}` : undefined"
                    @input="onNumberTextInput(spec, $event)"
                    @blur="validateNumberInput(spec)"
                    @keydown.enter.prevent="$event.currentTarget.blur()"
                  />
                  <small v-if="displayUnit(spec)">{{ displayUnit(spec) }}</small>
                </span>
                <div
                  v-if="validationErrors[spec.id]"
                  :id="`ps-error-${spec.id}`"
                  class="ps-validation ps-validation--project"
                  role="alert"
                >
                  <CircleAlert aria-hidden="true" />
                  <span>{{ validationErrors[spec.id] }}</span>
                </div>
              </template>

              <!-- 固定范围 / 基准值±100% 动态滑块 -->
              <template v-else-if="spec.control === 'slider' || spec.control === 'dynamic_slider'">
                <div v-if="rangeOf(spec)" class="pslider ps-rail">
                  <span class="ps-label">{{ spec.cn || spec.id }}</span>
                  <span class="ps-value-area">
                    <span v-if="activeSliderHint === spec.id" class="ps-input-hint" role="status">
                      点击数值可精确输入
                    </span>
                    <span class="ps-val xc-num">
                      <input
                        :value="sliderInputValues[spec.id]"
                        type="number"
                        :min="rangeOf(spec).min" :max="rangeOf(spec).max" :step="spec.step"
                        class="ir-adjust__number ps-val-input"
                        :class="{ 'is-invalid': validationErrors[spec.id] }"
                        :disabled="responding"
                        :aria-invalid="Boolean(validationErrors[spec.id])"
                        :aria-describedby="validationErrors[spec.id] ? `ps-error-${spec.id}` : undefined"
                        @focus="hideSliderHint(spec.id)"
                        @input="onSliderTextInput(spec, $event)"
                        @blur="validateSliderInput(spec)"
                        @keydown.enter.prevent="$event.currentTarget.blur()"
                      />
                      <small v-if="displayUnit(spec)">{{ displayUnit(spec) }}</small>
                    </span>
                  </span>
                  <div class="ps-track">
                    <input
                      v-model.number="localValues[spec.id]"
                      type="range"
                      :min="rangeOf(spec).min" :max="rangeOf(spec).max" :step="spec.step"
                      class="ir-adjust__slider"
                      :disabled="responding"
                      :style="{ '--pct': pctOf(spec) + '%' }"
                      @pointerenter="showSliderHint(spec.id)"
                      @pointerleave="hideSliderHint(spec.id)"
                      @pointerdown="onSliderPointerDown(spec.id)"
                      @focus="onSliderFocus(spec.id)"
                      @blur="hideSliderHint(spec.id)"
                      @input="onSliderInput(spec)"
                    />
                    <span
                      v-if="frozenMarkerPctOf(spec) !== null"
                      class="ps-mark"
                      :style="{ '--mark-pct': `${frozenMarkerPctOf(spec)}%` }"
                      aria-hidden="true"
                    >{{ formatRangeEndpoint(spec, frozenBaselineOf(spec)) }}</span>
                    <div class="ps-range-labels xc-num">
                      <span>{{ formatRangeEndpoint(spec, rangeOf(spec).min) }}</span>
                      <span>{{ formatRangeEndpoint(spec, rangeOf(spec).max) }}</span>
                    </div>
                  </div>
                  <div class="ps-foot">
                    <span v-if="deltaOf(spec)" class="ps-delta" :class="deltaOf(spec).dir">{{ deltaOf(spec).text }}</span>
                  </div>
                  <div
                    v-if="validationErrors[spec.id]"
                    :id="`ps-error-${spec.id}`"
                    class="ps-validation"
                    role="alert"
                  >
                    <CircleAlert aria-hidden="true" />
                    <span>{{ validationErrors[spec.id] }}</span>
                  </div>
                </div>
                <span v-else class="ir-adjust__pending">数据待完善</span>
              </template>
              </div>
            </div>
          </div>
        </div>
      </section>
      </div>

      <div v-show="activeTab === 'advanced'" class="ir-adjust__tab-panel ir-adjust__tab-panel--advanced" role="tabpanel">
        <slot name="advanced" />
      </div>

      <div class="ir-adjust__footer">
        <span v-if="hasPendingChanges" class="ir-adjust__draft-note">{{ pendingChangesText }}</span>
        <button
          class="ir-adjust__reset"
          type="button"
          :disabled="responding || !hasPendingChanges"
          @click="discardChanges"
        >放弃全部修改</button>
        <button class="ir-adjust__submit" type="button" :disabled="responding || !hasPendingChanges || hasValidationErrors" @click="onSubmit">
          {{ responding ? '测算中…' : '重新测算' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, getCurrentInstance, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { ElOption, ElPopover, ElSelect, ElTooltip } from 'element-plus'
import { ChevronDown, CircleAlert } from '@lucide/vue'
import {
  buildOverrides,
  comparableValue,
  decimalsForStep,
  dynamicRange,
  frozenBaseline,
  frozenMarkerPct,
  groupByZone,
  isFieldLocked,
  numericInputError,
  roundToStep,
  validateNumericInput,
} from '@/utils/paramAdjust'
import { formatNumber } from '@/utils/formatNumber'

const props = defineProps({
  paramDict: { type: Array, default: () => [] },
  switches: { type: Object, default: () => ({}) },
  seedInput: { type: Object, default: () => ({}) },
  comparisonInput: { type: Object, default: null },
  stationOptions: { type: Array, default: () => [] },
  stationLoading: { type: Boolean, default: false },
  stationHasMore: { type: Boolean, default: false },
  stationError: { type: String, default: '' },
  advancedOverrides: { type: Object, default: () => ({}) },
  advancedOverrideCount: { type: Number, default: 0 },
  advancedValidationError: { type: Boolean, default: false },
  version: { type: String, default: '' },
  responding: { type: Boolean, default: false },
})
const emit = defineEmits([
  'recalculate',
  'dirty-change',
  'discard-all-changes',
  'station-open',
  'station-search',
  'station-load-more',
])

const expanded = ref(false)
const activeTab = ref('common')
const nodeEditorOpen = ref(false)
const nodeTrigger = ref(null)
const nodeSelect = ref(null)
const nodePopperClass = `ir-adjust__node-popper ir-adjust__node-popper--${getCurrentInstance().uid}`
const localValues = reactive({})
const numberInputValues = reactive({})
const sliderInputValues = reactive({})
const validationErrors = reactive({})
const activeSliderHint = ref(null)
let sliderHintTimer = null
let suppressedSliderFocus = null
let nodeSearchTimer = null

const PROJECT_ORDER = ['province', 'city', 'node_name', 'power_mw', 'capacity_mwh']
const isHenan = computed(() => String(localValues.province || props.seedInput.province || '').trim() === '河南')
// 每个分区的行布局：一行一个 id = 该项独占半宽一行；一行多个 id = 并排共享一行。
// operation_years 不在任何分区的行布局里出现——即便后端字典仍返回该字段，也不会被渲染（见 zoneGroups 的过滤）。
const FINANCIAL_ROWS = [['epc_unit_price'], ['loan_rate', 'loan_years']]
const REVENUE_ROWS = [
  ['spot_charge_avg', 'spot_discharge_avg'],
  ['daily_cycles'],
  ['mid_long_energy_revenue_first_year_tax'],
  ['frequency_first_year_revenue'],
  ['intervention_first_year_revenue'],
  ['lease_unit_price', 'lease_achievement_rate'],
]
const ZONE_ROWS = {
  financial_boundary: FINANCIAL_ROWS,
  revenue_boundary: REVENUE_ROWS,
}
const ZONE_ICONS = {
  project_definition: '<path d="M4 20V9l8-5 8 5v11" stroke-linejoin="round"/><path d="M9 20v-6h6v6M8 10h.01M16 10h.01" stroke-linecap="round"/>',
  financial_boundary: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2" stroke-linecap="round" stroke-linejoin="round"/>',
  revenue_boundary: '<path d="M4 18 9 13l4 3 7-9" stroke-linecap="round" stroke-linejoin="round"/><path d="M15 7h5v5" stroke-linecap="round" stroke-linejoin="round"/>',
}
const PROJECT_FIELD_ICONS = {
  province: '<path d="M12 21s7-6.1 7-12a7 7 0 1 0-14 0c0 5.9 7 12 7 12Z"/><circle cx="12" cy="9" r="2.3"/>',
  node_name: '<circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="m8.3 11 7.4-4M8.3 13l7.4 4" stroke-linecap="round"/>',
  power_mw: '<path d="M13 2 4 14h7l-1 8 9-12h-7z" stroke-linejoin="round" stroke-linecap="round"/>',
  capacity_mwh: '<rect x="3" y="7" width="16" height="10" rx="2"/><path d="M21 10v4M7 10v4M11 10v4M15 10v4" stroke-linecap="round"/>',
}
const DROPPED_FIELDS = new Set([
  'operation_years',
  'battery_replace_cost',
  'maint_cost',
  'opex_cost',
  'strategy_achievement_rate',
  'capacity_achievement_rate',
  'mid_long_charge_avg',
  'mid_long_discharge_avg',
])

function resetLocalValues() {
  nodeEditorOpen.value = false
  Object.keys(localValues).forEach((k) => delete localValues[k])
  Object.keys(numberInputValues).forEach((k) => delete numberInputValues[k])
  Object.keys(sliderInputValues).forEach((k) => delete sliderInputValues[k])
  Object.keys(validationErrors).forEach((k) => delete validationErrors[k])
  for (const spec of props.paramDict) {
    const value = spec.id in props.seedInput ? props.seedInput[spec.id] : spec.default
    localValues[spec.id] = value
    if (spec.control === 'number') numberInputValues[spec.id] = value ?? ''
    if (spec.control === 'slider' || spec.control === 'dynamic_slider') {
      sliderInputValues[spec.id] = typeof value === 'number' && spec.step
        ? roundToStep(value, spec.step)
        : value ?? ''
    }
  }
  const city = props.seedInput.city
  if (city !== undefined) localValues.city = city
}
watch(() => props.seedInput, resetLocalValues, { immediate: true })
watch(nodeEditorOpen, (open, wasOpen) => {
  if (open && !wasOpen) focusNodeEditor()
})
watch(() => props.responding, (responding) => {
  if (responding) {
    nodeEditorOpen.value = false
    hideSliderHint()
  }
})
onBeforeUnmount(() => {
  clearTimeout(sliderHintTimer)
  clearTimeout(nodeSearchTimer)
})

const nodeOptions = computed(() => [...new Set([
  localValues.node_name,
  ...props.stationOptions,
].filter(Boolean))])

async function focusNodeEditor() {
  emit('station-open', {
    province: localValues.province || props.seedInput.province,
    selectedNode: localValues.node_name || null,
  })
  await nextTick()
  nodeSelect.value?.focus?.()
}
function searchNodes(keyword) {
  clearTimeout(nodeSearchTimer)
  nodeSearchTimer = setTimeout(() => {
    emit('station-search', {
      province: localValues.province || props.seedInput.province,
      keyword,
      selectedNode: localValues.node_name || null,
    })
  }, 300)
}
function handleNodePopupScroll(event) {
  if (!props.stationHasMore || props.stationLoading) return
  const eventTarget = event?.target
  const scrollContainer = eventTarget && typeof eventTarget === 'object'
    && 'clientHeight' in eventTarget && 'scrollHeight' in eventTarget
    ? eventTarget
    : document.querySelector(`.${nodePopperClass.split(' ').at(-1)} .el-select-dropdown__wrap`)
  if (!scrollContainer) return
  const eventScrollTop = Number(event?.scrollTop)
  const scrollTop = Number.isFinite(eventScrollTop) ? eventScrollTop : scrollContainer.scrollTop
  if (scrollTop + scrollContainer.clientHeight < scrollContainer.scrollHeight - 24) return
  emit('station-load-more', { selectedNode: localValues.node_name || null })
}
async function closeNodeEditor(restoreFocus = false) {
  nodeEditorOpen.value = false
  if (restoreFocus) {
    await nextTick()
    const trigger = nodeTrigger.value?.$el || nodeTrigger.value
    if (typeof trigger?.focus === 'function') trigger.focus()
  }
}
function selectNode() {
  closeNodeEditor(true)
}

const zoneGroups = computed(() => groupByZone(props.paramDict, props.switches)
  .map((group) => {
    let items = group.items.filter((spec) => !DROPPED_FIELDS.has(spec.id))
    if (group.zone === 'project_definition') {
      if (isHenan.value) {
        items = items.filter((spec) => spec.id !== 'node_name')
        if (!items.some((spec) => spec.id === 'city')) {
          items.push({ id: 'city', cn: '所在城市', control: 'text', zone: 'project_definition', default: '' })
        }
      } else {
        items = items.filter((spec) => spec.id !== 'city')
      }
      items = [...items].sort((a, b) => PROJECT_ORDER.indexOf(a.id) - PROJECT_ORDER.indexOf(b.id))
    }
    return { ...group, label: group.zone === 'project_definition' ? '项目信息' : group.label, items }
  })
  .filter((group) => group.items.length))
const localChangeCount = computed(() => zoneGroups.value.reduce((count, group) => count + group.items.reduce((groupCount, spec) => {
  if (isLocked(spec)) return groupCount
  const baseline = spec.id in props.seedInput ? props.seedInput[spec.id] : spec.default
  return comparableValue(localValues[spec.id], spec.step) !== comparableValue(baseline, spec.step)
    ? groupCount + 1
    : groupCount
}, 0), 0))
const hasLocalChanges = computed(() => localChangeCount.value > 0)
const hasPendingChanges = computed(() => hasLocalChanges.value || props.advancedOverrideCount > 0)
const hasValidationErrors = computed(() => Object.values(validationErrors).some(Boolean) || props.advancedValidationError)
const pendingChangesText = computed(() => {
  if (hasLocalChanges.value && props.advancedOverrideCount > 0) {
    return `常用参数和 ${props.advancedOverrideCount} 项高级参数已修改，重新测算后生效`
  }
  if (hasLocalChanges.value) return '常用参数已修改，重新测算后生效'
  return `${props.advancedOverrideCount} 项高级参数已修改，重新测算后生效`
})
watch(hasLocalChanges, (dirty) => emit('dirty-change', dirty), { immediate: true })

function zoneIcon(zone) { return ZONE_ICONS[zone] || ZONE_ICONS.financial_boundary }
function projectFieldIcon(id) { return PROJECT_FIELD_ICONS[id] || PROJECT_FIELD_ICONS.node_name }

// 项目信息整区就是"一行"，卡片按内容自适应宽度、由 CSS space-between 均匀分布；
// 金融/收益边界按 ZONE_ROWS 固定行布局分组，行内 id 若因开关关闭而缺失则整行跳过。
function rowsFor(group) {
  if (group.zone === 'project_definition') return group.items.length ? [group.items] : []
  const layout = ZONE_ROWS[group.zone]
  if (!layout) return group.items.map((item) => [item])
  const byId = new Map(group.items.map((item) => [item.id, item]))
  return layout
    .map((ids) => ids.map((id) => byId.get(id)).filter(Boolean))
    .filter((row) => row.length)
}

function isLocked(spec) { return isFieldLocked(spec) }
function dynamicRangeOf(spec) { return dynamicRange(props.seedInput[spec.id], spec.step) }
function rangeOf(spec) {
  if (spec.control === 'slider') return { min: spec.min, max: spec.max }
  if (spec.control === 'dynamic_slider') return dynamicRangeOf(spec)
  return null
}
function pctOf(spec) {
  const range = rangeOf(spec)
  const value = localValues[spec.id]
  if (!range || typeof value !== 'number' || !Number.isFinite(value) || range.max === range.min) return 0
  return Math.min(100, Math.max(0, ((value - range.min) / (range.max - range.min)) * 100))
}
function deltaOf(spec) {
  const historicalBaseline = props.comparisonInput?.[spec.id]
  const baseline = typeof historicalBaseline === 'number'
    ? historicalBaseline
    : spec.control === 'dynamic_slider' ? props.seedInput[spec.id] : spec.default
  const value = localValues[spec.id]
  if (typeof baseline !== 'number' || typeof value !== 'number') return null
  const delta = value - baseline
  if (Math.abs(delta) <= (spec.step || 0) / 2) return null
  return {
    dir: delta > 0 ? 'up' : 'down',
    text: `${delta > 0 ? '+' : ''}${delta.toFixed(decimalsForStep(spec.step))}${displayUnit(spec)}`,
  }
}
function frozenBaselineOf(spec) { return frozenBaseline(spec, props.seedInput) }
function frozenMarkerPctOf(spec) { return frozenMarkerPct(rangeOf(spec), frozenBaselineOf(spec)) }
function formatSpecValue(spec, value) { return formatNumber(value, decimalsForStep(spec.step)) }
function displayUnit(spec) { return spec.unit && spec.unit !== '—' ? spec.unit : '' }
function formatRangeEndpoint(spec, value) {
  return `${formatSpecValue(spec, value)}${displayUnit(spec) ? ` ${displayUnit(spec)}` : ''}`
}
function projectNumberWidth(value) {
  const length = String(value ?? '').length
  return `${Math.min(10, Math.max(3, length + 0.5))}ch`
}
function numberError(spec, rawValue, range = null) {
  return numericInputError(
    validateNumericInput(rawValue, range),
    (limit) => formatSpecValue(spec, limit),
    displayUnit(spec),
  )
}
function onNumberTextInput(spec, event) {
  const rawValue = event.target.value
  numberInputValues[spec.id] = rawValue
  const result = validateNumericInput(rawValue)
  validationErrors[spec.id] = numericInputError(result)
  if (result.valid) localValues[spec.id] = result.value
}
function validateNumberInput(spec) {
  const result = validateNumericInput(numberInputValues[spec.id])
  validationErrors[spec.id] = numericInputError(result)
  if (!result.valid) return
  const value = roundToStep(result.value, spec.step)
  localValues[spec.id] = value
  numberInputValues[spec.id] = value
}
function showSliderHint(id) {
  clearTimeout(sliderHintTimer)
  activeSliderHint.value = id
  sliderHintTimer = setTimeout(() => {
    if (activeSliderHint.value === id) activeSliderHint.value = null
  }, 1800)
}
function hideSliderHint(id) {
  clearTimeout(sliderHintTimer)
  sliderHintTimer = null
  if (!id || activeSliderHint.value === id) activeSliderHint.value = null
}
function onSliderPointerDown(id) {
  suppressedSliderFocus = id
  hideSliderHint(id)
  setTimeout(() => {
    if (suppressedSliderFocus === id) suppressedSliderFocus = null
  }, 0)
}
function onSliderFocus(id) {
  if (suppressedSliderFocus === id) return
  showSliderHint(id)
}
function sliderError(spec, rawValue) {
  return numberError(spec, rawValue, rangeOf(spec))
}
function onSliderTextInput(spec, event) {
  const rawValue = event.target.value
  sliderInputValues[spec.id] = rawValue
  const error = sliderError(spec, rawValue)
  validationErrors[spec.id] = error
  if (!error) localValues[spec.id] = Number(rawValue)
}
function validateSliderInput(spec) {
  const error = sliderError(spec, sliderInputValues[spec.id])
  validationErrors[spec.id] = error
  if (error) return
  const value = roundToStep(Number(sliderInputValues[spec.id]), spec.step)
  localValues[spec.id] = value
  sliderInputValues[spec.id] = value
}
function onSliderInput(spec) {
  hideSliderHint(spec.id)
  const value = roundToStep(localValues[spec.id], spec.step)
  localValues[spec.id] = value
  sliderInputValues[spec.id] = value
  delete validationErrors[spec.id]
}
function discardChanges() {
  resetLocalValues()
  emit('discard-all-changes')
}
function resetCommonChanges() {
  resetLocalValues()
}
function onSubmit() {
  if (props.responding || !hasPendingChanges.value || hasValidationErrors.value) return
  emit('recalculate', {
    overrides: { ...buildOverrides(props.paramDict, localValues, props.seedInput), ...props.advancedOverrides },
    basics: {
      city: isHenan.value ? (localValues.city || null) : undefined,
      node_name: isHenan.value ? null : (localValues.node_name || null),
      capacity_mwh: localValues.capacity_mwh,
      power_mw: localValues.power_mw,
    },
  })
}
</script>

<style scoped>
.ir-adjust { margin: var(--xc-space-5) var(--xc-space-6) var(--xc-space-6); border: 1px solid var(--xc-border-card); border-radius: var(--xc-radius-lg); background: var(--xc-surface-card); box-shadow: var(--xc-shadow-sm); backdrop-filter: blur(var(--xc-blur-sm)); overflow: hidden; }
.ir-adjust__header { display:flex; align-items:center; justify-content:space-between; gap:var(--xc-space-4); padding:var(--xc-space-5); }
.ir-adjust__toggle { width:100%; display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:center; gap:var(--xc-space-4); min-width:0; padding:0; border:0; background:transparent; color:var(--xc-text-soft); text-align:left; cursor:pointer; }
.ir-adjust__heading-copy { display:grid; gap:var(--xc-space-1); }
.ir-adjust__heading-copy strong { color:var(--xc-text-default); font-size:var(--xc-fs-sm); font-weight:var(--xc-fw-semi); }
.ir-adjust__heading-copy small { color:var(--xc-text-soft); font-size:var(--xc-fs-xs); line-height:var(--xc-lh-normal); font-weight:var(--xc-fw-regular); }
.ir-adjust__toggle:hover:not(:disabled) strong { color:var(--xc-text-strong); }
.ir-adjust__toggle-action { display:inline-flex; align-items:center; gap:var(--xc-space-2); min-height:44px; padding:0 var(--xc-space-4); border:1px solid var(--xc-border-accent); border-radius:var(--xc-radius-sm); background:var(--xc-accent-blue-soft); color:var(--xc-accent-blue); font-size:var(--xc-fs-sm); font-weight:var(--xc-fw-semi); white-space:nowrap; }
.ir-adjust__toggle:focus-visible,.ir-adjust__reset:focus-visible,.ir-adjust__scope-reset:focus-visible,.ir-adjust__submit:focus-visible,.ir-adjust__tabs button:focus-visible { outline:2px solid var(--xc-accent-blue); outline-offset:2px; }
.ir-adjust__toggle:disabled,.ir-adjust__reset:disabled,.ir-adjust__scope-reset:disabled,.ir-adjust__submit:disabled { cursor:not-allowed; opacity:.6; }
.ir-adjust__pending-bar { display:flex; align-items:center; justify-content:space-between; gap:var(--xc-space-4); padding:var(--xc-space-4) var(--xc-space-5); border-top:1px solid var(--xc-border-soft); background:var(--xc-surface-tinted); }
.ir-adjust__pending-copy { min-width:0; color:var(--xc-text-soft); font-size:var(--xc-fs-sm); line-height:var(--xc-lh-normal); }
.ir-adjust__pending-actions { display:flex; align-items:center; gap:var(--xc-space-3); flex:0 0 auto; }
.ir-adjust__caret { width:16px; height:16px; flex:0 0 auto; color:var(--xc-accent-blue); transition:transform var(--xc-dur-fast) var(--xc-ease-out); }
.ir-adjust__caret.is-open { transform:rotate(180deg); }
.ir-adjust__draft-count { display:grid; place-items:center; min-width:22px; height:22px; padding:0 var(--xc-space-1); border-radius:var(--xc-radius-full); background:var(--xc-accent-blue); color:var(--xc-text-inverse); font-size:var(--xc-fs-2xs); font-weight:var(--xc-fw-bold); }
.ir-adjust__body { padding: 0 var(--xc-space-5) var(--xc-space-5); }
.ir-adjust__tabs { display:flex; gap:var(--xc-space-6); border-top:1px solid var(--xc-border-soft); border-bottom:1px solid var(--xc-border-soft); }
.ir-adjust__tabs button { position:relative; display:inline-flex; align-items:center; gap:var(--xc-space-2); min-height:48px; padding:0 var(--xc-space-2); border:0; background:transparent; color:var(--xc-text-soft); font-size:var(--xc-fs-sm); cursor:pointer; }
.ir-adjust__tabs button::after { content:""; position:absolute; right:0; bottom:-1px; left:0; height:2px; background:transparent; }
.ir-adjust__tabs button.is-active { color:var(--xc-text-strong); font-weight:var(--xc-fw-semi); }
.ir-adjust__tabs button.is-active::after { background:var(--xc-accent-blue); }
.ir-adjust__tab-panel--advanced { padding-top:var(--xc-space-1); }
.ir-adjust__tab-toolbar { display:flex; align-items:center; justify-content:space-between; gap:var(--xc-space-4); min-height:60px; padding:var(--xc-space-4) 0; border-bottom:1px solid var(--xc-border-soft); color:var(--xc-text-soft); font-size:var(--xc-fs-sm); }
.ir-adjust__scope-reset { width:132px; min-height:44px; padding:0; border:1px solid var(--xc-border-soft); border-radius:8px; background:transparent; color:var(--xc-text-soft); font-size:var(--xc-fs-sm); cursor:pointer; }
.ir-adjust__scope-reset:hover:not(:disabled) { border-color:var(--xc-border-accent); color:var(--xc-accent-blue); }
.ir-adjust__zone { padding:var(--xc-space-7) 0 var(--xc-space-6); border-top:1px solid var(--xc-border-soft); }
.ir-adjust__tab-panel .ir-adjust__zone:first-child { border-top:0; }
.ir-adjust__zone-title { display:flex; align-items:center; gap:var(--xc-space-2); font-size:var(--xc-fs-sm); font-weight:var(--xc-fw-semi); color:var(--xc-text-strong); margin:0 0 var(--xc-space-5); }
.ir-adjust__zone-icon { width:18px; height:18px; flex:0 0 auto; color:var(--xc-accent-blue); }

/* 项目信息使用铺满可用宽度的数据带；可调参数使用全宽单行轨道。 */
.ir-adjust__rows { display:flex; flex-direction:column; gap: var(--xc-space-6); }
.ir-adjust__row { display:grid; grid-template-columns:1fr; gap:var(--xc-space-6); align-items:stretch; }
.ir-adjust__row--single { grid-template-columns:1fr; }

/* 项目信息使用铺满可用宽度的数据带：3/4 项自动均分，首项与分区标题共用左边界。 */
.ir-adjust__row--project { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:var(--xc-space-7); width:100%; }
.ir-adjust__row--project .ir-adjust__field { width:auto; }

.ir-adjust__field { min-width:0; display:flex; flex-direction:column; gap:var(--xc-space-2); }
.ir-adjust__field:not(.ir-adjust__project-item) { width:100%; }
.ir-adjust__project-item {
  min-height:92px;
  display:grid;
  grid-template-columns:18px minmax(0,1fr);
  grid-template-rows:auto minmax(44px,auto);
  align-content:center;
  align-items:center;
  column-gap:var(--xc-space-2);
  row-gap:var(--xc-space-4);
  padding:var(--xc-space-3) 0;
  text-align:left;
}
.ir-adjust__project-icon { display:grid; place-items:center; width:18px; height:18px; color:var(--xc-accent-blue); }
.ir-adjust__project-icon svg { width:16px; height:16px; }
.ir-adjust__field-content { min-width:0; display:flex; flex-direction:column; gap:var(--xc-space-2); }
.ir-adjust__project-item .ir-adjust__field-content { display:contents; }
.ir-adjust__project-item .ir-adjust__label { grid-column:2; grid-row:1; }
.ir-adjust__project-item .ir-adjust__ro,
.ir-adjust__project-item .ir-adjust__node-trigger,
.ir-adjust__project-item .ir-adjust__number-value { grid-column:1 / -1; grid-row:2; justify-self:start; margin-left:4px; min-height:44px; display:flex; align-items:center; line-height:1.2; padding:0; }
.ir-adjust__project-item .ir-adjust__node-trigger { width:100%; min-width:0; }
.ir-adjust__project-item .ir-adjust__number-value { justify-content:flex-start; }
.ir-adjust__project-item .ir-adjust__number {
  width:3.5ch;
  min-width:3.5ch;
  max-width:10ch;
  padding:0;
  border:0;
  border-radius:0;
  outline:0;
  background:transparent;
  color:var(--xc-text-strong);
  caret-color:var(--xc-accent-blue);
  font-family:var(--xc-font-num);
  font-size:var(--xc-fs-kpi-md);
  font-weight:var(--xc-fw-bold);
  text-align:left;
  transition:color var(--xc-dur-fast),text-shadow var(--xc-dur-fast);
}
.ir-adjust__project-item .ir-adjust__number:hover { color:var(--xc-accent-blue); }
.ir-adjust__project-item .ir-adjust__number:focus-visible { outline:none; border:0; color:var(--xc-accent-blue); text-shadow:var(--xc-glow-blue); }
.ir-adjust__project-item .ir-adjust__ro { font-size:var(--xc-fs-lg); font-weight:var(--xc-fw-semi); color:var(--xc-text-strong); }
.ir-adjust__project-item .ir-adjust__label { font-size:var(--xc-fs-xs); }
.ir-adjust__label { font-size:var(--xc-fs-sm); line-height:var(--xc-lh-normal); color:var(--xc-text-soft); }
.ir-adjust__number-value { display:inline-flex; align-items:baseline; gap:var(--xc-space-2); color:var(--xc-text-strong); }
.ir-adjust__number-value small { color:var(--xc-text-mute); font-size:var(--xc-fs-xs); }
.ir-adjust__ro { font-size:var(--xc-fs-sm); color:var(--xc-text-soft); }
.ir-adjust__pending { font-size:var(--xc-fs-xs); line-height:var(--xc-lh-normal); color:var(--xc-text-soft); }

.pslider { min-width:0; }
.ps-rail { display:grid; grid-template-columns:minmax(118px,168px) minmax(108px,auto) minmax(220px,1fr) minmax(82px,112px); align-items:center; gap:var(--xc-space-4); min-height:62px; padding:var(--xc-space-2) 0; }
.ps-label { min-width:0; color:var(--xc-text-soft); font-size:var(--xc-fs-sm); line-height:var(--xc-lh-normal); }
.ps-value-area { position:relative; display:inline-flex; justify-content:flex-end; min-width:0; }
.ps-val { display:inline-flex; align-items:baseline; justify-content:flex-end; gap:var(--xc-space-2); padding:0; background:transparent; }
.ps-val small { color:var(--xc-text-soft); font-size:var(--xc-fs-xs); white-space:nowrap; transition:color var(--xc-dur-fast); }
.ps-val:hover small,.ps-val:focus-within small { color:var(--xc-text-soft); }
.ps-track { position:relative; min-width:0; padding-top:18px; }
.ps-range-labels { display:flex; justify-content:space-between; gap:var(--xc-space-3); margin-top:0; color:var(--xc-text-soft); font-size:var(--xc-fs-xs); line-height:var(--xc-lh-normal); }
.ps-mark { position:absolute; top:0; left:clamp(32px,var(--mark-pct),calc(100% - 32px)); max-width:96px; overflow:hidden; color:var(--xc-text-soft); font-family:var(--xc-font-num); font-size:var(--xc-fs-2xs); line-height:var(--xc-lh-normal); pointer-events:none; text-overflow:ellipsis; white-space:nowrap; transform:translateX(-50%); }
.ps-mark::after { content:""; display:block; width:1px; height:7px; margin:3px auto 0; background:var(--xc-border-strong); }
.ps-input-hint { position:absolute; right:0; bottom:calc(100% + 10px); z-index:2; padding:var(--xc-space-2) var(--xc-space-3); border:1px solid var(--xc-border-strong); border-radius:var(--xc-radius-sm); background:var(--xc-surface-raised); box-shadow:var(--xc-shadow-sm); color:var(--xc-text-soft); font-size:var(--xc-fs-xs); line-height:var(--xc-lh-normal); pointer-events:none; white-space:nowrap; }
.ps-input-hint::after { content:""; position:absolute; top:100%; right:18px; width:7px; height:7px; border-right:1px solid var(--xc-border-strong); border-bottom:1px solid var(--xc-border-strong); background:var(--xc-surface-raised); transform:translateY(-4px) rotate(45deg); }
.ps-validation { grid-column:2 / 5; display:flex; align-items:center; justify-content:flex-end; gap:var(--xc-space-2); min-height:22px; margin-top:calc(var(--xc-space-2) * -1); color:var(--xc-status-danger); font-size:var(--xc-fs-xs); font-weight:var(--xc-fw-semi); line-height:var(--xc-lh-normal); }
.ps-validation--project { grid-column:1 / -1; justify-content:flex-start; margin-top:var(--xc-space-1); }
.ps-validation svg { width:14px; height:14px; flex:0 0 auto; }
.ir-adjust__slider { -webkit-appearance:none; appearance:none; width:100%; height:4px; margin:12px 0 16px; border-radius:var(--xc-radius-full); cursor:pointer; background:linear-gradient(90deg,var(--xc-accent-blue) var(--pct,0%),var(--xc-border-soft) var(--pct,0%)); transition:filter var(--xc-dur-base),box-shadow var(--xc-dur-base); }
.ir-adjust__slider:hover { filter:brightness(1.2); }
.ir-adjust__slider:focus-visible { outline:2px solid var(--xc-accent-blue); outline-offset:5px; box-shadow:var(--xc-glow-blue); }
.ir-adjust__slider::-webkit-slider-thumb { -webkit-appearance:none; appearance:none; width:16px; height:16px; border-radius:50%; background:var(--xc-text-strong); border:3px solid var(--xc-accent-blue); box-shadow:var(--xc-shadow-sm); cursor:pointer; transition:transform var(--xc-dur-base),box-shadow var(--xc-dur-base); }
.ir-adjust__slider::-moz-range-thumb { width:16px; height:16px; border-radius:50%; background:var(--xc-text-strong); border:3px solid var(--xc-accent-blue); cursor:pointer; transition:transform var(--xc-dur-base),box-shadow var(--xc-dur-base); }
.ir-adjust__slider:active::-webkit-slider-thumb { transform:scale(1.15); box-shadow:var(--xc-glow-blue); }
.ir-adjust__slider:active::-moz-range-thumb { transform:scale(1.15); box-shadow:var(--xc-glow-blue); }
.ps-foot { display:flex; justify-content:flex-end; align-items:center; min-width:0; min-height:22px; font-size:var(--xc-fs-xs); line-height:var(--xc-lh-normal); }
.ps-delta { font-weight:var(--xc-fw-semi); padding:1px var(--xc-space-2); border-radius:var(--xc-radius-full); }
.ps-delta.up { color:var(--xc-status-ok); background:var(--xc-status-ok-soft); }
.ps-delta.down { color:var(--xc-status-danger); background:var(--xc-status-danger-soft); }
.ir-adjust__number,.ir-adjust__text { width:100%; height:44px; padding:0 var(--xc-space-3); border:1px solid var(--xc-inline-border); border-radius:var(--xc-radius-sm); background:var(--xc-inline-bg); color:var(--xc-text-default); font-size:var(--xc-fs-sm); text-align:center; -moz-appearance:textfield; appearance:textfield; }
/* 站点在数据带中保持为自然宽度铭牌；搜索只在独立浮层中出现。 */
.ir-adjust__node-trigger { display:flex; align-items:center; gap:var(--xc-space-3); min-width:0; width:100%; max-width:100%; padding:0; border:0; border-radius:var(--xc-radius-xs); background:transparent; color:var(--xc-text-strong); font-family:var(--xc-font-zh); text-align:left; cursor:pointer; }
.ir-adjust__node-trigger:hover:not(:disabled) { background:var(--xc-surface-control); }
.ir-adjust__node-trigger:focus-visible { outline:2px solid var(--xc-accent-blue); outline-offset:2px; }
.ir-adjust__node-trigger:disabled { cursor:not-allowed; opacity:.6; }
.ir-adjust__node-name-tooltip { min-width:0; flex:1 1 auto; overflow:hidden; }
.ir-adjust__node-name { display:block; min-width:0; overflow:hidden; color:inherit; font-size:var(--xc-fs-lg); font-weight:var(--xc-fw-semi); line-height:1.2; text-overflow:ellipsis; white-space:nowrap; }
.ir-adjust__node-action { flex:0 0 auto; color:var(--xc-text-soft); font-size:var(--xc-fs-xs); font-weight:var(--xc-fw-regular); }
.ir-adjust__node-trigger:hover:not(:disabled) .ir-adjust__node-action,
.ir-adjust__node-trigger:focus-visible .ir-adjust__node-action { color:var(--xc-accent-blue); }
:global(.ir-adjust__node-editor.el-popper) { width:min(320px, calc(100vw - var(--xc-space-8))) !important; max-width:calc(100vw - var(--xc-space-8)); min-width:220px; padding:var(--xc-space-3); border:1px solid var(--xc-border-strong); border-radius:var(--xc-radius-sm); background:var(--xc-surface-raised); box-shadow:var(--xc-shadow-md); }
:global(.ir-adjust__node-editor .ir-adjust__node-editor-body) { width:100%; max-width:100%; }
:global(.ir-adjust__node-editor .ir-adjust__node-select) { width:100%; min-width:0; }
:global(.ir-adjust__node-editor .ir-adjust__node-select .el-select__wrapper) { min-height:44px; padding:0 var(--xc-space-3); border:1px solid var(--xc-border-accent); border-radius:var(--xc-radius-sm); background:var(--xc-inline-bg); box-shadow:none; }
:global(.ir-adjust__node-editor .ir-adjust__node-select .el-select__wrapper.is-focused) { box-shadow:0 0 0 1px var(--xc-accent-blue); }
:global(.ir-adjust__node-editor .ir-adjust__node-select .el-select__selected-item),
:global(.ir-adjust__node-editor .ir-adjust__node-select .el-select__placeholder),
:global(.ir-adjust__node-editor .ir-adjust__node-select .el-select__input) { color:var(--xc-text-default); font-family:var(--xc-font-zh); font-size:var(--xc-fs-sm); }
:global(.ir-adjust__node-editor .ir-adjust__node-select .el-select__input) { caret-color:var(--xc-accent-blue); }
:global(.ir-adjust__node-popper.el-popper) { overflow:hidden; border:1px solid var(--xc-border-strong); border-radius:var(--xc-radius-sm); background:var(--xc-surface-raised); box-shadow:var(--xc-shadow-md); color:var(--xc-text-default); }
:global(.ir-adjust__node-popper.el-popper .el-popper__arrow::before) { border-color:var(--xc-border-strong); background:var(--xc-surface-raised); }
:global(.ir-adjust__node-popper .el-select-dropdown) { background:var(--xc-surface-raised); }
:global(.ir-adjust__node-popper .el-select-dropdown__wrap) { max-height:240px; overflow-x:hidden; scrollbar-color:var(--xc-border-strong) var(--xc-surface-frosted); scrollbar-width:thin; }
:global(.ir-adjust__node-popper .el-select-dropdown__wrap::-webkit-scrollbar) { width:6px; }
:global(.ir-adjust__node-popper .el-select-dropdown__wrap::-webkit-scrollbar-track) { background:var(--xc-surface-frosted); }
:global(.ir-adjust__node-popper .el-select-dropdown__wrap::-webkit-scrollbar-thumb) { border-radius:var(--xc-radius-sm); background:var(--xc-border-strong); }
:global(.ir-adjust__node-popper .el-select-dropdown__wrap::-webkit-scrollbar-thumb:hover) { background:var(--xc-border-accent); }
:global(.ir-adjust__node-popper .el-select-dropdown__list) { padding:var(--xc-space-1); }
:global(.ir-adjust__node-popper .el-select-dropdown__item) { min-height:44px; height:auto; padding:var(--xc-space-3) var(--xc-space-4); border-radius:var(--xc-radius-xs); background:transparent; color:var(--xc-text-default); font-size:var(--xc-fs-sm); line-height:var(--xc-lh-normal); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
:global(.ir-adjust__node-popper .el-select-dropdown__item:hover),
:global(.ir-adjust__node-popper .el-select-dropdown__item.hover) { background:var(--xc-surface-control); color:var(--xc-text-strong); }
:global(.ir-adjust__node-popper .el-select-dropdown__item.is-selected),
:global(.ir-adjust__node-popper .el-select-dropdown__item.is-selected:hover),
:global(.ir-adjust__node-popper .el-select-dropdown__item.is-selected.hover) { background:var(--xc-accent-blue-soft); color:var(--xc-accent-blue); }
:global(.ir-adjust__node-popper .el-select-dropdown__empty) { margin:0; padding:var(--xc-space-5) var(--xc-space-4); border-top:1px solid var(--xc-border-soft); background:var(--xc-surface-frosted); color:var(--xc-text-mute); font-size:var(--xc-fs-xs); }
:global(.ir-adjust__node-popper .el-select-dropdown__footer) { padding:var(--xc-space-2) var(--xc-space-4); border-top:1px solid var(--xc-border-soft); background:var(--xc-surface-frosted); color:var(--xc-text-mute); font-size:var(--xc-fs-3xs); line-height:20px; text-align:center; }
.ir-adjust__number::-webkit-inner-spin-button,.ir-adjust__number::-webkit-outer-spin-button { -webkit-appearance:none; margin:0; }
.ir-adjust__number:disabled,.ir-adjust__slider:disabled { cursor:not-allowed; opacity:.55; }
.ir-adjust__number.is-invalid { border-color:var(--xc-status-danger); color:var(--xc-status-danger); }
.ps-val-input { width:7ch; height:24px; border:0; border-radius:0; outline:0; background:transparent; font-size:16px; font-weight:var(--xc-fw-semi); color:var(--xc-text-default); caret-color:var(--xc-accent-blue); padding:0; text-align:right; transition:color var(--xc-dur-fast),text-shadow var(--xc-dur-fast); }
.ps-val-input:hover { color:var(--xc-accent-blue); }
.ps-val-input:focus-visible { outline:none; border:0; color:var(--xc-accent-blue); text-shadow:var(--xc-glow-blue); }
.ps-val-input.is-invalid { color:var(--xc-status-danger); text-shadow:none; }
.ir-adjust__text:focus-visible { outline:2px solid var(--xc-accent-blue); outline-offset:2px; border-color:var(--xc-border-accent); }
.ir-adjust__footer { display:flex; justify-content:flex-end; align-items:center; gap:var(--xc-space-4); padding-top:var(--xc-space-5); border-top:1px solid var(--xc-border-soft); }
.ir-adjust__reset { min-height:44px; padding:0 var(--xc-space-4); border:1px solid var(--xc-border-soft); border-radius:var(--xc-radius-md); background:transparent; color:var(--xc-text-soft); font-size:var(--xc-fs-sm); cursor:pointer; transition:border-color var(--xc-dur-base),color var(--xc-dur-base),box-shadow var(--xc-dur-base); }
.ir-adjust__reset:hover:not(:disabled) { border-color:var(--xc-border-accent); color:var(--xc-accent-blue); box-shadow:var(--xc-glow-blue); }
.ir-adjust__draft-note { margin-right:auto; color:var(--xc-text-soft); font-size:var(--xc-fs-xs); line-height:var(--xc-lh-normal); }
.ir-adjust__submit { min-height:44px; padding:0 var(--xc-space-6); border:0; border-radius:var(--xc-radius-md); background:var(--xc-grad-brand); color:var(--xc-text-strong); font-size:var(--xc-fs-sm); cursor:pointer; transition:transform var(--xc-dur-base),box-shadow var(--xc-dur-base); }
.ir-adjust__submit:hover:not(:disabled) { transform:translateY(-1px); box-shadow:var(--xc-glow-blue); }
@container (max-width:900px) { .ir-adjust__row--project { grid-template-columns:repeat(2,minmax(0,1fr)); } }
@container (max-width:760px) {
  .ps-rail { grid-template-columns:minmax(96px,140px) minmax(96px,auto) minmax(150px,1fr) minmax(70px,96px); gap:var(--xc-space-3); }
}
@container (max-width:640px) {
  .ir-adjust { margin-inline:var(--xc-space-4); }
  .ir-adjust__toggle { grid-template-columns:minmax(0,1fr) auto; }
  .ir-adjust__tab-toolbar { align-items:stretch; flex-direction:column; }
  .ps-rail { grid-template-columns:minmax(0,1fr) auto; row-gap:var(--xc-space-2); min-height:96px; }
  .ps-label { grid-column:1; grid-row:1; }
  .ps-value-area { grid-column:2; grid-row:1; }
  .ps-track { grid-column:1 / -1; grid-row:2; }
  .ps-foot { grid-column:1 / -1; grid-row:3; min-height:18px; }
  .ps-validation { grid-column:1 / -1; }
  .ir-adjust__row--single .ir-adjust__field,.ir-adjust__field:not(.ir-adjust__project-item) { width:100%; max-width:none; }
  .ir-adjust__row--project { grid-template-columns:1fr; width:100%; }
  .ir-adjust__row--project .ir-adjust__field { width:100%; }
  .ir-adjust__footer,.ir-adjust__pending-bar { align-items:stretch; flex-direction:column; }
  .ir-adjust__pending-actions { width:100%; flex-direction:column; }
  .ir-adjust__draft-note { margin-right:0; }
  .ir-adjust__reset,.ir-adjust__submit { width:100%; }
}
@media (prefers-reduced-motion:reduce) {
  .ir-adjust__caret,.ir-adjust__reset,.ir-adjust__scope-reset,.ir-adjust__submit,.ir-adjust__slider,.ir-adjust__slider::-webkit-slider-thumb,.ir-adjust__slider::-moz-range-thumb { transition:none; }
}
</style>

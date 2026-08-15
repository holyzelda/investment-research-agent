<template>
  <div
    v-if="modelValue || embedded"
    :class="embedded ? 'ir-advanced-embedded' : 'ir-advanced__mask'"
    @click.self="!embedded && close()"
    @keydown.esc="!embedded && close()"
  >
    <section ref="dialog" class="ir-advanced" :class="{ 'is-embedded': embedded }" :role="embedded ? 'region' : 'dialog'" :aria-modal="embedded ? undefined : 'true'" :aria-labelledby="embedded ? undefined : 'advanced-param-title'" :tabindex="embedded ? undefined : -1">
      <header v-if="!embedded" class="ir-advanced__head">
        <div>
          <h3 id="advanced-param-title">高级参数</h3>
          <p>修改后暂存，点击“重新测算”时统一提交。</p>
        </div>
        <button ref="closeButton" type="button" class="ir-advanced__close" aria-label="关闭高级参数" @click="close">×</button>
      </header>

      <div v-if="embedded" class="ir-advanced__embedded-toolbar">
        <span>{{ advancedChangeCount > 0 ? `已修改 ${advancedChangeCount} 项高级参数` : '高级参数暂无修改' }}</span>
        <button type="button" class="ir-advanced__reset" :disabled="disabled || !hasChangesFromSeed" @click="resetToSeed">
          撤销高级参数修改
        </button>
      </div>

      <div class="ir-advanced__body">
        <section v-for="section in sections" :key="section.title" class="ir-advanced__section">
          <h4>
            <svg class="ir-advanced__section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true" v-html="section.icon" />
            {{ section.title }}
          </h4>
          <div class="ir-advanced__fields" :class="`ir-advanced__fields--${section.key}`">
            <div
              v-for="spec in section.items"
              :key="spec.id"
              class="ir-advanced__field"
              :class="{ 'ir-advanced__field--slider': isEditable(spec) && rangeOf(spec) }"
            >
              <div class="ir-advanced__field-head">
                <span class="ir-advanced__field-label">
                  <svg class="ir-advanced__field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true" v-html="fieldIcon(spec.id)" />
                  <span>{{ spec.cn || spec.id }}</span>
                </span>
                <select
                  v-if="spec.control === 'select'"
                  :data-param-id="spec.id"
                  v-model.number="values[spec.id]"
                  class="ir-advanced__select"
                  :disabled="disabled"
                  @change="onOperationYearsChange"
                >
                  <option v-for="option in spec.options || []" :key="option.value" :value="option.value">
                    {{ option.label }}
                  </option>
                </select>
                <span v-else-if="isEditable(spec) && rangeOf(spec)" class="ir-advanced__value xc-num">
                  <input
                    :value="sliderInputValues[spec.id]"
                    class="ir-advanced__number"
                    :class="{ 'is-invalid': validationErrors[spec.id] }"
                    type="number"
                    :min="rangeOf(spec).min"
                    :max="rangeOf(spec).max"
                    :step="spec.step"
                    :disabled="disabled"
                    :aria-invalid="Boolean(validationErrors[spec.id])"
                    :aria-describedby="validationErrors[spec.id] ? `advanced-error-${spec.id}` : undefined"
                    @focus="hideSliderHint(spec.id)"
                    @input="onSliderTextInput(spec, $event)"
                    @blur="validateSliderInput(spec)"
                    @keydown.enter.prevent="$event.currentTarget.blur()"
                  />
                  <small v-if="displayUnit(spec)">{{ displayUnit(spec) }}</small>
                </span>
                <span v-else-if="isEditable(spec)" class="ir-advanced__readonly">数据待完善</span>
                <span v-else class="ir-advanced__readonly xc-num">
                  {{ displayValue(spec) }}<template v-if="displayUnit(spec)"> {{ displayUnit(spec) }}</template>
                </span>
              </div>
              <div v-if="isEditable(spec) && rangeOf(spec)" class="ir-advanced__slider-wrap">
                <input
                  v-model.number="values[spec.id]"
                  class="ir-advanced__slider"
                  type="range"
                  :min="rangeOf(spec).min"
                  :max="rangeOf(spec).max"
                  :step="spec.step"
                  :disabled="disabled"
                  :style="{ '--pct': pctOf(spec) + '%' }"
                  @pointerenter="showSliderHint(spec.id)"
                  @pointerleave="hideSliderHint(spec.id)"
                  @focus="onSliderFocus(spec.id)"
                  @blur="hideSliderHint(spec.id)"
                  @pointerdown="onSliderPointerDown(spec.id)"
                  @input="onSliderInput(spec)"
                />
                <span
                  v-if="frozenMarkerPctOf(spec) !== null"
                  class="ir-advanced__mark"
                  :style="{ '--mark-pct': `${frozenMarkerPctOf(spec)}%` }"
                  aria-hidden="true"
                >{{ formatRangeEndpoint(spec, frozenBaselineOf(spec)) }}</span>
                <span v-if="activeSliderHint === spec.id" class="ir-advanced__input-hint" role="status">点击数值可精确输入</span>
                <div class="ir-advanced__range-labels xc-num">
                  <span>{{ formatRangeEndpoint(spec, rangeOf(spec).min) }}</span>
                  <span>{{ formatRangeEndpoint(spec, rangeOf(spec).max) }}</span>
                </div>
              </div>
              <div
                v-if="validationErrors[spec.id]"
                :id="`advanced-error-${spec.id}`"
                class="ir-advanced__validation"
                role="alert"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                  <circle cx="12" cy="12" r="9" />
                  <path d="M12 7v6M12 17h.01" stroke-linecap="round" />
                </svg>
                <span>{{ validationErrors[spec.id] }}</span>
              </div>
              <div v-if="deltaOf(spec)" class="ir-advanced__delta-row">
                <span class="ir-advanced__delta" :class="deltaOf(spec).dir">{{ deltaOf(spec).text }}</span>
              </div>
            </div>
          </div>
        </section>
      </div>

      <footer v-if="!embedded" class="ir-advanced__footer">
        <button
          type="button"
          class="ir-advanced__reset"
          :disabled="disabled || !hasChangesFromSeed"
          @click="resetToSeed"
        >恢复本次测算值</button>
        <div class="ir-advanced__footer-actions">
          <button type="button" class="ir-advanced__cancel" @click="close">取消</button>
          <button type="button" class="ir-advanced__save" :disabled="disabled || hasValidationErrors" @click="save">暂存修改</button>
        </div>
      </footer>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import {
  decimalsForStep,
  dynamicRange,
  frozenBaseline,
  frozenMarkerPct,
  numericInputError,
  resolveVariant,
  roundToStep,
  validateNumericInput,
} from '@/utils/paramAdjust'
import { formatNumber } from '@/utils/formatNumber'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  paramDict: { type: Array, default: () => [] },
  seedInput: { type: Object, default: () => ({}) },
  comparisonInput: { type: Object, default: null },
  draftInput: { type: Object, default: () => ({}) },
  embedded: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'save', 'validation-change'])

const ADVANCED_SECTION_IDS = [
  {
    key: 'financial', title: '金融边界', ids: ['operation_years'],
    icon: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2" stroke-linecap="round" stroke-linejoin="round"/>',
  },
  {
    key: 'revenue', title: '收益边界', ids: ['mid_long_charge_avg', 'mid_long_discharge_avg', 'strategy_achievement_rate', 'capacity_achievement_rate'],
    icon: '<path d="M4 18 9 13l4 3 7-9" stroke-linecap="round" stroke-linejoin="round"/><path d="M15 7h5v5" stroke-linecap="round" stroke-linejoin="round"/>',
  },
  {
    key: 'cost', title: '成本边界', ids: ['battery_replace_cost', 'maint_cost', 'opex_cost'],
    icon: '<circle cx="12" cy="12" r="9"/><path d="M8 9.5c0-1.4 1.5-2.5 4-2.5s4 1.1 4 2.5-1.5 2.5-4 2.5-4 1.1-4 2.5S9.5 17 12 17s4-1.1 4-2.5M12 5v14" stroke-linecap="round"/>',
  },
]
const FIELD_ICONS = {
  operation_years: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2" stroke-linecap="round" stroke-linejoin="round"/>',
  mid_long_charge_avg: '<path d="M12 3v6m0 0 3-3m-3 3L9 6" stroke-linecap="round" stroke-linejoin="round"/><rect x="5" y="11" width="14" height="10" rx="2"/>',
  mid_long_discharge_avg: '<path d="M12 21v-6m0 0 3 3m-3-3-3 3" stroke-linecap="round" stroke-linejoin="round"/><rect x="5" y="3" width="14" height="10" rx="2"/>',
  strategy_achievement_rate: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  capacity_achievement_rate: '<rect x="3" y="7" width="16" height="10" rx="2"/><path d="M21 10v4M7 10v4M11 10v4M15 10v4" stroke-linecap="round"/>',
  battery_replace_cost: '<path d="M13 2 4 14h7l-1 8 9-12h-7z" stroke-linejoin="round" stroke-linecap="round"/>',
  maint_cost: '<path d="m14.7 6.3 3-3a4 4 0 0 1-5 5L6 15l-3 6 6-3 6.7-6.7a4 4 0 0 1 5-5l-3 3" stroke-linecap="round" stroke-linejoin="round"/>',
  opex_cost: '<path d="M4 7h16M7 4v6M17 4v6M5 11h14v9H5z" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 15h6" stroke-linecap="round"/>',
}
const values = reactive({})
const sliderInputValues = reactive({})
const validationErrors = reactive({})
const activeSliderHint = ref(null)
let sliderHintTimer = null
let suppressedSliderFocus = null
const dialog = ref(null)
const closeButton = ref(null)

function resetValues() {
  Object.keys(values).forEach((key) => delete values[key])
  Object.keys(sliderInputValues).forEach((key) => delete sliderInputValues[key])
  Object.keys(validationErrors).forEach((key) => delete validationErrors[key])
  for (const spec of props.paramDict) {
    // 默认值/步长按当前运营期解析 variants（operation_years 在字典中先于带 variants 的参数出现，已先行赋值）
    const resolved = resolveVariant(spec, values['operation_years'] ?? props.seedInput['operation_years'] ?? 15)
    const value = spec.id in props.draftInput
      ? props.draftInput[spec.id]
      : spec.id in props.seedInput
        ? props.seedInput[spec.id]
        : resolved.default
    const normalized = typeof value === 'number' && resolved.step ? roundToStep(value, resolved.step) : value
    values[spec.id] = normalized
    if (resolved.control === 'slider' || resolved.control === 'dynamic_slider') {
      sliderInputValues[spec.id] = normalized ?? ''
    }
  }
}
watch(() => [props.modelValue, props.seedInput, props.draftInput, props.paramDict], resetValues, { immediate: true, deep: true })
watch(() => props.modelValue, async (open) => {
  if (!open || props.embedded) return
  await nextTick()
  if (closeButton.value) closeButton.value.focus()
  else dialog.value?.focus()
})

const sections = computed(() => {
  const byId = new Map(props.paramDict.map((spec) => [spec.id, spec]))
  const opYears = values['operation_years']
  return ADVANCED_SECTION_IDS
    .map(({ key, title, ids, icon }) => ({
      key, title, icon,
      items: ids.map((id) => byId.get(id)).filter(Boolean).map((spec) => resolveVariant(spec, opYears)),
    }))
    .filter((section) => section.items.length)
})
const advancedChangeCount = computed(() => sections.value.reduce((count, section) => count + section.items.reduce((sectionCount, spec) => {
  if (!isEditable(spec) || spec.g !== 1) return sectionCount
  const baseline = spec.id in props.seedInput ? props.seedInput[spec.id] : spec.default
  return normalizeValue(values[spec.id], spec.step) !== normalizeValue(baseline, spec.step)
    ? sectionCount + 1
    : sectionCount
}, 0), 0))
const hasChangesFromSeed = computed(() => advancedChangeCount.value > 0)
const hasValidationErrors = computed(() => Object.values(validationErrors).some(Boolean))
watch(hasValidationErrors, (invalid) => emit('validation-change', invalid), { immediate: true })

function normalizeValue(value, step) {
  return typeof value === 'number' && step ? roundToStep(value, step) : value
}
function resetToSeed() {
  for (const section of sections.value) {
    for (const spec of section.items) {
      if (!isEditable(spec) || spec.g !== 1) continue
      const value = spec.id in props.seedInput ? props.seedInput[spec.id] : spec.default
      const normalized = normalizeValue(value, spec.step)
      values[spec.id] = normalized
      if (spec.control === 'slider' || spec.control === 'dynamic_slider') {
        sliderInputValues[spec.id] = normalized ?? ''
      }
      delete validationErrors[spec.id]
    }
  }
  saveEmbeddedDraft()
}

function isEditable(spec) {
  return spec.control === 'slider' || spec.control === 'dynamic_slider' || spec.control === 'select'
}
function fieldIcon(id) {
  return FIELD_ICONS[id] || '<circle cx="12" cy="12" r="9"/><path d="M12 8v4M12 16h.01" stroke-linecap="round"/>'
}
function rangeOf(spec) {
  if (spec.control === 'slider') return { min: spec.min, max: spec.max }
  if (spec.control === 'dynamic_slider') return dynamicRange(props.seedInput[spec.id], spec.step)
  return null
}
function pctOf(spec) {
  const range = rangeOf(spec)
  const value = values[spec.id]
  if (!range || typeof value !== 'number' || !Number.isFinite(value) || range.max === range.min) return 0
  return Math.min(100, Math.max(0, ((value - range.min) / (range.max - range.min)) * 100))
}
function deltaOf(spec) {
  if (!isEditable(spec)) return null
  const historicalBaseline = props.comparisonInput?.[spec.id]
  const baseline = typeof historicalBaseline === 'number'
    ? historicalBaseline
    : spec.control === 'dynamic_slider' ? props.seedInput[spec.id] : spec.default
  const value = values[spec.id]
  if (typeof baseline !== 'number' || typeof value !== 'number') return null
  const delta = value - baseline
  if (Math.abs(delta) <= (spec.step || 0) / 2) return null
  return {
    dir: delta > 0 ? 'up' : 'down',
    text: `${delta > 0 ? '+' : ''}${delta.toFixed(decimalsForStep(spec.step))}${displayUnit(spec)}`,
  }
}
function sliderError(spec, rawValue) {
  return numericInputError(
    validateNumericInput(rawValue, rangeOf(spec)),
    (limit) => formatNumber(limit, decimalsForStep(spec.step)),
    displayUnit(spec),
  )
}
function onSliderTextInput(spec, event) {
  const rawValue = event.target.value
  sliderInputValues[spec.id] = rawValue
  const error = sliderError(spec, rawValue)
  validationErrors[spec.id] = error
  if (!error) {
    values[spec.id] = Number(rawValue)
    saveEmbeddedDraft()
  }
}
function validateSliderInput(spec) {
  const error = sliderError(spec, sliderInputValues[spec.id])
  validationErrors[spec.id] = error
  if (error) return
  const value = roundToStep(Number(sliderInputValues[spec.id]), spec.step)
  values[spec.id] = value
  sliderInputValues[spec.id] = value
  saveEmbeddedDraft()
}
function onSliderInput(spec) {
  hideSliderHint(spec.id)
  const value = roundToStep(values[spec.id], spec.step)
  values[spec.id] = value
  sliderInputValues[spec.id] = value
  delete validationErrors[spec.id]
  saveEmbeddedDraft()
}
function onSliderPointerDown(id) {
  suppressedSliderFocus = id
  hideSliderHint(id)
}
function onSliderFocus(id) {
  if (suppressedSliderFocus === id) {
    suppressedSliderFocus = null
    hideSliderHint(id)
    return
  }
  showSliderHint(id)
}
function showSliderHint(id) {
  clearTimeout(sliderHintTimer)
  activeSliderHint.value = id
  sliderHintTimer = setTimeout(() => { if (activeSliderHint.value === id) activeSliderHint.value = null }, 1800)
}
function hideSliderHint(id) {
  clearTimeout(sliderHintTimer)
  if (!id || activeSliderHint.value === id) activeSliderHint.value = null
}
function displayUnit(spec) {
  return spec.unit && spec.unit !== '—' ? spec.unit : ''
}
function formatRangeEndpoint(spec, value) {
  return `${formatNumber(value, decimalsForStep(spec.step))}${displayUnit(spec) ? ` ${displayUnit(spec)}` : ''}`
}
function displayValue(spec) {
  const value = values[spec.id]
  return value === null || value === undefined || value === '' ? '—' : formatNumber(value, decimalsForStep(spec.step))
}
function frozenBaselineOf(spec) {
  return frozenBaseline(spec, props.seedInput)
}
function frozenMarkerPctOf(spec) { return frozenMarkerPct(rangeOf(spec), frozenBaselineOf(spec)) }
function close() {
  emit('update:modelValue', false)
}
function onOperationYearsChange() {
  // 用户切换运营期：带 variants 的参数（换电成本）重置为新档默认值（15→0，20→0.3）。
  // 用 @change 而非 watch，避免 seedInput 刷新（新版本到达）时误把沿用值 clobber 成默认值。
  for (const spec of props.paramDict) {
    if (!spec.variants) continue
    const resolved = resolveVariant(spec, values['operation_years'])
    values[spec.id] = resolved.default
    if (resolved.control === 'slider' || resolved.control === 'dynamic_slider') {
      sliderInputValues[spec.id] = resolved.default ?? ''
    } else {
      delete sliderInputValues[spec.id]
    }
    delete validationErrors[spec.id]
  }
  saveEmbeddedDraft()
}
function collectOverrides() {
  const overrides = {}
  for (const section of sections.value) {
    for (const spec of section.items) {
      if (!isEditable(spec) || spec.g !== 1 || values[spec.id] === null || values[spec.id] === undefined) continue
      const baselineValue = spec.id in props.seedInput ? props.seedInput[spec.id] : spec.default
      if (normalizeValue(values[spec.id], spec.step) !== normalizeValue(baselineValue, spec.step)) {
        overrides[spec.id] = values[spec.id]
      }
    }
  }
  return overrides
}
function saveEmbeddedDraft() {
  if (props.embedded && !hasValidationErrors.value) emit('save', collectOverrides())
}
function save() {
  if (props.disabled || hasValidationErrors.value) return
  emit('save', collectOverrides())
  close()
}
</script>

<style scoped>
.ir-advanced__mask { position:fixed; inset:0; z-index:var(--xc-z-modal); display:grid; place-items:center; padding:var(--xc-space-6); background:var(--xc-surface-overlay); backdrop-filter:blur(var(--xc-blur-sm)); }
.ir-advanced-embedded { width:100%; }
.ir-advanced { width:min(680px,100%); max-height:min(760px,calc(100vh - 48px)); display:flex; flex-direction:column; overflow:hidden; border:1px solid var(--xc-border-card); border-radius:var(--xc-radius-xl); background:var(--xc-surface-raised); box-shadow:var(--xc-shadow-raised); }
.ir-advanced.is-embedded { width:100%; max-height:none; overflow:visible; border:0; border-radius:0; background:transparent; box-shadow:none; }
.ir-advanced.is-embedded .ir-advanced__body { padding-inline:0; }
.ir-advanced:focus { outline:none; }
.ir-advanced__head { display:flex; justify-content:space-between; gap:var(--xc-space-5); padding:var(--xc-space-6); border-bottom:1px solid var(--xc-border-soft); }
.ir-advanced__head h3 { margin:0; color:var(--xc-text-strong); font-size:var(--xc-fs-lg); font-weight:var(--xc-fw-semi); }
.ir-advanced__head p { margin:var(--xc-space-2) 0 0; color:var(--xc-text-mute); font-size:var(--xc-fs-xs); }
.ir-advanced__close { width:36px; height:36px; border:0; border-radius:var(--xc-radius-sm); background:transparent; color:var(--xc-text-mute); font-size:22px; line-height:1; cursor:pointer; }
.ir-advanced__close:hover { background:var(--xc-surface-control); color:var(--xc-text-strong); }
.ir-advanced__close:focus-visible,.ir-advanced__reset:focus-visible,.ir-advanced__cancel:focus-visible,.ir-advanced__save:focus-visible,.ir-advanced__select:focus-visible { outline:2px solid var(--xc-accent-blue); outline-offset:2px; }
.ir-advanced__reset:disabled { cursor:not-allowed; opacity:.6; }
.ir-advanced__number:disabled,.ir-advanced__select:disabled,.ir-advanced__slider:disabled { cursor:not-allowed; opacity:.55; }
.ir-advanced__number:focus-visible { outline:none; }
.ir-advanced__number.is-invalid { color:var(--xc-status-danger); text-shadow:none; }
.ir-advanced__body { overflow-y:auto; padding:0 var(--xc-space-6); }
.ir-advanced__section { padding:var(--xc-space-7) 0 var(--xc-space-6); border-bottom:1px solid var(--xc-border-soft); }
.ir-advanced__section:last-child { border-bottom:0; }
.ir-advanced__section h4 { display:flex; align-items:center; gap:var(--xc-space-2); margin:0 0 var(--xc-space-5); color:var(--xc-text-strong); font-size:var(--xc-fs-sm); font-weight:var(--xc-fw-semi); }
.ir-advanced__section-icon { width:18px; height:18px; flex:0 0 auto; color:var(--xc-accent-blue); }
.ir-advanced__fields { display:grid; grid-template-columns:1fr; gap:var(--xc-space-5); }
.ir-advanced__field { min-width:0; }
.ir-advanced__field--slider { display:grid; grid-template-columns:minmax(118px,168px) minmax(108px,auto) minmax(180px,1fr) minmax(82px,112px); align-items:center; gap:var(--xc-space-4); min-height:62px; }
.ir-advanced__field--slider .ir-advanced__field-head { display:contents; }
.ir-advanced__field--slider .ir-advanced__field-label { grid-column:1; }
.ir-advanced__field--slider .ir-advanced__value { grid-column:2; }
.ir-advanced__field-head { display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:center; min-height:32px; gap:var(--xc-space-4); color:var(--xc-text-soft); font-size:var(--xc-fs-xs); }
.ir-advanced__field:not(.ir-advanced__field--slider) .ir-advanced__field-head { min-height:52px; }
.ir-advanced__field-label { min-width:0; display:inline-flex; align-items:center; gap:var(--xc-space-2); }
.ir-advanced__field-icon { width:15px; height:15px; flex:0 0 auto; color:var(--xc-accent-blue); }
.ir-advanced__field:not(.ir-advanced__field--slider) .ir-advanced__readonly { color:var(--xc-text-strong); font-size:var(--xc-fs-xs); }
.ir-advanced__value { display:inline-flex; align-items:baseline; justify-content:flex-end; gap:var(--xc-space-2); padding:0; background:transparent; }
.ir-advanced__number { width:7ch; height:24px; padding:0; border:0; background:transparent; color:var(--xc-text-default); caret-color:var(--xc-accent-blue); font-size:16px; font-weight:var(--xc-fw-semi); text-align:right; appearance:textfield; -moz-appearance:textfield; transition:color var(--xc-dur-fast),text-shadow var(--xc-dur-fast); }
.ir-advanced__number:hover { color:var(--xc-accent-blue); }
.ir-advanced__number:focus-visible { outline:none; color:var(--xc-accent-blue); text-shadow:var(--xc-glow-blue); }
.ir-advanced__select { min-width:96px; height:32px; padding:0 var(--xc-space-3); border:1px solid var(--xc-inline-border); border-radius:var(--xc-radius-sm); background:var(--xc-inline-bg); color:var(--xc-text-strong); color-scheme:dark; font-size:var(--xc-fs-xs); cursor:pointer; }
.ir-advanced__select option { background:var(--xc-surface-raised); color:var(--xc-text-strong); }
.ir-advanced__number::-webkit-inner-spin-button,.ir-advanced__number::-webkit-outer-spin-button { margin:0; -webkit-appearance:none; }
.ir-advanced__value small,.ir-advanced__readonly { color:var(--xc-text-mute); font-size:10px; }
.ir-advanced__value small { white-space:nowrap; transition:color var(--xc-dur-fast); }
.ir-advanced__value:hover small,.ir-advanced__value:focus-within small { color:var(--xc-text-soft); }
.ir-advanced__readonly { color:var(--xc-text-soft); white-space:nowrap; }
.ir-advanced__slider-wrap { position:relative; grid-column:3; min-width:0; width:100%; padding-top:18px; }
.ir-advanced__mark { position:absolute; top:0; left:clamp(28px,var(--mark-pct),calc(100% - 28px)); max-width:84px; overflow:hidden; color:var(--xc-text-mute); font-family:var(--xc-font-num); font-size:9px; line-height:1; pointer-events:none; text-overflow:ellipsis; white-space:nowrap; transform:translateX(-50%); }
.ir-advanced__mark::after { content:""; display:block; width:1px; height:7px; margin:3px auto 0; background:var(--xc-border-strong); }
.ir-advanced__slider { -webkit-appearance:none; appearance:none; width:100%; height:4px; margin:12px 0 16px; border-radius:var(--xc-radius-full); cursor:pointer; background:linear-gradient(90deg,var(--xc-accent-blue) var(--pct,0%),var(--xc-border-soft) var(--pct,0%)); transition:filter var(--xc-dur-base),box-shadow var(--xc-dur-base); }
.ir-advanced__slider:hover { filter:brightness(1.2); }
.ir-advanced__slider:focus-visible { outline:2px solid var(--xc-accent-blue); outline-offset:5px; box-shadow:var(--xc-glow-blue); }
.ir-advanced__slider::-webkit-slider-thumb { width:16px; height:16px; -webkit-appearance:none; appearance:none; border:3px solid var(--xc-accent-blue); border-radius:50%; background:var(--xc-text-strong); box-shadow:var(--xc-shadow-sm); transition:transform var(--xc-dur-base),box-shadow var(--xc-dur-base); }
.ir-advanced__slider::-moz-range-thumb { width:16px; height:16px; border:3px solid var(--xc-accent-blue); border-radius:50%; background:var(--xc-text-strong); transition:transform var(--xc-dur-base),box-shadow var(--xc-dur-base); }
.ir-advanced__slider:active::-webkit-slider-thumb { transform:scale(1.15); box-shadow:var(--xc-glow-blue); }
.ir-advanced__slider:active::-moz-range-thumb { transform:scale(1.15); box-shadow:var(--xc-glow-blue); }
.ir-advanced__input-hint { position:absolute; right:0; bottom:calc(100% + 10px); z-index:2; padding:6px 9px; border:1px solid var(--xc-border-strong); border-radius:var(--xc-radius-sm); background:var(--xc-surface-raised); box-shadow:var(--xc-shadow-sm); color:var(--xc-text-soft); font-size:var(--xc-fs-3xs); line-height:1.2; pointer-events:none; white-space:nowrap; }
.ir-advanced__range-labels { display:flex; justify-content:space-between; gap:var(--xc-space-3); margin-top:0; color:var(--xc-text-faint); font-size:10px; line-height:1; }
.ir-advanced__validation { grid-column:2 / 5; display:flex; align-items:center; justify-content:flex-end; gap:var(--xc-space-2); min-height:20px; margin-top:calc(var(--xc-space-2) * -1); color:var(--xc-status-danger); font-size:var(--xc-fs-2xs); font-weight:var(--xc-fw-semi); line-height:1.25; }
.ir-advanced__validation svg { width:14px; height:14px; flex:0 0 auto; }
.ir-advanced__delta-row { grid-column:4; display:flex; justify-content:flex-end; min-width:0; min-height:18px; margin-top:0; font-size:var(--xc-fs-3xs); }
.ir-advanced__delta { padding:1px var(--xc-space-2); border-radius:var(--xc-radius-full); font-weight:var(--xc-fw-semi); }
.ir-advanced__delta.up { color:var(--xc-status-ok); background:var(--xc-status-ok-soft); }
.ir-advanced__delta.down { color:var(--xc-status-danger); background:var(--xc-status-danger-soft); }
.ir-advanced__footer { display:flex; align-items:center; justify-content:space-between; gap:var(--xc-space-4); padding:var(--xc-space-5) var(--xc-space-6); border-top:1px solid var(--xc-border-soft); }
.ir-advanced__embedded-toolbar { display:flex; align-items:center; justify-content:space-between; gap:var(--xc-space-4); min-height:60px; padding:var(--xc-space-4) 0; border-bottom:1px solid var(--xc-border-soft); color:var(--xc-text-mute); font-size:var(--xc-fs-2xs); }
.ir-advanced__footer-actions { display:flex; justify-content:flex-end; gap:var(--xc-space-3); }
.ir-advanced__reset,.ir-advanced__cancel,.ir-advanced__save { min-height:36px; padding:0 16px; border-radius:8px; font-size:12px; cursor:pointer; }
.ir-advanced__embedded-toolbar .ir-advanced__reset { width:132px; padding-inline:0; }
.ir-advanced__reset,.ir-advanced__cancel { border:1px solid var(--xc-border-soft); background:transparent; color:var(--xc-text-soft); }
.ir-advanced__save { border:0; background:var(--xc-grad-brand); color:var(--xc-text-strong); }
.ir-advanced__save:disabled { cursor:not-allowed; opacity:.6; box-shadow:none; }
.ir-advanced__save:hover:not(:disabled),.ir-advanced__cancel:hover,.ir-advanced__reset:hover:not(:disabled) { box-shadow:var(--xc-glow-blue); }
.ir-advanced__reset:hover:not(:disabled) { border-color:var(--xc-border-accent); color:var(--xc-accent-blue); }
@container (max-width:760px) {
  .ir-advanced__field--slider { grid-template-columns:minmax(96px,140px) minmax(96px,auto) minmax(140px,1fr) minmax(70px,96px); gap:var(--xc-space-3); }
}
@media (max-width:560px) {
  .ir-advanced__mask { place-items:stretch; padding:var(--xc-space-3); }
  .ir-advanced { max-height:calc(100vh - var(--xc-space-2) * 2); }
  .ir-advanced__head,.ir-advanced__body,.ir-advanced__footer { padding-inline:var(--xc-space-5); }
  .ir-advanced__fields { grid-template-columns:1fr; }
  .ir-advanced__field--slider { grid-template-columns:minmax(0,1fr) auto; row-gap:var(--xc-space-2); min-height:96px; }
  .ir-advanced__field--slider .ir-advanced__field-label { grid-column:1; grid-row:1; }
  .ir-advanced__field--slider .ir-advanced__value { grid-column:2; grid-row:1; }
  .ir-advanced__field--slider .ir-advanced__slider-wrap { grid-column:1 / -1; grid-row:2; }
  .ir-advanced__field--slider .ir-advanced__delta-row { grid-column:1 / -1; grid-row:3; }
  .ir-advanced__field--slider .ir-advanced__validation { grid-column:1 / -1; justify-content:flex-end; }
  .ir-advanced__footer { align-items:stretch; flex-direction:column; }
  .ir-advanced__footer-actions { display:flex; width:100%; }
  .ir-advanced__reset { width:100%; }
  .ir-advanced__cancel,.ir-advanced__save { flex:1; }
  .ir-advanced__embedded-toolbar { align-items:stretch; flex-direction:column; }
}
@media (prefers-reduced-motion:reduce) {
  .ir-advanced__reset,.ir-advanced__slider,.ir-advanced__slider::-webkit-slider-thumb,.ir-advanced__slider::-moz-range-thumb { transition:none; }
}
</style>

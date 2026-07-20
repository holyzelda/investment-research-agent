<template>
  <div v-if="modelValue" class="ir-advanced__mask" @click.self="close">
    <section class="ir-advanced" role="dialog" aria-modal="true" aria-labelledby="advanced-param-title">
      <header class="ir-advanced__head">
        <div>
          <h3 id="advanced-param-title">高级参数</h3>
          <p>修改后暂存，点击“重新测算”时统一提交。</p>
        </div>
        <button class="ir-advanced__close" aria-label="关闭高级参数" @click="close">×</button>
      </header>

      <div class="ir-advanced__body">
        <section v-for="section in sections" :key="section.title" class="ir-advanced__section">
          <h4>{{ section.title }}</h4>
          <div class="ir-advanced__fields" :class="`ir-advanced__fields--${section.key}`">
            <div
              v-for="spec in section.items"
              :key="spec.id"
              class="ir-advanced__field"
              :class="{ 'ir-advanced__field--slider': isEditable(spec) && rangeOf(spec) }"
            >
              <div class="ir-advanced__field-head">
                <span>{{ spec.cn || spec.id }}</span>
                <select
                  v-if="spec.control === 'select'"
                  :data-param-id="spec.id"
                  v-model.number="values[spec.id]"
                  class="ir-advanced__select"
                >
                  <option v-for="option in spec.options || []" :key="option.value" :value="option.value">
                    {{ option.label }}
                  </option>
                </select>
                <span v-else-if="isEditable(spec)" class="ir-advanced__value">
                  <input
                    v-model.number="values[spec.id]"
                    class="ir-advanced__number"
                    type="number"
                    :min="rangeOf(spec)?.min"
                    :max="rangeOf(spec)?.max"
                    :step="spec.step"
                    @blur="roundField(spec)"
                  />
                  <small v-if="displayUnit(spec)">{{ displayUnit(spec) }}</small>
                </span>
                <span v-else class="ir-advanced__readonly xc-num">
                  {{ displayValue(spec) }}<template v-if="displayUnit(spec)"> {{ displayUnit(spec) }}</template>
                </span>
              </div>
              <input
                v-if="isEditable(spec) && rangeOf(spec)"
                v-model.number="values[spec.id]"
                class="ir-advanced__slider"
                type="range"
                :min="rangeOf(spec).min"
                :max="rangeOf(spec).max"
                :step="spec.step"
                :style="{ '--pct': pctOf(spec) + '%' }"
              />
              <div v-if="deltaOf(spec)" class="ir-advanced__delta-row">
                <span class="ir-advanced__delta" :class="deltaOf(spec).dir">{{ deltaOf(spec).text }}</span>
              </div>
            </div>
          </div>
        </section>
      </div>

      <footer class="ir-advanced__footer">
        <button class="ir-advanced__cancel" @click="close">取消</button>
        <button class="ir-advanced__save" @click="save">暂存修改</button>
      </footer>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { decimalsForStep, dynamicRange, roundToStep } from '@/utils/paramAdjust'
import { formatNumber } from '@/utils/formatNumber'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  paramDict: { type: Array, default: () => [] },
  seedInput: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['update:modelValue', 'save'])

const ADVANCED_SECTION_IDS = [
  { key: 'financial', title: '金融边界', ids: ['operation_years'] },
  { key: 'revenue', title: '收益边界', ids: ['mid_long_charge_avg', 'mid_long_discharge_avg', 'strategy_achievement_rate', 'capacity_achievement_rate'] },
  { key: 'cost', title: '成本边界', ids: ['battery_replace_cost', 'maint_cost', 'opex_cost'] },
]
const values = reactive({})

function resetValues() {
  Object.keys(values).forEach((key) => delete values[key])
  for (const spec of props.paramDict) {
    const value = spec.id in props.seedInput ? props.seedInput[spec.id] : spec.default
    values[spec.id] = typeof value === 'number' && spec.step ? roundToStep(value, spec.step) : value
  }
}
watch(() => [props.modelValue, props.seedInput, props.paramDict], resetValues, { immediate: true, deep: true })

const sections = computed(() => {
  const byId = new Map(props.paramDict.map((spec) => [spec.id, spec]))
  return ADVANCED_SECTION_IDS
    .map(({ key, title, ids }) => ({ key, title, items: ids.map((id) => byId.get(id)).filter(Boolean) }))
    .filter((section) => section.items.length)
})

function isEditable(spec) {
  return spec.control === 'slider' || spec.control === 'dynamic_slider' || spec.control === 'select'
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
  const baseline = spec.control === 'dynamic_slider' ? props.seedInput[spec.id] : spec.default
  const value = values[spec.id]
  if (typeof baseline !== 'number' || typeof value !== 'number') return null
  const delta = value - baseline
  if (Math.abs(delta) <= (spec.step || 0) / 2) return null
  return {
    dir: delta > 0 ? 'up' : 'down',
    text: `${delta > 0 ? '+' : ''}${delta.toFixed(decimalsForStep(spec.step))}${displayUnit(spec)}`,
  }
}
function roundField(spec) {
  if (typeof values[spec.id] === 'number') values[spec.id] = roundToStep(values[spec.id], spec.step)
}
function displayUnit(spec) {
  return spec.unit && spec.unit !== '—' ? spec.unit : ''
}
function displayValue(spec) {
  const value = values[spec.id]
  return value === null || value === undefined || value === '' ? '—' : formatNumber(value, decimalsForStep(spec.step))
}
function close() {
  emit('update:modelValue', false)
}
function save() {
  const overrides = {}
  for (const section of sections.value) {
    for (const spec of section.items) {
      if (!isEditable(spec) || spec.g !== 1 || values[spec.id] === null || values[spec.id] === undefined) continue
      overrides[spec.id] = values[spec.id]
    }
  }
  emit('save', overrides)
  close()
}
</script>

<style scoped>
.ir-advanced__mask { position:fixed; inset:0; z-index:var(--xc-z-modal); display:grid; place-items:center; padding:var(--xc-space-6); background:rgba(0,0,0,.58); backdrop-filter:blur(8px); }
.ir-advanced { width:min(680px,100%); max-height:min(760px,calc(100vh - 48px)); display:flex; flex-direction:column; overflow:hidden; border:1px solid rgba(255,255,255,.14); border-radius:var(--xc-radius-lg); background:var(--xc-surface-base); box-shadow:var(--xc-shadow-xl); }
.ir-advanced__head { display:flex; justify-content:space-between; gap:var(--xc-space-5); padding:var(--xc-space-6); border-bottom:1px solid var(--xc-border-soft); }
.ir-advanced__head h3 { margin:0; color:var(--xc-text-strong); font-size:var(--xc-fs-lg); font-weight:var(--xc-fw-semi); }
.ir-advanced__head p { margin:var(--xc-space-2) 0 0; color:var(--xc-text-mute); font-size:var(--xc-fs-xs); }
.ir-advanced__close { width:28px; height:28px; border:0; border-radius:var(--xc-radius-sm); background:transparent; color:var(--xc-text-mute); font-size:22px; line-height:1; cursor:pointer; }
.ir-advanced__close:hover { background:var(--xc-surface-2); color:var(--xc-text-strong); }
.ir-advanced__body { overflow-y:auto; padding:var(--xc-space-6); }
.ir-advanced__section + .ir-advanced__section { margin-top:var(--xc-space-7); }
.ir-advanced__section h4 { display:flex; align-items:center; gap:var(--xc-space-2); margin:0 0 var(--xc-space-4); color:var(--xc-text-strong); font-size:var(--xc-fs-sm); font-weight:var(--xc-fw-semi); }
.ir-advanced__section h4::before { content:''; width:4px; height:14px; border-radius:var(--xc-radius-full); background:var(--xc-accent-blue); }
.ir-advanced__fields { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:var(--xc-space-6) var(--xc-space-5); }
.ir-advanced__fields--revenue .ir-advanced__field:nth-child(n+3),.ir-advanced__fields--cost .ir-advanced__field { grid-column:1 / -1; width:min(280px,100%); }
.ir-advanced__field { min-width:0; }
.ir-advanced__field-head { display:flex; align-items:center; justify-content:space-between; min-height:28px; gap:var(--xc-space-3); color:var(--xc-text-soft); font-size:var(--xc-fs-xs); }
.ir-advanced__field:not(.ir-advanced__field--slider) .ir-advanced__field-head { justify-content:flex-start; min-height:52px; gap:var(--xc-space-5); padding:var(--xc-space-4) var(--xc-space-5); border-left:2px solid var(--xc-border-accent); border-radius:0 var(--xc-radius-sm) var(--xc-radius-sm) 0; background:rgba(255,255,255,.025); }
.ir-advanced__field:not(.ir-advanced__field--slider) .ir-advanced__readonly { color:var(--xc-text-strong); font-size:var(--xc-fs-xs); }
.ir-advanced__value { display:inline-flex; align-items:center; gap:2px; }
.ir-advanced__number { width:62px; height:24px; padding:0 var(--xc-space-2); border:1px solid transparent; border-radius:var(--xc-radius-sm); background:transparent; color:var(--xc-text-strong); font-size:var(--xc-fs-sm); font-weight:var(--xc-fw-semi); text-align:center; appearance:textfield; -moz-appearance:textfield; }
.ir-advanced__select { min-width:88px; height:28px; padding:0 var(--xc-space-2); border:1px solid var(--xc-border-soft); border-radius:var(--xc-radius-sm); background:var(--xc-surface-2); color:var(--xc-text-strong); font-size:var(--xc-fs-xs); cursor:pointer; }
.ir-advanced__select:focus { outline:none; border-color:var(--xc-border-accent); }
.ir-advanced__number:hover,.ir-advanced__number:focus { outline:none; border-color:var(--xc-border-accent); background:rgba(255,255,255,.04); }
.ir-advanced__number::-webkit-inner-spin-button,.ir-advanced__number::-webkit-outer-spin-button { margin:0; -webkit-appearance:none; }
.ir-advanced__value small,.ir-advanced__readonly { color:var(--xc-text-mute); font-size:var(--xc-fs-3xs); }
.ir-advanced__readonly { color:var(--xc-text-soft); }
.ir-advanced__slider { -webkit-appearance:none; appearance:none; width:100%; height:4px; margin-top:var(--xc-space-4); border-radius:var(--xc-radius-full); cursor:pointer; background:linear-gradient(90deg,var(--xc-accent-blue) var(--pct,0%),rgba(255,255,255,.12) var(--pct,0%)); }
.ir-advanced__slider::-webkit-slider-thumb { width:14px; height:14px; -webkit-appearance:none; appearance:none; border:3px solid var(--xc-accent-blue); border-radius:50%; background:#fff; box-shadow:var(--xc-shadow-sm); }
.ir-advanced__slider::-moz-range-thumb { width:14px; height:14px; border:3px solid var(--xc-accent-blue); border-radius:50%; background:#fff; }
.ir-advanced__delta-row { display:flex; justify-content:flex-end; min-height:16px; margin-top:var(--xc-space-2); font-size:var(--xc-fs-3xs); }
.ir-advanced__delta { padding:1px var(--xc-space-2); border-radius:var(--xc-radius-full); font-weight:var(--xc-fw-semi); }
.ir-advanced__delta.up { color:var(--xc-status-ok); background:var(--xc-status-ok-soft); }
.ir-advanced__delta.down { color:var(--xc-status-danger); background:var(--xc-status-danger-soft); }
@media (max-width:560px) { .ir-advanced__fields { grid-template-columns:1fr; } .ir-advanced__fields--revenue .ir-advanced__field:nth-child(n+3),.ir-advanced__fields--cost .ir-advanced__field { grid-column:auto; width:100%; } }
.ir-advanced__footer { display:flex; justify-content:flex-end; gap:var(--xc-space-3); padding:var(--xc-space-5) var(--xc-space-6); border-top:1px solid var(--xc-border-soft); }
.ir-advanced__cancel,.ir-advanced__save { height:34px; padding:0 var(--xc-space-5); border-radius:var(--xc-radius-md); font-size:var(--xc-fs-xs); cursor:pointer; }
.ir-advanced__cancel { border:1px solid var(--xc-border-soft); background:transparent; color:var(--xc-text-soft); }
.ir-advanced__save { border:0; background:var(--xc-grad-brand); color:#fff; }
</style>

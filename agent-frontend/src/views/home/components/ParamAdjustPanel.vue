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
        <span class="ir-adjust__caret" :class="{ 'is-open': expanded }" aria-hidden="true">▸</span>
        <span class="ir-adjust__heading-copy">
          <strong>调整参数并重新测算</strong>
          <small>修改当前版本参数，生成新的测算版本</small>
        </span>
      </button>
      <button
        ref="advancedTrigger"
        class="ir-adjust__advanced"
        type="button"
        :disabled="responding"
        :aria-label="advancedButtonLabel"
        @click="$emit('open-advanced')"
      >
        <span>高级参数</span>
        <span v-if="advancedOverrideCount > 0" class="ir-adjust__draft-count xc-num">{{ advancedOverrideCount }}</span>
        <span aria-hidden="true">›</span>
      </button>
    </div>

    <div v-if="expanded" id="ir-adjust-panel-body" class="ir-adjust__body">
      <section
        v-for="group in zoneGroups"
        :key="group.zone"
        class="ir-adjust__zone"
        :class="`ir-adjust__zone--${group.zone}`"
      >
        <h5 class="ir-adjust__zone-title">{{ group.label }}</h5>
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
              <!-- 项目信息：仅当该省存在节点时显示节点选择卡；节点来源于 ir_spot_station。 -->
              <template v-if="spec.id === 'node_name'">
                <span class="ir-adjust__label">节点名称</span>
                <select v-model="localValues.node_name" class="ir-adjust__select">
                  <option v-for="station in stationOptions" :key="station" :value="station">{{ station }}</option>
                </select>
              </template>

              <!-- 永久/本阶段锁定：只读展示 -->
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
                    v-model.number="localValues[spec.id]"
                    type="number"
                    class="ir-adjust__number"
                    @blur="roundField(spec)"
                  />
                  <small v-if="displayUnit(spec)">{{ displayUnit(spec) }}</small>
                </span>
              </template>

              <!-- 固定范围 / 基准值±100% 动态滑块 -->
              <template v-else-if="spec.control === 'slider' || spec.control === 'dynamic_slider'">
                <div v-if="rangeOf(spec)" class="pslider">
                  <div class="ps-top">
                    <span class="ps-label">{{ spec.cn || spec.id }}</span>
                    <span class="ps-val xc-num">
                      <input
                        v-model.number="localValues[spec.id]"
                        type="number"
                        :min="rangeOf(spec).min" :max="rangeOf(spec).max" :step="spec.step"
                        class="ir-adjust__number ps-val-input"
                        @blur="roundField(spec)"
                      />
                      <small v-if="displayUnit(spec)">{{ displayUnit(spec) }}</small>
                    </span>
                  </div>
                  <input
                    v-model.number="localValues[spec.id]"
                    type="range"
                    :min="rangeOf(spec).min" :max="rangeOf(spec).max" :step="spec.step"
                    class="ir-adjust__slider"
                    :style="{ '--pct': pctOf(spec) + '%' }"
                  />
                  <div v-if="deltaOf(spec)" class="ps-foot">
                    <span class="ps-delta" :class="deltaOf(spec).dir">{{ deltaOf(spec).text }}</span>
                  </div>
                </div>
                <span v-else class="ir-adjust__pending">数据待完善</span>
              </template>
            </div>
          </div>
        </div>
      </section>

      <div class="ir-adjust__footer">
        <span v-if="advancedOverrideCount > 0" class="ir-adjust__draft-note">
          {{ advancedOverrideCount }} 项高级修改将在重新测算时生效
        </span>
        <button class="ir-adjust__submit" type="button" :disabled="responding" @click="onSubmit">
          {{ responding ? '测算中…' : '重新测算' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import {
  buildOverrides,
  decimalsForStep,
  dynamicRange,
  groupByZone,
  isFieldLocked,
  roundToStep,
} from '@/utils/paramAdjust'
import { formatNumber } from '@/utils/formatNumber'

const props = defineProps({
  paramDict: { type: Array, default: () => [] },
  switches: { type: Object, default: () => ({}) },
  seedInput: { type: Object, default: () => ({}) },
  stationOptions: { type: Array, default: () => [] },
  advancedOverrides: { type: Object, default: () => ({}) },
  advancedOverrideCount: { type: Number, default: 0 },
  version: { type: String, default: '' },
  responding: { type: Boolean, default: false },
})
const emit = defineEmits(['recalculate', 'open-advanced'])

const expanded = ref(false)
const advancedTrigger = ref(null)
const localValues = reactive({})
const advancedButtonLabel = computed(() => props.advancedOverrideCount > 0
  ? `高级参数，已暂存 ${props.advancedOverrideCount} 项修改`
  : '高级参数')

const PROJECT_ORDER = ['province', 'node_name', 'power_mw', 'capacity_mwh']
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
  Object.keys(localValues).forEach((k) => delete localValues[k])
  for (const spec of props.paramDict) {
    let value = spec.id in props.seedInput ? props.seedInput[spec.id] : spec.default
    if (typeof value === 'number' && spec.step) value = roundToStep(value, spec.step)
    localValues[spec.id] = value
  }
}
watch(() => props.seedInput, resetLocalValues, { immediate: true })

const zoneGroups = computed(() => groupByZone(props.paramDict, props.switches)
  .map((group) => {
    let items = group.items.filter((spec) => !DROPPED_FIELDS.has(spec.id))
    if (group.zone === 'project_definition') {
      items = items.filter((spec) => spec.id !== 'node_name' || props.stationOptions.length > 0)
      items = [...items].sort((a, b) => PROJECT_ORDER.indexOf(a.id) - PROJECT_ORDER.indexOf(b.id))
    }
    return { ...group, label: group.zone === 'project_definition' ? '项目信息' : group.label, items }
  })
  .filter((group) => group.items.length))

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
  const baseline = spec.control === 'dynamic_slider' ? props.seedInput[spec.id] : spec.default
  const value = localValues[spec.id]
  if (typeof baseline !== 'number' || typeof value !== 'number') return null
  const delta = value - baseline
  if (Math.abs(delta) <= (spec.step || 0) / 2) return null
  return {
    dir: delta > 0 ? 'up' : 'down',
    text: `${delta > 0 ? '+' : ''}${delta.toFixed(decimalsForStep(spec.step))}${displayUnit(spec)}`,
  }
}
function formatSpecValue(spec, value) { return formatNumber(value, decimalsForStep(spec.step)) }
function displayUnit(spec) { return spec.unit && spec.unit !== '—' ? spec.unit : '' }
function roundField(spec) {
  if (typeof localValues[spec.id] === 'number') localValues[spec.id] = roundToStep(localValues[spec.id], spec.step)
}
function onSubmit() {
  emit('recalculate', {
    overrides: { ...buildOverrides(props.paramDict, localValues), ...props.advancedOverrides },
    basics: {
      node_name: localValues.node_name || null,
      capacity_mwh: localValues.capacity_mwh,
      power_mw: localValues.power_mw,
    },
  })
}
function focusAdvancedTrigger() {
  advancedTrigger.value?.focus()
}
defineExpose({ focusAdvancedTrigger })
</script>

<style scoped>
.ir-adjust { margin: var(--xc-space-5) var(--xc-space-6) var(--xc-space-6); border: 1px solid var(--xc-border-card); border-radius: var(--xc-radius-lg); background: var(--xc-surface-card); box-shadow: var(--xc-shadow-sm); backdrop-filter: blur(var(--xc-blur-sm)); overflow: hidden; }
.ir-adjust__header { display:flex; align-items:center; justify-content:space-between; gap:var(--xc-space-4); padding:var(--xc-space-5); }
.ir-adjust__toggle { display:flex; align-items:center; gap:var(--xc-space-3); min-width:0; padding:0; border:0; background:transparent; color:var(--xc-text-soft); text-align:left; cursor:pointer; }
.ir-adjust__heading-copy { display:grid; gap:var(--xc-space-1); }
.ir-adjust__heading-copy strong { color:var(--xc-text-default); font-size:var(--xc-fs-sm); font-weight:var(--xc-fw-semi); }
.ir-adjust__heading-copy small { color:var(--xc-text-mute); font-size:var(--xc-fs-2xs); font-weight:var(--xc-fw-regular); }
.ir-adjust__toggle:hover:not(:disabled) strong { color:var(--xc-text-strong); }
.ir-adjust__toggle:focus-visible,.ir-adjust__advanced:focus-visible,.ir-adjust__submit:focus-visible { outline:2px solid var(--xc-accent-blue); outline-offset:2px; }
.ir-adjust__toggle:disabled,.ir-adjust__advanced:disabled,.ir-adjust__submit:disabled { cursor:not-allowed; opacity:.6; }
.ir-adjust__caret { flex:0 0 auto; color:var(--xc-accent-blue); transition:transform var(--xc-dur-fast) var(--xc-ease-out); }
.ir-adjust__caret.is-open { transform:rotate(90deg); }
.ir-adjust__advanced { display:inline-flex; align-items:center; gap:var(--xc-space-2); min-height:36px; flex:0 0 auto; padding:0 var(--xc-space-4); border:1px solid var(--xc-border-accent); border-radius:var(--xc-radius-full); background:var(--xc-accent-blue-soft); color:var(--xc-accent-blue); font-size:var(--xc-fs-xs); cursor:pointer; transition:border-color var(--xc-dur-base),box-shadow var(--xc-dur-base),transform var(--xc-dur-base); }
.ir-adjust__advanced:hover:not(:disabled) { border-color:var(--xc-accent-blue); box-shadow:var(--xc-glow-blue); transform:translateY(-1px); }
.ir-adjust__draft-count { display:grid; place-items:center; min-width:20px; height:20px; padding:0 var(--xc-space-1); border-radius:var(--xc-radius-full); background:var(--xc-accent-blue); color:var(--xc-text-inverse); font-size:var(--xc-fs-3xs); font-weight:var(--xc-fw-bold); }
.ir-adjust__body { padding: 0 var(--xc-space-5) var(--xc-space-5); }
.ir-adjust__zone { padding:var(--xc-space-7) 0 var(--xc-space-6); border-top:1px solid var(--xc-border-soft); }
.ir-adjust__zone-title { display:flex; align-items:center; gap:var(--xc-space-3); font-size:var(--xc-fs-sm); font-weight:var(--xc-fw-semi); color:var(--xc-text-strong); margin:0 0 var(--xc-space-5); }
.ir-adjust__zone-title::before { content:''; width:3px; height:16px; border-radius:var(--xc-radius-full); background:var(--xc-accent-blue); box-shadow:var(--xc-glow-blue); }

/* 行式布局：一行一项 = 半宽单独一行；一行多项 = 并排共享一行。行间距拉开，避免相邻两组滑块显得局促。 */
.ir-adjust__rows { display:flex; flex-direction:column; gap: var(--xc-space-7); }
.ir-adjust__row { display:flex; gap: var(--xc-space-6); align-items:flex-start; }
.ir-adjust__row .ir-adjust__field { flex:1 1 0; min-width:0; }
.ir-adjust__row--single .ir-adjust__field { flex:0 1 auto; width: calc(50% - var(--xc-space-3)); }

/* 项目信息使用轻量数据网格，不再叠加独立卡片背景。 */
.ir-adjust__row--project { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:var(--xc-space-5); }
.ir-adjust__row--project .ir-adjust__field { width:auto; }

.ir-adjust__field { min-width:0; display:flex; flex-direction:column; gap:var(--xc-space-2); }
.ir-adjust__project-item {
  min-height:64px;
  justify-content:center;
  padding-left:var(--xc-space-4);
  border-left:2px solid var(--xc-border-accent);
}
.ir-adjust__project-item .ir-adjust__number-value { justify-content:flex-start; }
.ir-adjust__project-item .ir-adjust__number {
  width:72px;
  padding:0;
  border-color:transparent;
  background:transparent;
  color:var(--xc-text-strong);
  font-family:var(--xc-font-num);
  font-size:var(--xc-fs-lg);
  font-weight:var(--xc-fw-semi);
  text-align:left;
}
.ir-adjust__project-item .ir-adjust__number:hover { border-bottom-color:var(--xc-border-accent); }
.ir-adjust__project-item .ir-adjust__ro { font-size:var(--xc-fs-lg); font-weight:var(--xc-fw-semi); color:var(--xc-text-strong); }
.ir-adjust__project-item .ir-adjust__label { font-size:var(--xc-fs-2xs); }
.ir-adjust__label { font-size:var(--xc-fs-xs); color:var(--xc-text-mute); }
.ir-adjust__number-value { display:inline-flex; align-items:baseline; gap:var(--xc-space-2); color:var(--xc-text-strong); }
.ir-adjust__number-value small { color:var(--xc-text-mute); font-size:var(--xc-fs-xs); }
.ir-adjust__ro { font-size:var(--xc-fs-sm); color:var(--xc-text-soft); }
.ir-adjust__pending { font-size:var(--xc-fs-xs); color:var(--xc-text-faint); }

.pslider { display:flex; flex-direction:column; gap: var(--xc-space-4); padding-top: var(--xc-space-1); }
.ps-top { display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:center; gap:var(--xc-space-4); }
.ps-label { min-width:0; font-size:var(--xc-fs-xs); color:var(--xc-text-soft); }
.ps-val { display:inline-flex; align-items:baseline; justify-content:flex-end; gap:2px; min-width:112px; padding:var(--xc-space-2) var(--xc-space-3); border:1px solid var(--xc-border-accent); border-radius:var(--xc-radius-sm); background:var(--xc-surface-tinted); }
.ps-val small { font-size:var(--xc-fs-3xs); color:var(--xc-text-mute); white-space:nowrap; }
.ir-adjust__slider { -webkit-appearance:none; appearance:none; width:100%; height:4px; border-radius:var(--xc-radius-full); cursor:pointer; background:linear-gradient(90deg,var(--xc-accent-blue) var(--pct,0%),var(--xc-border-soft) var(--pct,0%)); transition:filter var(--xc-dur-base),box-shadow var(--xc-dur-base); }
.ir-adjust__slider:hover { filter:brightness(1.2); }
.ir-adjust__slider:focus-visible { outline:2px solid var(--xc-accent-blue); outline-offset:5px; box-shadow:var(--xc-glow-blue); }
.ir-adjust__slider::-webkit-slider-thumb { -webkit-appearance:none; appearance:none; width:16px; height:16px; border-radius:50%; background:var(--xc-text-strong); border:3px solid var(--xc-accent-blue); box-shadow:var(--xc-shadow-sm); cursor:pointer; transition:transform var(--xc-dur-base),box-shadow var(--xc-dur-base); }
.ir-adjust__slider::-moz-range-thumb { width:12px; height:12px; border-radius:50%; background:var(--xc-text-strong); border:3px solid var(--xc-accent-blue); cursor:pointer; transition:transform var(--xc-dur-base),box-shadow var(--xc-dur-base); }
.ir-adjust__slider:active::-webkit-slider-thumb { transform:scale(1.15); box-shadow:var(--xc-glow-blue); }
.ir-adjust__slider:active::-moz-range-thumb { transform:scale(1.15); box-shadow:var(--xc-glow-blue); }
.ps-foot { display:flex; justify-content:flex-end; min-height:16px; font-size:var(--xc-fs-3xs); }
.ps-delta { font-weight:var(--xc-fw-semi); padding:1px var(--xc-space-2); border-radius:var(--xc-radius-full); }
.ps-delta.up { color:var(--xc-status-ok); background:var(--xc-status-ok-soft); }
.ps-delta.down { color:var(--xc-status-danger); background:var(--xc-status-danger-soft); }
.ir-adjust__number,.ir-adjust__select,.ir-adjust__text { width:100%; height:32px; padding:0 var(--xc-space-2); border:1px solid var(--xc-inline-border); border-radius:var(--xc-radius-sm); background:var(--xc-inline-bg); color:var(--xc-text-default); font-size:var(--xc-fs-sm); text-align:center; -moz-appearance:textfield; appearance:textfield; }
.ir-adjust__number::-webkit-inner-spin-button,.ir-adjust__number::-webkit-outer-spin-button { -webkit-appearance:none; margin:0; }
.ps-val-input { width:68px; height:22px; border:0; background:transparent; font-size:var(--xc-fs-md); font-weight:var(--xc-fw-semi); color:var(--xc-text-strong); padding:0; }
.ir-adjust__number:focus-visible,.ir-adjust__select:focus-visible,.ir-adjust__text:focus-visible { outline:2px solid var(--xc-accent-blue); outline-offset:2px; border-color:var(--xc-border-accent); }
.ir-adjust__footer { display:flex; justify-content:flex-end; align-items:center; gap:var(--xc-space-4); padding-top:var(--xc-space-5); border-top:1px solid var(--xc-border-soft); }
.ir-adjust__draft-note { margin-right:auto; color:var(--xc-text-mute); font-size:var(--xc-fs-2xs); }
.ir-adjust__submit { min-height:40px; padding:0 var(--xc-space-6); border:0; border-radius:var(--xc-radius-md); background:var(--xc-grad-brand); color:var(--xc-text-strong); font-size:var(--xc-fs-sm); cursor:pointer; transition:transform var(--xc-dur-base),box-shadow var(--xc-dur-base); }
.ir-adjust__submit:hover:not(:disabled) { transform:translateY(-1px); box-shadow:var(--xc-glow-blue); }
@media (max-width:900px) { .ir-adjust__row--project { grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media (max-width:640px) {
  .ir-adjust { margin-inline:var(--xc-space-4); }
  .ir-adjust__header { align-items:flex-start; flex-wrap:wrap; }
  .ir-adjust__advanced { margin-left:auto; }
  .ir-adjust__row { flex-direction:column; }
  .ir-adjust__row--single .ir-adjust__field { width:100%; }
  .ir-adjust__row--project { grid-template-columns:1fr; width:100%; }
  .ir-adjust__row--project .ir-adjust__field { width:100%; }
  .ir-adjust__footer { align-items:stretch; flex-direction:column; }
  .ir-adjust__draft-note { margin-right:0; }
  .ir-adjust__submit { width:100%; }
}
@media (prefers-reduced-motion:reduce) {
  .ir-adjust__caret,.ir-adjust__advanced,.ir-adjust__submit,.ir-adjust__slider,.ir-adjust__slider::-webkit-slider-thumb,.ir-adjust__slider::-moz-range-thumb { transition:none; }
}
</style>

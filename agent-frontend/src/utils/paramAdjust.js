// 参数调整区纯逻辑（Batch5）：四区分组、市场开关统一显隐、动态区间、锁项规则、提交值收集。
// 不依赖 Vue，便于直接单测；ParamAdjustPanel.vue 只负责渲染与交互。

export const ZONE_ORDER = ['project_definition', 'financial_boundary', 'revenue_boundary', 'cost_boundary']

export const ZONE_LABEL = {
  project_definition: '项目定义',
  financial_boundary: '金融边界',
  revenue_boundary: '收益边界',
  cost_boundary: '成本边界',
}

// 收益类参数 -> 决定其显隐的省级市场开关（PRD 2026-07-15 确认：现货与其他市场统一按开关显隐）
const MARKET_SWITCH_OF = {
  spot_charge_avg: 'switch_spot',
  spot_discharge_avg: 'switch_spot',
  mid_long_energy_revenue_first_year_tax: 'switch_mid_long',
  frequency_first_year_revenue: 'switch_frequency',
  intervention_first_year_revenue: 'switch_intervention',
  lease_unit_price: 'switch_lease',
  lease_achievement_rate: 'switch_lease',
}

export function isVisible(spec, switches) {
  const switchId = MARKET_SWITCH_OF[spec.id]
  if (!switchId) return true
  return (switches || {})[switchId] === 1
}

// 按四区分组；无 zone/control 的参数（输出项等）不进入调整区；市场开关关闭的项目被过滤；
// 分组内没有任何可展示项时该区不出现。
export function groupByZone(paramDict, switches) {
  const buckets = {}
  for (const spec of paramDict) {
    if (!spec.zone || !spec.control) continue
    if (!isVisible(spec, switches)) continue
    ;(buckets[spec.zone] ||= []).push(spec)
  }
  return ZONE_ORDER
    .filter((zone) => buckets[zone]?.length)
    .map((zone) => ({ zone, label: ZONE_LABEL[zone], items: buckets[zone] }))
}

// 动态区间：以上一版本冻结值为基准，0~2倍；基准为 0/null/undefined 视为数据待完善，不可调。
export function dynamicRange(baseline, step) {
  if (baseline === null || baseline === undefined || baseline === 0) return null
  const max = Number((Math.abs(baseline) * 2).toFixed(6))
  return { min: 0, max, step }
}

// 轨道上的冻结值基准：优先取本次测算冻结输入，无冻结值时回退参数默认值。
export function frozenBaseline(spec, seedInput = {}) {
  const seed = seedInput?.[spec.id]
  if (typeof seed === 'number' && Number.isFinite(seed)) return seed
  return typeof spec.default === 'number' && Number.isFinite(spec.default) ? spec.default : null
}

export function frozenMarkerPct(range, baseline) {
  if (!range || range.max === range.min || typeof baseline !== 'number' || !Number.isFinite(baseline)) return null
  const clamped = Math.min(range.max, Math.max(range.min, baseline))
  return ((clamped - range.min) / (range.max - range.min)) * 100
}

// variants 分档解析：参数字典把某参数的 control/default/min/max/step 按另一参数（如 operation_years）
// 的取值分档（variants: { "15": {...}, "20": {...} }）。命中当前取值时浅合并覆盖基础定义，
// 未命中或没有 variants 时返回原 spec。返回的可能是新对象，调用方不得依赖引用相等。
export function resolveVariant(spec, operationYears) {
  const variants = spec.variants
  if (!variants) return spec
  const key = operationYears === null || operationYears === undefined ? undefined : String(operationYears)
  const variant = key ? variants[key] : undefined
  if (!variant) return spec
  return { ...spec, ...variant }
}

// 仅参数字典声明为 fixed 的字段锁定；省份等固定字段保持只读，
// 节点、容量和功率在所有版本均可编辑。
export function isFieldLocked(spec) {
  return spec.control === 'fixed'
}

// 提交当前面板改动值：仅收集 slider/dynamic_slider/select 控件中与 seedInput 基线不同的值，
// 实现"用户改了哪些就提交哪些"的增量语义。
// seedInput 默认为空字典，未提供时所有值均视为非基线而提交（兼容无基线场景）。
export function buildOverrides(paramDict, values, seedInput = {}) {
  const overrides = {}
  for (const spec of paramDict) {
    if (!['slider', 'dynamic_slider', 'select'].includes(spec.control)) continue
    if (!(spec.id in values)) continue
    const baseline = spec.id in seedInput ? seedInput[spec.id] : spec.default
    if (values[spec.id] !== baseline) {
      overrides[spec.id] = values[spec.id]
    }
  }
  return overrides
}

// 展示 / 输入精度：由 step 的小数位数决定（如现货充放电价格 step=0.0001 → 4 位），
// 避免默认按浮点全精度展示（如 0.6099999999999999）。step 为整数或缺失时按 0 位（整数）处理。
export function decimalsForStep(step) {
  if (step === null || step === undefined) return 0
  const str = String(step)
  const dot = str.indexOf('.')
  return dot === -1 ? 0 : str.length - dot - 1
}

// 按 step 精度四舍五入，修正浮点误差；非数字原样返回（如省份等字符串只读项）。
export function roundToStep(value, step) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return value
  return Number(value.toFixed(decimalsForStep(step)))
}

// 数字输入统一校验：组件保留原始文本，只在 valid=true 时更新业务值。
// range 为空时仅校验是否为有限数，适用于装机功率/容量等普通数字字段。
export function validateNumericInput(rawValue, range = null) {
  if (rawValue === '' || rawValue === null || rawValue === undefined) {
    return { valid: false, value: null, reason: 'invalid' }
  }
  const value = Number(rawValue)
  if (!Number.isFinite(value)) return { valid: false, value: null, reason: 'invalid' }
  if (range && value < range.min) return { valid: false, value, reason: 'min', limit: range.min }
  if (range && value > range.max) return { valid: false, value, reason: 'max', limit: range.max }
  return { valid: true, value, reason: null }
}

export function numericInputError(result, formatLimit = String, unit = '') {
  if (result.valid) return ''
  if (result.reason === 'min') return `不能低于 ${formatLimit(result.limit)}${unit}`
  if (result.reason === 'max') return `不能高于 ${formatLimit(result.limit)}${unit}`
  return '请输入有效数值'
}

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

// 锁项：control=fixed 的参数（省份/运营期/换电成本，本阶段业务范围未开放）始终锁定；
// 项目定义区其余字段（节点/容量/功率）仅首次测算锁定，二次起解锁；其余分区不受首二次限制。
export function isFieldLocked(spec, { firstCalc }) {
  if (spec.control === 'fixed') return true
  if (spec.zone === 'project_definition') return firstCalc
  return false
}

// 提交当前完整面板值：仅收集 slider/dynamic_slider/select 控件的当前值作为受控 overrides，
// 是否真的查库由后端按现货依赖规则决定，前端始终提交面板当前值。
export function buildOverrides(paramDict, values) {
  const overrides = {}
  for (const spec of paramDict) {
    if (!['slider', 'dynamic_slider', 'select'].includes(spec.control)) continue
    if (!(spec.id in values)) continue
    overrides[spec.id] = values[spec.id]
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

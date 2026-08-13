const CATEGORY_BY_ZONE = {
  project_definition: 'basic',
  financial_boundary: 'advanced',
  revenue_boundary: 'editable',
  cost_boundary: 'editable',
}

const CATEGORY_ORDER = ['basic', 'editable', 'advanced']
const CATEGORY_LABELS = {
  basic: '项目基本信息',
  editable: '可修改参数',
  advanced: '高级参数',
}

const ADVANCED_IDS = new Set([
  'operation_years', 'mid_long_charge_avg', 'mid_long_discharge_avg',
  'strategy_achievement_rate', 'capacity_achievement_rate',
  'battery_replace_cost', 'maint_cost', 'opex_cost',
])

const METRIC_META = {
  projectIrr: { unit: '个百分点', direction: 'higher-is-better', format: (value) => `${value} 个百分点` },
  capitalIrr: { unit: '个百分点', direction: 'higher-is-better', format: (value) => `${value} 个百分点` },
  averageProfit: { unit: '万元', direction: 'higher-is-better', format: (value) => `${value} 万元` },
  projectStaticPayback: { unit: '年', direction: 'lower-is-better', format: (value) => `${value} 年` },
  capitalStaticPayback: { unit: '年', direction: 'lower-is-better', format: (value) => `${value} 年` },
}

export const CATEGORY_LABEL = CATEGORY_LABELS

export function normalizeComparableValue(value) {
  if (value === null || value === undefined || value === '') return null
  if (typeof value === 'number') return Number(value.toFixed(8))
  if (typeof value === 'string' && value.trim() !== '' && Number.isFinite(Number(value))) {
    return Number(Number(value).toFixed(8))
  }
  return value
}

function changed(oldValue, newValue) {
  return normalizeComparableValue(oldValue) !== normalizeComparableValue(newValue)
}

function labelFor(spec, id) {
  return spec?.cn || spec?.label || spec?.name || id
}

function categoryFor(spec, id) {
  if (ADVANCED_IDS.has(id)) return 'advanced'
  if (spec?.category && CATEGORY_LABELS[spec.category]) return spec.category
  return CATEGORY_BY_ZONE[spec?.zone] || (['power_mw', 'capacity_mwh', 'province', 'node_name', 'voltage_kv'].includes(id) ? 'basic' : 'editable')
}

export function diffVersionInputs(currentInput = {}, compareInput = {}, changeMeta = {}, paramDict = []) {
  const specs = new Map((paramDict || []).map((spec) => [spec.id, spec]))
  const knownIds = (paramDict || []).map((spec) => spec.id)
  const extraIds = [...new Set([...Object.keys(currentInput || {}), ...Object.keys(compareInput || {})])]
    .filter((id) => !specs.has(id))
    .sort()
  const ids = [...knownIds, ...extraIds]
  const explicit = new Set(changeMeta.explicitOverrideKeys || [])
  const derived = new Set(changeMeta.derivedChangedKeys || [])
  const groups = CATEGORY_ORDER.map((category) => ({ category, label: CATEGORY_LABELS[category], items: [] }))

  for (const id of ids) {
    const oldValue = compareInput?.[id]
    const newValue = currentInput?.[id]
    if (!changed(oldValue, newValue)) continue
    const spec = specs.get(id)
    const category = categoryFor(spec, id)
    const source = explicit.has(id) ? 'explicit' : derived.has(id) ? 'derived' : 'unknown'
    groups.find((group) => group.category === category).items.push({
      id,
      label: labelFor(spec, id),
      oldValue,
      newValue,
      source,
    })
  }

  const populated = groups.filter((group) => group.items.length)
  return {
    groups: populated,
    totalCount: populated.reduce((sum, group) => sum + group.items.length, 0),
    explicitCount: populated.reduce((sum, group) => sum + group.items.filter((item) => item.source === 'explicit').length, 0),
    derivedCount: populated.reduce((sum, group) => sum + group.items.filter((item) => item.source === 'derived').length, 0),
  }
}

export function getMetricDelta(key, currentValue, compareValue) {
  const current = normalizeComparableValue(currentValue)
  const compare = normalizeComparableValue(compareValue)
  const meta = METRIC_META[key]
  if (!meta || typeof current !== 'number' || typeof compare !== 'number') {
    return { delta: null, direction: 'flat', tone: 'neutral', text: '', icon: 'flat' }
  }
  const rawDelta = Number((current - compare).toFixed(4))
  if (rawDelta === 0) return { delta: 0, direction: 'flat', tone: 'neutral', text: '', icon: 'flat' }
  const direction = rawDelta > 0 ? 'up' : 'down'
  const improves = meta.direction === 'higher-is-better' ? rawDelta > 0 : rawDelta < 0
  const magnitude = Math.abs(rawDelta)
  return {
    delta: rawDelta,
    direction,
    tone: improves ? 'good' : 'bad',
    text: `${rawDelta > 0 ? '增加' : '减少'} ${meta.format(magnitude)}`,
    icon: direction,
  }
}

function compactSource(items) {
  const labels = items.slice(0, 2).map((item) => item.label)
  return {
    count: items.length,
    labels: labels.length < items.length ? [...labels, `等 ${items.length} 项`] : labels,
  }
}

export function buildArchiveSummary(currentVersion, previousVersion, paramDict = []) {
  if (!currentVersion || !previousVersion) {
    return { previousVersion: null, projectIrr: currentVersion?.result?.financial?.projectIrr ?? null, explicit: { count: 0, labels: [] }, derived: { count: 0, labels: [] }, initial: true }
  }
  const diff = diffVersionInputs(currentVersion.input, previousVersion.input, currentVersion.changeMeta, paramDict)
  const explicitItems = diff.groups.flatMap((group) => group.items.filter((item) => item.source === 'explicit'))
  const derivedItems = diff.groups.flatMap((group) => group.items.filter((item) => item.source === 'derived'))
  return {
    previousVersion: previousVersion.version,
    projectIrr: currentVersion.result?.financial?.projectIrr ?? null,
    explicit: compactSource(explicitItems),
    derived: compactSource(derivedItems),
    initial: false,
  }
}

import { beforeEach, describe, expect, it } from 'vitest'
import {
  buildOverrides,
  decimalsForStep,
  dynamicRange,
  groupByZone,
  isFieldLocked,
  isVisible,
  resolveVariant,
  roundToStep,
} from '@/utils/paramAdjust'

const PARAM_DICT = [
  { id: 'province', zone: 'project_definition', control: 'fixed' },
  { id: 'node_name', zone: 'project_definition', control: 'text' },
  { id: 'capacity_mwh', zone: 'project_definition', control: 'number' },
  { id: 'power_mw', zone: 'project_definition', control: 'number' },
  { id: 'daily_cycles', zone: 'revenue_boundary', control: 'slider', g: 1, min: 1, max: 2, step: 0.1 },
  { id: 'epc_unit_price', zone: 'financial_boundary', control: 'slider', g: 1, min: 0.7, max: 0.85, step: 0.01 },
  { id: 'operation_years', zone: 'financial_boundary', control: 'select', g: 1, options: [{ value: 15, label: '15年' }, { value: 20, label: '20年' }] },
  { id: 'battery_replace_cost', zone: 'cost_boundary', control: 'fixed' },
  { id: 'maint_cost', zone: 'cost_boundary', control: 'slider', g: 1, min: 0, max: 0.1, step: 0.0001 },
  { id: 'spot_charge_avg', zone: 'revenue_boundary', control: 'dynamic_slider', g: 1, step: 0.0001 },
  { id: 'spot_discharge_avg', zone: 'revenue_boundary', control: 'dynamic_slider', g: 1, step: 0.0001 },
  { id: 'frequency_first_year_revenue', zone: 'revenue_boundary', control: 'dynamic_slider', step: 0.01 },
  { id: 'lease_unit_price', zone: 'revenue_boundary', control: 'dynamic_slider', step: 0.01 },
  { id: 'mid_long_energy_revenue_first_year_tax', zone: 'revenue_boundary', control: 'dynamic_slider', step: 0.01 },
  { id: 'project_irr', direction: 'output' }, // 无 zone/control，不进调整区
]

describe('paramAdjust: 现货同样受开关约束的统一显隐', () => {
  it('switch_spot=0 时隐藏现货参数', () => {
    const spec = PARAM_DICT.find((p) => p.id === 'spot_charge_avg')
    expect(isVisible(spec, { switch_spot: 0 })).toBe(false)
    expect(isVisible(spec, { switch_spot: 1 })).toBe(true)
  })

  it('调频/租赁/中长期按各自开关显隐', () => {
    expect(isVisible(PARAM_DICT.find((p) => p.id === 'frequency_first_year_revenue'), { switch_frequency: 0 })).toBe(false)
    expect(isVisible(PARAM_DICT.find((p) => p.id === 'lease_unit_price'), { switch_lease: 1 })).toBe(true)
    expect(isVisible(PARAM_DICT.find((p) => p.id === 'mid_long_energy_revenue_first_year_tax'), { switch_mid_long: 0 })).toBe(false)
  })

  it('非市场关联参数不受开关影响', () => {
    expect(isVisible(PARAM_DICT.find((p) => p.id === 'daily_cycles'), {})).toBe(true)
    expect(isVisible(PARAM_DICT.find((p) => p.id === 'epc_unit_price'), {})).toBe(true)
  })
})

describe('paramAdjust: 四区分组', () => {
  it('按 zone 分组并过滤掉开关关闭的市场参数与无 zone/control 的输出项', () => {
    const groups = groupByZone(PARAM_DICT, { switch_spot: 1, switch_frequency: 0, switch_lease: 0, switch_mid_long: 0 })
    const zoneIds = groups.map((g) => g.zone)
    expect(zoneIds).toEqual(['project_definition', 'financial_boundary', 'revenue_boundary', 'cost_boundary'])

    const revenue = groups.find((g) => g.zone === 'revenue_boundary').items.map((i) => i.id)
    expect(revenue).toContain('spot_charge_avg')
    expect(revenue).toContain('daily_cycles')
    expect(revenue).not.toContain('frequency_first_year_revenue')
    expect(revenue).not.toContain('lease_unit_price')
    expect(revenue).not.toContain('mid_long_energy_revenue_first_year_tax')

    const projectDefinition = groups.find((g) => g.zone === 'project_definition').items.map((i) => i.id)
    expect(projectDefinition).toEqual(['province', 'node_name', 'capacity_mwh', 'power_mw'])
  })

  it('某分区全部参数被显隐过滤后，该分区不出现', () => {
    const groups = groupByZone(
      PARAM_DICT.filter((p) => p.zone === 'revenue_boundary' && p.id !== 'daily_cycles'),
      { switch_spot: 0, switch_frequency: 0, switch_lease: 0, switch_mid_long: 0 },
    )
    expect(groups).toEqual([])
  })
})

describe('paramAdjust: 动态区间(基准值0~2倍)', () => {
  it('基准值为正数时返回 0~2倍区间', () => {
    expect(dynamicRange(0.2536, 0.0001)).toEqual({ min: 0, max: 0.5072, step: 0.0001 })
  })

  it('基准值为 0/null/undefined 时不可调（返回 null）', () => {
    expect(dynamicRange(0, 0.01)).toBeNull()
    expect(dynamicRange(null, 0.01)).toBeNull()
    expect(dynamicRange(undefined, 0.01)).toBeNull()
  })
})

describe('paramAdjust: variants 分档解析', () => {
  const battery = {
    id: 'battery_replace_cost', control: 'fixed', default: 0,
    variants: { '15': { control: 'fixed', default: 0 }, '20': { control: 'slider', default: 0.3, min: 0, max: 1, step: 0.01 } },
  }

  it('无 variants 时原样返回原 spec', () => {
    const spec = { id: 'maint_cost', control: 'slider', min: 0, max: 0.01 }
    expect(resolveVariant(spec, 20)).toBe(spec)
  })

  it('命中分档时浅合并覆盖 control/default/min/max/step', () => {
    const resolved = resolveVariant(battery, 20)
    expect(resolved.control).toBe('slider')
    expect(resolved.default).toBe(0.3)
    expect(resolved.min).toBe(0)
    expect(resolved.max).toBe(1)
    expect(resolved.step).toBe(0.01)
  })

  it('未命中或 key 缺失时回落基础定义', () => {
    expect(resolveVariant(battery, 15).control).toBe('fixed')
    expect(resolveVariant(battery, undefined).control).toBe('fixed')
    expect(resolveVariant(battery, null).control).toBe('fixed')
  })
})

describe('paramAdjust: 锁项规则（仅字典固定项锁定）', () => {
  it('省份 control=fixed 时始终锁定，不受版本影响', () => {
    const province = PARAM_DICT.find((p) => p.id === 'province')
    expect(isFieldLocked(province, { firstCalc: true })).toBe(true)
    expect(isFieldLocked(province, { firstCalc: false })).toBe(true)
  })

  it('运营期 select 可编辑，换电成本仍固定', () => {
    const years = PARAM_DICT.find((p) => p.id === 'operation_years')
    const battery = PARAM_DICT.find((p) => p.id === 'battery_replace_cost')
    expect(isFieldLocked(years, { firstCalc: true })).toBe(false)
    expect(isFieldLocked(years, { firstCalc: false })).toBe(false)
    expect(isFieldLocked(battery, { firstCalc: true })).toBe(true)
    expect(isFieldLocked(battery, { firstCalc: false })).toBe(true)
  })

  it('节点/容量/功率在首次及后续结果均可编辑', () => {
    const node = PARAM_DICT.find((p) => p.id === 'node_name')
    const capacity = PARAM_DICT.find((p) => p.id === 'capacity_mwh')
    const power = PARAM_DICT.find((p) => p.id === 'power_mw')
    for (const firstCalc of [true, false]) {
      expect(isFieldLocked(node, { firstCalc })).toBe(false)
      expect(isFieldLocked(capacity, { firstCalc })).toBe(false)
      expect(isFieldLocked(power, { firstCalc })).toBe(false)
    }
  })

  it('金融/收益/成本边界的可调参数不受版本限制', () => {
    const epc = PARAM_DICT.find((p) => p.id === 'epc_unit_price')
    expect(isFieldLocked(epc, { firstCalc: true })).toBe(false)
    expect(isFieldLocked(epc, { firstCalc: false })).toBe(false)
  })
})

describe('paramAdjust: 提交当前完整面板值', () => {
  it('收集 slider/dynamic_slider/select 控件当前值，忽略 fixed/text/number/无control项', () => {
    const values = {
      province: '甘肃', node_name: '祥泰站', capacity_mwh: 800, power_mw: 200,
      daily_cycles: 1.5, epc_unit_price: 0.8, operation_years: 20, battery_replace_cost: 0,
      maint_cost: 0.006, spot_charge_avg: 0.22, spot_discharge_avg: 0.61,
    }
    const overrides = buildOverrides(PARAM_DICT, values)
    expect(overrides).toEqual({
      daily_cycles: 1.5, epc_unit_price: 0.8, operation_years: 20, maint_cost: 0.006,
      spot_charge_avg: 0.22, spot_discharge_avg: 0.61,
    })
  })
})

describe('paramAdjust: 展示/输入精度（由 step 小数位数决定）', () => {
  it('decimalsForStep 按 step 的小数位数取值，整数或缺失 step 记为 0 位', () => {
    expect(decimalsForStep(0.0001)).toBe(4)
    expect(decimalsForStep(0.01)).toBe(2)
    expect(decimalsForStep(0.1)).toBe(1)
    expect(decimalsForStep(1)).toBe(0)
    expect(decimalsForStep(undefined)).toBe(0)
    expect(decimalsForStep(null)).toBe(0)
  })

  it('roundToStep 按精度四舍五入，修正现货充放电价格等字段的浮点误差', () => {
    expect(roundToStep(0.6099999999999999, 0.0001)).toBe(0.61)
    expect(roundToStep(0.22, 0.0001)).toBe(0.22)
    expect(roundToStep(0.8, 0.01)).toBe(0.8)
  })

  it('roundToStep 对非数字（如省份等只读字符串）原样返回', () => {
    expect(roundToStep('甘肃', 0.01)).toBe('甘肃')
    expect(roundToStep(null, 0.01)).toBeNull()
    expect(roundToStep(undefined, 0.01)).toBeUndefined()
  })
})

import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useCalculationStore } from '@/store/modules/calculation'
import {
  buildArchiveSummary,
  diffVersionInputs,
  getMetricDelta,
} from '@/utils/versionComparison'

const paramDict = [
  { id: 'capacity_mwh', cn: '装机容量', zone: 'project_definition', control: 'number', unit: 'MWh' },
  { id: 'operation_years', cn: '项目运营期', zone: 'financial_boundary', control: 'select', g: 1, unit: '年' },
  { id: 'strategy_achievement_rate', cn: '策略达成率', zone: 'revenue_boundary', control: 'slider', g: 1 },
  { id: 'spot_charge_avg', cn: '现货充电均价', zone: 'revenue_boundary', control: 'slider', g: 1 },
]

describe('version comparison model', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('groups final input changes and preserves explicit versus derived source', () => {
    const result = diffVersionInputs(
      { capacity_mwh: 200, operation_years: 20, strategy_achievement_rate: 0.85, spot_charge_avg: 0.3415 },
      { capacity_mwh: 400, operation_years: 15, strategy_achievement_rate: 0.9, spot_charge_avg: 0.3281 },
      { explicitOverrideKeys: ['operation_years', 'strategy_achievement_rate'], derivedChangedKeys: ['capacity_mwh', 'spot_charge_avg'] },
      paramDict,
    )

    expect(result.groups.map((group) => group.category)).toEqual(['basic', 'editable', 'advanced'])
    expect(result.totalCount).toBe(4)
    expect(result.groups.find((group) => group.category === 'basic').items[0]).toMatchObject({
      id: 'capacity_mwh', source: 'derived', oldValue: 400, newValue: 200,
    })
    expect(result.groups.find((group) => group.category === 'advanced').items).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: 'operation_years', source: 'explicit' }),
      expect.objectContaining({ id: 'strategy_achievement_rate', source: 'explicit' }),
    ]))
  })

  it('treats normalized numeric values as equal and keeps missing values visible', () => {
    const result = diffVersionInputs(
      { capacity_mwh: 200.0000, operation_years: null },
      { capacity_mwh: 200, operation_years: 15 },
      {},
      paramDict,
    )

    expect(result.totalCount).toBe(1)
    expect(result.groups[0].items[0]).toMatchObject({ id: 'operation_years', oldValue: 15, newValue: null })
  })

  it('does not report unchanged four-decimal spot prices when only EPC and frequency revenue change', () => {
    const dict = [
      { id: 'epc_unit_price', cn: 'EPC单价', zone: 'financial_boundary', control: 'slider', g: 1 },
      { id: 'frequency_first_year_revenue', cn: '首年调频收益', zone: 'revenue_boundary', control: 'dynamic_slider', g: 1 },
      { id: 'spot_charge_avg', cn: '现货充电均价', zone: 'revenue_boundary', control: 'dynamic_slider', g: 1 },
      { id: 'spot_discharge_avg', cn: '现货放电均价', zone: 'revenue_boundary', control: 'dynamic_slider', g: 1 },
    ]
    const result = diffVersionInputs(
      {
        epc_unit_price: 0.8,
        frequency_first_year_revenue: 1200,
        spot_charge_avg: 0.0703,
        spot_discharge_avg: 0.4833,
      },
      {
        epc_unit_price: 0.75,
        frequency_first_year_revenue: 1000,
        spot_charge_avg: 0.0703,
        spot_discharge_avg: 0.4833,
      },
      {
        explicitOverrideKeys: ['epc_unit_price', 'frequency_first_year_revenue'],
        derivedChangedKeys: [],
      },
      dict,
    )

    expect(result.totalCount).toBe(2)
    expect(result.groups.flatMap((group) => group.items).map((item) => item.id)).toEqual([
      'frequency_first_year_revenue',
      'epc_unit_price',
    ])
  })

  it('treats historical full-precision values as equal at the parameter step precision', () => {
    const dict = [
      { id: 'spot_charge_avg', cn: '现货充电均价', zone: 'revenue_boundary', control: 'dynamic_slider', g: 1, step: 0.0001 },
      { id: 'spot_discharge_avg', cn: '现货放电均价', zone: 'revenue_boundary', control: 'dynamic_slider', g: 1, step: 0.0001 },
    ]
    const result = diffVersionInputs(
      {
        spot_charge_avg: 0.0703,
        spot_discharge_avg: 0.4833,
      },
      {
        spot_charge_avg: 0.07032071762870515,
        spot_discharge_avg: 0.4832751404056162,
      },
      {
        derivedChangedKeys: ['spot_charge_avg', 'spot_discharge_avg'],
      },
      dict,
    )

    expect(result.totalCount).toBe(0)
    expect(result.groups).toEqual([])
  })

  it('keeps real changes visible at the parameter step precision', () => {
    const dict = [
      { id: 'spot_charge_avg', cn: '现货充电均价', zone: 'revenue_boundary', control: 'dynamic_slider', g: 1, step: 0.0001 },
    ]
    const result = diffVersionInputs(
      { spot_charge_avg: 0.0704 },
      { spot_charge_avg: 0.07032071762870515 },
      {},
      dict,
    )

    expect(result.totalCount).toBe(1)
  })

  it('uses economic meaning for KPI delta tone and line direction', () => {
    expect(getMetricDelta('projectIrr', 9, 8)).toMatchObject({ direction: 'up', tone: 'good' })
    expect(getMetricDelta('projectStaticPayback', 9, 8)).toMatchObject({ direction: 'up', tone: 'bad' })
    expect(getMetricDelta('projectStaticPayback', 8, 9)).toMatchObject({ direction: 'down', tone: 'good' })
    expect(getMetricDelta('averageProfit', 1000, 1000)).toMatchObject({ direction: 'flat', tone: 'neutral' })
  })

  it('builds a compact archive summary against the adjacent version', () => {
    const summary = buildArchiveSummary(
      {
        version: 'V3', input: { operation_years: 20, strategy_achievement_rate: 0.85, spot_charge_avg: 0.34 },
        result: { financial: { projectIrr: 8.42 } },
        changeMeta: { previousTaskId: 2, explicitOverrideKeys: ['operation_years', 'strategy_achievement_rate'], derivedChangedKeys: ['spot_charge_avg'] },
      },
      { version: 'V2', taskId: 2, input: { operation_years: 15, strategy_achievement_rate: 0.9, spot_charge_avg: 0.33 } },
      paramDict,
    )

    expect(summary).toMatchObject({ previousVersion: 'V2', projectIrr: 8.42 })
    expect(summary.explicit).toMatchObject({ count: 2 })
    expect(summary.derived).toMatchObject({ count: 1 })
    expect(summary.explicit.labels).toEqual(['项目运营期', '策略达成率'])
  })

  it('remembers comparison choices only for the current store session', () => {
    const store = useCalculationStore()
    store.versions = [{ version: 'V1' }, { version: 'V2' }, { version: 'V3' }]

    expect(store.comparisonVersionFor('V3')).toBe('V2')
    store.selectComparisonVersion('V3', 'V1')
    expect(store.comparisonVersionFor('V3')).toBe('V1')
    store.selectComparisonVersion('V2', 'V3')
    expect(store.comparisonVersionFor('V2')).toBe('V1')

    store.resetConversation()
    expect(store.comparisonVersionByVersion).toEqual({})
  })
})

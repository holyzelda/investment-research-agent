import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ResultCard from '@/views/home/components/ResultCard.vue'

vi.mock('@/views/home/composables/useEcharts', () => ({
  useEcharts: () => ({ el: { value: null }, resize: vi.fn() }),
  xcChartColors: () => ['#1', '#2', '#3', '#4'],
  xcVar: () => '#888',
}))

const snapshot = {
  basicInfo: {
    province: '甘肃', nodeName: null, powerMw: 200, capacityMwh: 800,
    chargeCost: 0.2, dischargeReturn: 0.61234, lossCost: 0.03,
  },
  financial: {
    projectIrr: 7.1, projectStaticPayback: 8.256, capitalIrr: 9.3,
    capitalStaticPayback: 6, averageProfit: 1200,
  },
  advanced: { donut: {}, debtServiceCoverage: {} },
  warnings: [],
}

describe('result card three modules', () => {
  it('renders basic information, five KPIs and both advanced charts', () => {
    const wrapper = mount(ResultCard, { props: { result: snapshot, version: 'V1' } })
    const text = wrapper.text()

    expect(text).toContain('项目基础边界条件')
    expect(text).toContain('甘肃')
    expect(text).not.toContain('节点')
    expect(text).toContain('核心投资收益指标')
    for (const label of ['项目全投资IRR', '全投资静态回收期', '资本金IRR', '资本金静态回收期', '年均利润']) {
      expect(text).toContain(label)
    }
    expect(text).toContain('首年收入结构')
    expect(text).toContain('偿债覆盖倍数')
    expect(text).toContain('0.2000元/kWh')
    expect(text).toContain('0.6123元/kWh')
    expect(text).toContain('0.0300元/kWh')
    expect(text).toContain('8.26')
    expect(text).toContain('6年')
    expect(text).not.toContain('6.00年')
    expect(wrapper.findAll('.ir-report-module')).toHaveLength(3)
    expect(wrapper.find('.ir-result--complete').exists()).toBe(true)
    expect(wrapper.find('.ir-fin__kpi--signature').text()).toContain('项目全投资IRR')
    expect(wrapper.findAll('.ir-fin__kpi')).toHaveLength(5)
    expect(snapshot.basicInfo.dischargeReturn).toBe(0.61234)
    expect(snapshot.financial.projectStaticPayback).toBe(8.256)
  })

  it('renders the project banner with province title, formatted time and version', () => {
    const wrapper = mount(ResultCard, {
      props: { result: snapshot, version: 'V1', calculatedAt: '2026-07-15T09:07:03' },
    })
    const banner = wrapper.find('.ir-result__banner')

    expect(banner.exists()).toBe(true)
    // 横幅插在头部之后、基础条件之前，且不计入三大模块
    expect(wrapper.findAll('.ir-report-module')).toHaveLength(3)
    expect(banner.find('.ir-result__banner-title').text()).toBe('甘肃省储能项目测算结果')
    const sub = banner.find('.ir-result__banner-sub').text()
    expect(sub).toContain('测算时间 2026年07月15日 09:07:03')
    expect(sub).toContain('测算版本 V1')
  })

  it('shows a placeholder time when calculatedAt is missing', () => {
    const wrapper = mount(ResultCard, { props: { result: snapshot, version: 'V1' } })
    expect(wrapper.find('.ir-result__banner-sub').text()).toContain('测算时间 —')
  })

  it('counts only advanced values that differ from the frozen input', async () => {
    const paramDict = [
      { id: 'operation_years', cn: '项目运营期', zone: 'financial_boundary', control: 'select', default: 15, g: 1, options: [{ value: 15, label: '15年' }, { value: 20, label: '20年' }] },
      { id: 'strategy_achievement_rate', cn: '现货策略达成率', zone: 'revenue_boundary', control: 'slider', min: 0.7, max: 0.95, step: 0.01, default: 0.9, g: 1 },
    ]
    const wrapper = mount(ResultCard, {
      props: { result: snapshot, version: 'V1', paramDict, seedInput: { operation_years: 15, strategy_achievement_rate: 0.9 } },
    })

    await wrapper.find('.ir-adjust__advanced').trigger('click')
    await wrapper.find('.ir-advanced__save').trigger('click')
    expect(wrapper.find('.ir-adjust__draft-count').exists()).toBe(false)

    await wrapper.find('.ir-adjust__advanced').trigger('click')
    await wrapper.find('select[data-param-id="operation_years"]').setValue('20')
    await wrapper.find('.ir-advanced__save').trigger('click')
    expect(wrapper.find('.ir-adjust__draft-count').text()).toBe('1')

    await wrapper.setProps({ version: 'V2', seedInput: { operation_years: 20, strategy_achievement_rate: 0.9 } })
    expect(wrapper.find('.ir-adjust__draft-count').exists()).toBe(false)
  })

  it('restores the saved advanced draft when reopening and discards unsaved edits', async () => {
    const paramDict = [
      { id: 'operation_years', cn: '项目运营期', zone: 'financial_boundary', control: 'select', default: 15, g: 1, options: [{ value: 15, label: '15年' }, { value: 20, label: '20年' }] },
      { id: 'strategy_achievement_rate', cn: '现货策略达成率', zone: 'revenue_boundary', control: 'slider', min: 0.7, max: 0.95, step: 0.01, default: 0.9, g: 1 },
    ]
    const wrapper = mount(ResultCard, {
      props: { result: snapshot, version: 'V1', paramDict, seedInput: { operation_years: 15, strategy_achievement_rate: 0.9 } },
    })

    await wrapper.find('.ir-adjust__advanced').trigger('click')
    await wrapper.find('select[data-param-id="operation_years"]').setValue('20')
    await wrapper.findAll('.ir-advanced__number')[0].setValue(0.85)
    await wrapper.find('.ir-advanced__save').trigger('click')

    await wrapper.find('.ir-adjust__advanced').trigger('click')
    expect(wrapper.find('select[data-param-id="operation_years"]').element.value).toBe('20')
    expect(wrapper.findAll('.ir-advanced__number')[0].element.value).toBe('0.85')

    await wrapper.findAll('.ir-advanced__number')[0].setValue(0.8)
    await wrapper.find('.ir-advanced__cancel').trigger('click')
    await wrapper.find('.ir-adjust__advanced').trigger('click')
    expect(wrapper.findAll('.ir-advanced__number')[0].element.value).toBe('0.85')
  })

  it('renders the adjustment panel when param dict is provided, hides it otherwise', async () => {
    const withDict = mount(ResultCard, {
      props: {
        result: snapshot, version: 'V1',
        paramDict: [{ id: 'epc_unit_price', cn: 'EPC单价', zone: 'financial_boundary', control: 'slider', min: 0.7, max: 0.85, step: 0.01 }],
        switches: {}, seedInput: {},
      },
    })
    expect(withDict.find('.ir-adjust__toggle').exists()).toBe(true)
    await withDict.find('.ir-adjust__toggle').trigger('click')
    expect(withDict.find('.ir-adjust__header .ir-adjust__advanced').exists()).toBe(true)

    const withoutDict = mount(ResultCard, { props: { result: snapshot, version: 'V1' } })
    expect(withoutDict.find('.ir-adjust__toggle').exists()).toBe(false)
  })

  it('generates a report only after the user clicks the clean result action', async () => {
    const wrapper = mount(ResultCard, { props: { result: snapshot, version: 'V1' } })
    const action = wrapper.find('.ir-result__act')

    expect(action.text()).toContain('生成报告')
    expect(action.attributes('disabled')).toBeUndefined()
    await action.trigger('click')
    expect(wrapper.emitted('generate-report')).toHaveLength(1)
  })

  it('requires recalculation before reporting when regular parameters have changed', async () => {
    const wrapper = mount(ResultCard, {
      props: {
        result: snapshot,
        version: 'V1',
        paramDict: [{ id: 'epc_unit_price', cn: 'EPC单价', zone: 'financial_boundary', control: 'slider', min: 0.7, max: 0.85, step: 0.01, default: 0.75 }],
        seedInput: { epc_unit_price: 0.8 },
      },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')
    await wrapper.find('.ps-val-input').setValue(0.82)

    const action = wrapper.find('.ir-result__act')
    expect(action.text()).toContain('请先重新测算')
    expect(action.attributes('disabled')).toBeDefined()
    expect(wrapper.find('.ir-result__report-hint').text()).toContain('参数修改尚未形成新版本')
    await action.trigger('click')
    expect(wrapper.emitted('generate-report')).toBeUndefined()
  })

  it('requires recalculation before reporting when advanced changes are staged', async () => {
    const paramDict = [
      { id: 'operation_years', cn: '项目运营期', zone: 'financial_boundary', control: 'select', default: 15, g: 1, options: [{ value: 15, label: '15年' }, { value: 20, label: '20年' }] },
    ]
    const wrapper = mount(ResultCard, {
      props: { result: snapshot, version: 'V1', paramDict, seedInput: { operation_years: 15 } },
    })
    await wrapper.find('.ir-adjust__advanced').trigger('click')
    await wrapper.find('select[data-param-id="operation_years"]').setValue('20')
    await wrapper.find('.ir-advanced__save').trigger('click')

    expect(wrapper.find('.ir-result__act').text()).toContain('请先重新测算')
    expect(wrapper.find('.ir-result__act').attributes('disabled')).toBeDefined()
  })

  it('allows recalculation from the collapsed advanced draft action bar', async () => {
    const paramDict = [
      { id: 'operation_years', cn: '项目运营期', zone: 'financial_boundary', control: 'select', default: 15, g: 1, options: [{ value: 15, label: '15年' }, { value: 20, label: '20年' }] },
    ]
    const wrapper = mount(ResultCard, {
      props: { result: snapshot, version: 'V1', paramDict, seedInput: { operation_years: 15 } },
    })
    await wrapper.find('.ir-adjust__advanced').trigger('click')
    await wrapper.find('select[data-param-id="operation_years"]').setValue('20')
    await wrapper.find('.ir-advanced__save').trigger('click')

    expect(wrapper.find('.ir-adjust__body').exists()).toBe(false)
    await wrapper.find('.ir-adjust__pending-bar .ir-adjust__submit').trigger('click')

    expect(wrapper.emitted('recalculate')).toHaveLength(1)
    expect(wrapper.emitted('recalculate')[0][0].overrides.operation_years).toBe(20)
  })

  it('discards regular and advanced drafts together', async () => {
    const paramDict = [
      { id: 'power_mw', cn: '储能装机功率', zone: 'project_definition', control: 'number', default: null, unit: 'MW' },
      { id: 'epc_unit_price', cn: 'EPC单价', zone: 'financial_boundary', control: 'slider', min: 0.7, max: 0.85, step: 0.01, default: 0.75 },
      { id: 'operation_years', cn: '项目运营期', zone: 'financial_boundary', control: 'select', default: 15, g: 1, options: [{ value: 15, label: '15年' }, { value: 20, label: '20年' }] },
    ]
    const wrapper = mount(ResultCard, {
      props: {
        result: snapshot, version: 'V1', paramDict,
        seedInput: { power_mw: 200, epc_unit_price: 0.8, operation_years: 15 },
      },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')
    await wrapper.find('.ps-val-input').setValue(0.82)
    await wrapper.find('.ir-adjust__advanced').trigger('click')
    await wrapper.find('select[data-param-id="operation_years"]').setValue('20')
    await wrapper.find('.ir-advanced__save').trigger('click')
    await wrapper.find('.ir-adjust__toggle').trigger('click')

    expect(wrapper.find('.ir-adjust__pending-bar').exists()).toBe(true)
    expect(wrapper.find('.ir-result__act').attributes('disabled')).toBeDefined()
    await wrapper.find('.ir-adjust__pending-bar .ir-adjust__reset').trigger('click')

    expect(wrapper.find('.ir-adjust__pending-bar').exists()).toBe(false)
    expect(wrapper.find('.ir-adjust__draft-count').exists()).toBe(false)
    expect(wrapper.find('.ir-result__report-hint').text()).not.toContain('参数修改尚未形成新版本')
    expect(wrapper.find('.ir-result__act').attributes('disabled')).toBeUndefined()
    expect(wrapper.emitted('recalculate')).toBeUndefined()

    await wrapper.find('.ir-adjust__toggle').trigger('click')
    expect(wrapper.find('.ps-val-input').element.value).toBe('0.8')
    await wrapper.find('.ir-adjust__advanced').trigger('click')
    expect(wrapper.find('select[data-param-id="operation_years"]').element.value).toBe('15')
  })

  it('keeps generation non-repeatable, exposes retry, and removes the completed duplicate action', async () => {
    const generating = mount(ResultCard, {
      props: { result: snapshot, version: 'V1', report: { status: 'generating' } },
    })
    expect(generating.find('.ir-result__act').text()).toContain('报告生成中')
    expect(generating.find('.ir-result__act').attributes('disabled')).toBeDefined()

    const failed = mount(ResultCard, {
      props: { result: snapshot, version: 'V1', report: { status: 'failed' } },
    })
    expect(failed.find('.ir-result__act').text()).toContain('重新生成报告')
    await failed.find('.ir-result__act').trigger('click')
    expect(failed.emitted('generate-report')).toHaveLength(1)

    const completed = mount(ResultCard, {
      props: { result: snapshot, version: 'V1', report: { status: 'completed', reportId: 'r-1' } },
    })
    expect(completed.find('.ir-result__footer').exists()).toBe(false)
    expect(completed.text()).not.toContain('已生成报告')
    expect(completed.emitted('view-report')).toBeUndefined()
  })
})

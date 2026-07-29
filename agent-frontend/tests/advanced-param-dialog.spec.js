import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AdvancedParamDialog from '@/views/home/components/AdvancedParamDialog.vue'

const PARAM_DICT = [
  { id: 'operation_years', cn: '项目运营期', zone: 'financial_boundary', control: 'select', default: 15, unit: '年', g: 1, options: [{ value: 15, label: '15年' }, { value: 20, label: '20年' }] },
  { id: 'mid_long_charge_avg', cn: '中长期充电均价', default: null, unit: '元/kWh', g: 0 },
  { id: 'mid_long_discharge_avg', cn: '中长期放电均价', default: null, unit: '元/kWh', g: 0 },
  { id: 'strategy_achievement_rate', cn: '现货策略达成率', zone: 'revenue_boundary', control: 'slider', min: 0.7, max: 0.95, step: 0.01, default: 0.9, g: 1 },
  { id: 'capacity_achievement_rate', cn: '容量市场达成率', zone: 'revenue_boundary', control: 'slider', min: 0.7, max: 0.95, step: 0.01, default: 0.9, g: 1 },
  { id: 'battery_replace_cost', cn: '换电成本', zone: 'cost_boundary', control: 'fixed', default: 0, unit: '元/Wh', g: 1 },
  { id: 'maint_cost', cn: '维保成本', zone: 'cost_boundary', control: 'slider', min: 0, max: 0.01, step: 0.0001, default: 0.005, unit: '元/Wh', g: 1 },
  { id: 'opex_cost', cn: '运营成本', zone: 'cost_boundary', control: 'slider', min: 0, max: 0.01, step: 0.0001, default: 0.005, unit: '元/Wh', g: 1 },
]

const SEED = { operation_years: 15, mid_long_charge_avg: null, mid_long_discharge_avg: null, strategy_achievement_rate: 0.9, capacity_achievement_rate: 0.9, battery_replace_cost: 0, maint_cost: 0.005, opex_cost: 0.005 }

describe('AdvancedParamDialog', () => {
  it('renders the approved sections and all parameter fields in the required order', () => {
    const wrapper = mount(AdvancedParamDialog, { props: { modelValue: true, paramDict: PARAM_DICT, seedInput: SEED } })
    const sections = wrapper.findAll('.ir-advanced__section')

    expect(sections.map((section) => section.find('h4').text())).toEqual(['金融边界', '收益边界', '成本边界'])
    expect(sections.every((section) => section.find('.ir-advanced__section-icon').exists())).toBe(true)
    expect(wrapper.findAll('.ir-advanced__field-icon')).toHaveLength(PARAM_DICT.length)
    expect(sections.every((section) => !section.classes().includes('ir-advanced__section-card'))).toBe(true)
    expect(sections.map((section) => section.findAll('.ir-advanced__field').map((field) => field.text()))).toEqual([
      [expect.stringContaining('项目运营期')],
      [expect.stringContaining('中长期充电均价'), expect.stringContaining('中长期放电均价'), expect.stringContaining('现货策略达成率'), expect.stringContaining('容量市场达成率')],
      [expect.stringContaining('换电成本'), expect.stringContaining('维保成本'), expect.stringContaining('运营成本')],
    ])
  })

  it('places the requested revenue and cost controls in dedicated rows', () => {
    const wrapper = mount(AdvancedParamDialog, { props: { modelValue: true, paramDict: PARAM_DICT, seedInput: SEED } })

    expect(wrapper.find('.ir-advanced__fields--revenue').exists()).toBe(true)
    expect(wrapper.find('.ir-advanced__fields--cost').exists()).toBe(true)
  })

  it('uses a dash for unavailable middle-long prices and metadata-defined read-only fields', () => {
    const wrapper = mount(AdvancedParamDialog, { props: { modelValue: true, paramDict: PARAM_DICT, seedInput: SEED } })
    const text = wrapper.text()

    expect(text).toContain('中长期充电均价—')
    expect(text).toContain('中长期放电均价—')
    expect(text).toContain('项目运营期')
    expect(text).toContain('换电成本0元/Wh')
  })

  it('uses aligned inline value editors for editable sliders and closes on Escape', async () => {
    const wrapper = mount(AdvancedParamDialog, { props: { modelValue: true, paramDict: PARAM_DICT, seedInput: SEED }, attachTo: document.body })

    expect(wrapper.findAll('.ir-advanced__field--slider .ir-advanced__value').length).toBeGreaterThan(0)
    await wrapper.find('.ir-advanced').trigger('keydown', { key: 'Escape' })
    expect(wrapper.emitted('update:modelValue')).toContainEqual([false])
    wrapper.unmount()
  })

  it('prefills editable values from the saved draft before frozen input defaults', () => {
    const wrapper = mount(AdvancedParamDialog, {
      props: {
        modelValue: true,
        paramDict: PARAM_DICT,
        seedInput: SEED,
        draftInput: { operation_years: 20, strategy_achievement_rate: 0.85 },
      },
    })

    expect(wrapper.find('select[data-param-id="operation_years"]').element.value).toBe('20')
    expect(wrapper.findAll('.ir-advanced__number').some((input) => input.element.value === '0.85')).toBe(true)
  })

  it('restores editable fields to frozen input without saving until confirmed', async () => {
    const wrapper = mount(AdvancedParamDialog, {
      props: {
        modelValue: true,
        paramDict: PARAM_DICT,
        seedInput: SEED,
        draftInput: { operation_years: 20, strategy_achievement_rate: 0.85 },
      },
    })
    const reset = wrapper.find('.ir-advanced__reset')
    expect(reset.attributes('disabled')).toBeUndefined()

    await reset.trigger('click')
    expect(wrapper.find('select[data-param-id="operation_years"]').element.value).toBe('15')
    expect(wrapper.findAll('.ir-advanced__number').some((input) => input.element.value === '0.9')).toBe(true)
    expect(reset.attributes('disabled')).toBeDefined()
    expect(wrapper.emitted('save')).toBeUndefined()

    await wrapper.find('.ir-advanced__save').trigger('click')
    expect(wrapper.emitted('save')[0][0]).toMatchObject({ operation_years: 15, strategy_achievement_rate: 0.9 })
  })

  it('renders operation years as the metadata-defined select and saves 20', async () => {
    const wrapper = mount(AdvancedParamDialog, { props: { modelValue: true, paramDict: PARAM_DICT, seedInput: SEED } })
    const select = wrapper.find('select[data-param-id="operation_years"]')
    expect(select.findAll('option').map((option) => option.text())).toEqual(['15年', '20年'])
    await select.setValue('20')
    await wrapper.find('.ir-advanced__save').trigger('click')
    expect(wrapper.emitted('save')[0][0]).toMatchObject({ operation_years: 20 })
  })

  it('saves only backend-authorized slider values into a draft without submitting a calculation', async () => {
    const wrapper = mount(AdvancedParamDialog, { props: { modelValue: true, paramDict: PARAM_DICT, seedInput: SEED } })
    const rate = wrapper.findAll('.ir-advanced__number').find((input) => input.element.value === '0.9')
    await rate.setValue(0.85)
    await wrapper.find('.ir-advanced__save').trigger('click')

    expect(wrapper.emitted('save')).toEqual([[{
      operation_years: 15,
      strategy_achievement_rate: 0.85,
      capacity_achievement_rate: 0.9,
      maint_cost: 0.005,
      opex_cost: 0.005,
    }]])
    expect(wrapper.emitted('recalculate')).toBeUndefined()
  })
})

import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AdvancedParamDialog from '@/views/home/components/AdvancedParamDialog.vue'

const PARAM_DICT = [
  { id: 'operation_years', cn: '项目运营期', zone: 'financial_boundary', control: 'select', default: 15, unit: '年', g: 1, options: [{ value: 15, label: '15年' }, { value: 20, label: '20年' }] },
  { id: 'income_tax_rate_input', cn: '所得税', zone: 'financial_boundary', control: 'slider', min: 0, max: 0.35, step: 0.01, default: null, unit: '—', g: 1 },
  { id: 'strategy_achievement_rate', cn: '现货策略达成率', zone: 'revenue_boundary', control: 'slider', min: 0.7, max: 0.95, step: 0.01, default: 0.9, g: 1 },
  { id: 'capacity_achievement_rate', cn: '容量市场达成率', zone: 'revenue_boundary', control: 'slider', min: 0.7, max: 0.95, step: 0.01, default: 0.9, g: 1 },
  { id: 'battery_replace_cost', cn: '换电成本', zone: 'cost_boundary', control: 'fixed', default: 0, unit: '元/Wh', g: 1, variants: { '15': { control: 'fixed', default: 0 }, '20': { control: 'slider', default: 0.3, min: 0, max: 1, step: 0.01 } } },
  { id: 'maint_cost', cn: '维保成本', zone: 'cost_boundary', control: 'slider', min: 0, max: 0.01, step: 0.0001, default: 0.005, unit: '元/Wh', g: 1 },
  { id: 'opex_cost', cn: '运营成本', zone: 'cost_boundary', control: 'slider', min: 0, max: 0.01, step: 0.0001, default: 0.005, unit: '元/Wh', g: 1 },
]

const SEED = { operation_years: 15, income_tax_rate_input: 0.15, strategy_achievement_rate: 0.9, capacity_achievement_rate: 0.9, battery_replace_cost: 0, maint_cost: 0.005, opex_cost: 0.005 }
const SWITCHES = { switch_spot: 1, switch_capacity: 1 }

describe('AdvancedParamDialog', () => {
  it('shows chat-driven changes against the previous calculation version', () => {
    const wrapper = mount(AdvancedParamDialog, {
      props: {
        modelValue: true,
        paramDict: PARAM_DICT,
        seedInput: { ...SEED, strategy_achievement_rate: 0.85, maint_cost: 0.007 },
        comparisonInput: SEED,
        switches: SWITCHES,
      },
    })

    const fields = wrapper.findAll('.ir-advanced__field')
    const strategy = fields.find((field) => field.text().includes('现货策略达成率'))
    const maintenance = fields.find((field) => field.text().includes('维保成本'))

    expect(strategy?.find('.ir-advanced__delta').text()).toBe('-0.05')
    expect(maintenance?.find('.ir-advanced__delta').text()).toBe('+0.0020元/Wh')
  })

  it('首个版本以当前冻结值为基准，不因地区值不同于默认值显示胶囊', async () => {
    const wrapper = mount(AdvancedParamDialog, {
      props: {
        modelValue: true,
        paramDict: PARAM_DICT,
        seedInput: { ...SEED, strategy_achievement_rate: 0.85, maint_cost: 0.007 },
        switches: SWITCHES,
      },
    })

    expect(wrapper.findAll('.ir-advanced__delta')).toHaveLength(0)

    const fields = wrapper.findAll('.ir-advanced__field')
    const strategy = fields.find((field) => field.text().includes('现货策略达成率'))
    await strategy.find('.ir-advanced__number').setValue(0.86)

    expect(strategy.find('.ir-advanced__delta').text()).toBe('+0.01')
  })

  it('renders approved sections and gates capacity achievement by its market switch', () => {
    const wrapper = mount(AdvancedParamDialog, { props: { modelValue: true, paramDict: PARAM_DICT, seedInput: SEED, switches: SWITCHES } })
    const sections = wrapper.findAll('.ir-advanced__section')

    expect(sections.map((section) => section.find('h4').text())).toEqual(['金融边界', '收益边界', '成本边界'])
    expect(sections.every((section) => section.find('.ir-advanced__section-icon').exists())).toBe(true)
    expect(wrapper.findAll('.ir-advanced__field-icon')).toHaveLength(PARAM_DICT.length)
    expect(sections.every((section) => !section.classes().includes('ir-advanced__section-card'))).toBe(true)
    expect(sections.map((section) => section.findAll('.ir-advanced__field').map((field) => field.text()))).toEqual([
      [expect.stringContaining('项目运营期'), expect.stringContaining('所得税')],
      [expect.stringContaining('现货策略达成率'), expect.stringContaining('容量市场达成率')],
      [expect.stringContaining('换电成本'), expect.stringContaining('维保成本'), expect.stringContaining('运营成本')],
    ])
    const text = wrapper.text()
    expect(text).not.toContain('中长期充电均价')
    expect(text).not.toContain('中长期放电均价')
    expect(wrapper.find('.ir-advanced__fields--revenue').exists()).toBe(true)
    expect(wrapper.find('.ir-advanced__fields--cost').exists()).toBe(true)

    const disabled = mount(AdvancedParamDialog, {
      props: {
        modelValue: true,
        paramDict: PARAM_DICT,
        seedInput: SEED,
        switches: { ...SWITCHES, switch_capacity: 0 },
      },
    })
    expect(disabled.text()).not.toContain('容量市场达成率')
  })

  it('submits income tax through the dedicated API input id', async () => {
    const wrapper = mount(AdvancedParamDialog, {
      props: { modelValue: true, paramDict: PARAM_DICT, seedInput: SEED, switches: SWITCHES },
    })
    const field = wrapper.findAll('.ir-advanced__field').find((node) => node.text().includes('所得税'))

    await field.find('.ir-advanced__number').setValue(0.2)
    await wrapper.find('.ir-advanced__save').trigger('click')

    expect(wrapper.emitted('save')[0][0]).toEqual({ income_tax_rate_input: 0.2 })
  })

  it('uses aligned inline value editors for editable sliders and closes on Escape', async () => {
    const wrapper = mount(AdvancedParamDialog, { props: { modelValue: true, paramDict: PARAM_DICT, seedInput: SEED, switches: SWITCHES }, attachTo: document.body })

    expect(wrapper.findAll('.ir-advanced__field--slider .ir-advanced__value').length).toBeGreaterThan(0)
    await wrapper.find('.ir-advanced').trigger('keydown', { key: 'Escape' })
    expect(wrapper.emitted('update:modelValue')).toContainEqual([false])
    wrapper.unmount()
  })

  it('uses aligned full-width rails with frozen-value markers for editable sliders', () => {
    const wrapper = mount(AdvancedParamDialog, { props: { modelValue: true, paramDict: PARAM_DICT, seedInput: SEED, switches: SWITCHES } })
    const railFields = wrapper.findAll('.ir-advanced__field--slider')

    expect(railFields.length).toBeGreaterThan(0)
    expect(railFields.every((field) => field.find('.ir-advanced__field-label').exists())).toBe(true)
    expect(railFields.every((field) => field.find('.ir-advanced__value').exists())).toBe(true)
    expect(railFields.every((field) => field.find('.ir-advanced__slider-wrap').exists())).toBe(true)
    expect(railFields.every((field) => field.find('.ir-advanced__mark').exists())).toBe(true)
    expect(railFields.every((field) => field.find('.ir-advanced__mark').attributes('aria-hidden') === 'true')).toBe(true)
  })

  it('prefills editable values from the saved draft before frozen input defaults', () => {
    const wrapper = mount(AdvancedParamDialog, {
      props: {
        modelValue: true,
        paramDict: PARAM_DICT,
        seedInput: SEED,
        draftInput: { operation_years: 20, strategy_achievement_rate: 0.85 },
        switches: SWITCHES,
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
        switches: SWITCHES,
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
    expect(wrapper.emitted('save')[0][0]).toEqual({})
  })

  it('renders operation years as the metadata-defined select and saves 20', async () => {
    const wrapper = mount(AdvancedParamDialog, { props: { modelValue: true, paramDict: PARAM_DICT, seedInput: SEED, switches: SWITCHES } })
    const select = wrapper.find('select[data-param-id="operation_years"]')
    expect(select.findAll('option').map((option) => option.text())).toEqual(['15年', '20年'])
    await select.setValue('20')
    await wrapper.find('.ir-advanced__save').trigger('click')
    expect(wrapper.emitted('save')[0][0]).toMatchObject({ operation_years: 20 })
  })

  it('saves only backend-authorized slider values into a draft without submitting a calculation', async () => {
    const wrapper = mount(AdvancedParamDialog, { props: { modelValue: true, paramDict: PARAM_DICT, seedInput: SEED, switches: SWITCHES } })
    const rate = wrapper.findAll('.ir-advanced__number').find((input) => input.element.value === '0.9')
    await rate.setValue(0.85)
    await wrapper.find('.ir-advanced__save').trigger('click')

    expect(wrapper.emitted('save')).toEqual([[{
      strategy_achievement_rate: 0.85,
    }]])
    expect(wrapper.emitted('recalculate')).toBeUndefined()
  })

  it('switches battery replace cost to an editable 0.3 slider on 20-year', async () => {
    const wrapper = mount(AdvancedParamDialog, { props: { modelValue: true, paramDict: PARAM_DICT, seedInput: SEED, switches: SWITCHES } })
    await wrapper.find('select[data-param-id="operation_years"]').setValue('20')

    const batteryField = wrapper.findAll('.ir-advanced__field').find((field) => field.text().includes('换电成本'))
    const number = batteryField?.find('.ir-advanced__number')
    expect(number?.exists()).toBe(true)
    expect(number?.element.value).toBe('0.3')
    const slider = batteryField?.find('.ir-advanced__slider')
    expect(slider?.attributes('min')).toBe('0')
    expect(slider?.attributes('max')).toBe('1')
    expect(slider?.attributes('step')).toBe('0.01')
    expect(batteryField?.find('.ir-advanced__mark').text()).toContain('0 元/Wh')
  })

  it('resets battery replace cost to read-only 0 when switching back to 15-year', async () => {
    const wrapper = mount(AdvancedParamDialog, { props: { modelValue: true, paramDict: PARAM_DICT, seedInput: SEED, switches: SWITCHES } })
    const select = wrapper.find('select[data-param-id="operation_years"]')
    await select.setValue('20')
    await select.setValue('15')

    const batteryField = wrapper.findAll('.ir-advanced__field').find((field) => field.text().includes('换电成本'))
    expect(batteryField?.find('.ir-advanced__number').exists()).toBe(false)
    expect(batteryField?.text()).toContain('换电成本0元/Wh')
  })

  it('does not collect the target-period battery default when saving in 20-year mode', async () => {
    const wrapper = mount(AdvancedParamDialog, { props: { modelValue: true, paramDict: PARAM_DICT, seedInput: SEED, switches: SWITCHES } })
    await wrapper.find('select[data-param-id="operation_years"]').setValue('20')
    await wrapper.find('.ir-advanced__save').trigger('click')

    expect(wrapper.emitted('save')[0][0]).toEqual({ operation_years: 20 })
  })

  it('collects only a battery value that differs from the target-period default', async () => {
    const wrapper = mount(AdvancedParamDialog, { props: { modelValue: true, paramDict: PARAM_DICT, seedInput: SEED, switches: SWITCHES } })
    await wrapper.find('select[data-param-id="operation_years"]').setValue('20')
    const batteryField = wrapper.findAll('.ir-advanced__field').find((field) => field.text().includes('换电成本'))
    const number = batteryField.find('.ir-advanced__number')

    await number.setValue(0.6)
    await wrapper.find('.ir-advanced__save').trigger('click')
    expect(wrapper.emitted('save').at(-1)[0]).toEqual({ operation_years: 20, battery_replace_cost: 0.6 })

    await number.setValue(0.3)
    await wrapper.find('.ir-advanced__save').trigger('click')
    expect(wrapper.emitted('save').at(-1)[0]).toEqual({ operation_years: 20 })
  })

  it('does not restore a prior 20-year battery draft after switching away and back', async () => {
    const wrapper = mount(AdvancedParamDialog, { props: { modelValue: true, paramDict: PARAM_DICT, seedInput: SEED, switches: SWITCHES } })
    const select = wrapper.find('select[data-param-id="operation_years"]')
    await select.setValue('20')
    let batteryField = wrapper.findAll('.ir-advanced__field').find((field) => field.text().includes('换电成本'))
    await batteryField.find('.ir-advanced__number').setValue(0.6)

    await select.setValue('15')
    await select.setValue('20')
    batteryField = wrapper.findAll('.ir-advanced__field').find((field) => field.text().includes('换电成本'))
    expect(batteryField.find('.ir-advanced__number').element.value).toBe('0.3')
    await wrapper.find('.ir-advanced__save').trigger('click')
    expect(wrapper.emitted('save').at(-1)[0]).toEqual({ operation_years: 20 })
  })

  it('edits inline without a modal and disables advanced controls while recalculating', async () => {
    const wrapper = mount(AdvancedParamDialog, {
      props: { embedded: true, paramDict: PARAM_DICT, seedInput: SEED, switches: SWITCHES },
    })

    expect(wrapper.find('.ir-advanced__mask').exists()).toBe(false)
    expect(wrapper.find('.ir-advanced-embedded').exists()).toBe(true)
    expect(wrapper.find('.ir-advanced__save').exists()).toBe(false)
    expect(wrapper.find('.ir-advanced__embedded-toolbar').text()).toContain('高级参数暂无修改')
    expect(wrapper.find('.ir-advanced__reset').attributes('disabled')).toBeDefined()

    await wrapper.find('select[data-param-id="operation_years"]').setValue('20')
    expect(wrapper.emitted('save')?.at(-1)?.[0]).toEqual({ operation_years: 20 })
    expect(wrapper.find('.ir-advanced__embedded-toolbar').text()).toContain('已修改 1 项高级参数')
    expect(wrapper.find('.ir-advanced__reset').text()).toBe('撤销高级参数修改')
    expect(wrapper.find('.ir-advanced__reset').attributes('disabled')).toBeUndefined()

    await wrapper.setProps({ disabled: true })
    expect(wrapper.find('.ir-advanced__select').attributes('disabled')).toBeDefined()
    expect(wrapper.find('.ir-advanced__number').attributes('disabled')).toBeDefined()
    expect(wrapper.find('.ir-advanced__slider').attributes('disabled')).toBeDefined()
    expect(wrapper.find('.ir-advanced__reset').attributes('disabled')).toBeDefined()
  })

  it('keeps invalid text visible, reports the range error, and blocks draft saving', async () => {
    const wrapper = mount(AdvancedParamDialog, {
      props: { modelValue: true, paramDict: PARAM_DICT, seedInput: SEED, switches: SWITCHES },
    })
    const input = wrapper.findAll('.ir-advanced__number').find((node) => node.element.value === '0.9')
    const field = input.element.closest('.ir-advanced__field')

    await input.setValue(1)

    expect(input.element.value).toBe('1')
    expect(input.attributes('aria-invalid')).toBe('true')
    expect(field.textContent).toContain('不能高于 0.95')
    expect(field.querySelector('.ir-advanced__slider').value).toBe('0.9')
    expect(wrapper.find('.ir-advanced__save').attributes('disabled')).toBeDefined()
    expect(wrapper.emitted('validation-change')?.at(-1)).toEqual([true])
    await wrapper.find('.ir-advanced__save').trigger('click')
    expect(wrapper.emitted('save')).toBeUndefined()
  })

  it('clears validation by correcting text or moving the slider', async () => {
    const wrapper = mount(AdvancedParamDialog, {
      props: { embedded: true, paramDict: PARAM_DICT, seedInput: SEED, switches: SWITCHES },
    })
    const input = wrapper.findAll('.ir-advanced__number').find((node) => node.element.value === '0.9')
    const field = input.element.closest('.ir-advanced__field')

    await input.setValue('')
    expect(field.textContent).toContain('请输入有效数值')
    expect(wrapper.emitted('save')).toBeUndefined()

    const slider = wrapper.findAll('.ir-advanced__slider').find((node) => node.element === field.querySelector('.ir-advanced__slider'))
    await slider.setValue(0.85)
    expect(field.querySelector('.ir-advanced__validation')).toBeNull()
    expect(input.element.value).toBe('0.85')
    expect(wrapper.emitted('save')?.at(-1)?.[0]).toEqual({ strategy_achievement_rate: 0.85 })
    expect(wrapper.emitted('validation-change')?.at(-1)).toEqual([false])
  })

  it('shows data pending when an editable dynamic range has no frozen baseline', () => {
    const dynamicDict = [...PARAM_DICT, {
      id: 'strategy_achievement_rate', cn: '现货策略达成率', zone: 'revenue_boundary',
      control: 'dynamic_slider', step: 0.01, default: null, g: 1,
    }]
    const wrapper = mount(AdvancedParamDialog, {
      props: { modelValue: true, paramDict: dynamicDict, seedInput: { ...SEED, strategy_achievement_rate: null }, switches: SWITCHES },
    })
    const field = wrapper.findAll('.ir-advanced__field').find((node) => node.text().includes('现货策略达成率'))

    expect(field.text()).toContain('数据待完善')
    expect(field.find('.ir-advanced__number').exists()).toBe(false)
    expect(field.find('.ir-advanced__slider').exists()).toBe(false)
  })

  it('shows the same precise-input hint when hovering or focusing an advanced slider', async () => {
    const wrapper = mount(AdvancedParamDialog, {
      props: { embedded: true, paramDict: PARAM_DICT, seedInput: SEED, switches: SWITCHES },
    })
    const slider = wrapper.find('.ir-advanced__slider')

    await slider.trigger('pointerenter')
    expect(wrapper.find('.ir-advanced__input-hint').text()).toBe('点击数值可精确输入')
    await slider.trigger('pointerleave')
    expect(wrapper.find('.ir-advanced__input-hint').exists()).toBe(false)

    await slider.trigger('focus')
    expect(wrapper.find('.ir-advanced__input-hint').exists()).toBe(true)
    await slider.trigger('pointerdown')
    expect(wrapper.find('.ir-advanced__input-hint').exists()).toBe(false)
  })
})

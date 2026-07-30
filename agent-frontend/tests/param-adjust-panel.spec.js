import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ParamAdjustPanel from '@/views/home/components/ParamAdjustPanel.vue'

const PARAM_DICT = [
  { id: 'province', cn: '所在省份', zone: 'project_definition', control: 'fixed', default: null },
  { id: 'node_name', cn: '节点名称', zone: 'project_definition', control: 'text', default: null },
  { id: 'capacity_mwh', cn: '装机容量', zone: 'project_definition', control: 'number', default: null, unit: 'MWh' },
  { id: 'power_mw', cn: '储能装机功率', zone: 'project_definition', control: 'number', default: null, unit: 'MW' },
  { id: 'battery_replace_cost', cn: '换电成本', zone: 'cost_boundary', control: 'fixed', default: 0, unit: '元/Wh' },
  { id: 'epc_unit_price', cn: 'EPC单价', zone: 'financial_boundary', control: 'slider', min: 0.7, max: 0.85, step: 0.01, default: 0.75 },
  { id: 'spot_charge_avg', cn: '现货充电均价', zone: 'revenue_boundary', control: 'dynamic_slider', step: 0.0001 },
  { id: 'spot_discharge_avg', cn: '现货放电均价', zone: 'revenue_boundary', control: 'dynamic_slider', step: 0.0001 },
]

const SEED = {
  province: '甘肃', node_name: '祥泰站', capacity_mwh: 800, power_mw: 200,
  epc_unit_price: 0.8, spot_charge_avg: 0.22, spot_discharge_avg: 0.61,
}

describe('ParamAdjustPanel', () => {
  it('default collapsed; expanding renders zones', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: { paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2' },
    })
    expect(wrapper.find('.ir-adjust__body').exists()).toBe(false)

    await wrapper.find('.ir-adjust__toggle').trigger('click')

    expect(wrapper.find('.ir-adjust__body').exists()).toBe(true)
    expect(wrapper.text()).toContain('项目信息')
    expect(wrapper.text()).toContain('金融边界')
    expect(wrapper.text()).toContain('收益边界')
    expect(wrapper.findAll('.ir-adjust__zone')).toHaveLength(3)
    expect(wrapper.findAll('.ir-adjust__project-item')).toHaveLength(3)
    expect(wrapper.find('.ir-adjust__zone-card').exists()).toBe(false)
  })

  it('V1 中省份只读，节点/容量/功率为可编辑控件', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: {
        paramDict: PARAM_DICT,
        switches: { switch_spot: 1 },
        seedInput: SEED,
        stationOptions: ['祥泰站', '新节点'],
        version: 'V1',
      },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')

    const roTexts = wrapper.findAll('.ir-adjust__ro').map((n) => n.text())
    expect(roTexts.some((t) => t.includes('甘肃'))).toBe(true)
    expect(wrapper.find('.ir-adjust__select').exists()).toBe(true)

    const projectFields = wrapper.findAll('.ir-adjust__project-item')
    const capacityField = projectFields.find((field) => field.text().includes('装机容量'))
    const powerField = projectFields.find((field) => field.text().includes('储能装机功率'))
    expect(capacityField?.find('input.ir-adjust__number').exists()).toBe(true)
    expect(powerField?.find('input.ir-adjust__number').exists()).toBe(true)
  })

  it('V2 中省份仍只读，节点/容量/功率仍可编辑', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: {
        paramDict: PARAM_DICT,
        switches: { switch_spot: 1 },
        seedInput: SEED,
        stationOptions: ['祥泰站'],
        version: 'V2',
      },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')

    expect(wrapper.findAll('.ir-adjust__ro').some((node) => node.text().includes('甘肃'))).toBe(true)
    expect(wrapper.find('.ir-adjust__select').exists()).toBe(true)
    expect(wrapper.findAll('.ir-adjust__project-item input.ir-adjust__number')).toHaveLength(2)
  })

  it('高级参数字段（如换电成本）不在内联调整面板重复展示', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: { paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2' },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')

    expect(wrapper.text()).not.toContain('换电成本')
  })

  it('已从产品需求中移除的 operation_years 即便仍在字典里返回，也不会渲染在任何分区', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: {
        paramDict: [...PARAM_DICT, { id: 'operation_years', cn: '项目运营期', zone: 'financial_boundary', control: 'fixed', default: 15, unit: '年' }],
        switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2',
      },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')

    expect(wrapper.text()).not.toContain('项目运营期')
  })

  it('现货基准缺失时显示"数据待完善"且不渲染滑块', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: {
        paramDict: PARAM_DICT, switches: { switch_spot: 1 },
        seedInput: { ...SEED, spot_charge_avg: null }, version: 'V2',
      },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')

    expect(wrapper.text()).toContain('数据待完善')
  })

  it('switch_spot=0 时不展示现货参数', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: { paramDict: PARAM_DICT, switches: { switch_spot: 0 }, seedInput: SEED, version: 'V2' },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')

    expect(wrapper.text()).not.toContain('现货充电均价')
  })

  it('省份的无单位占位符不渲染在值后方', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: { paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2' },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')

    const province = wrapper.findAll('.ir-adjust__field')
      .find((field) => field.text().includes('所在省份'))
    expect(province?.text()).toContain('甘肃')
    expect(province?.text()).not.toContain('甘肃 —')
  })

  it('滑动条卡片不展示默认值，只在有偏移时展示偏移量', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: { paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2' },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')

    expect(wrapper.text()).not.toContain('默认')
  })

  it('主重新测算将已暂存的高级参数覆盖与普通参数覆盖合并提交', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: {
        paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2',
        advancedOverrides: { maint_cost: 0.006, strategy_achievement_rate: 0.85 },
      },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')
    await wrapper.find('.ir-adjust__submit').trigger('click')

    expect(wrapper.emitted('recalculate')[0][0].overrides).toMatchObject({
      epc_unit_price: 0.8, spot_charge_avg: 0.22, spot_discharge_avg: 0.61,
      maint_cost: 0.006, strategy_achievement_rate: 0.85,
    })
  })

  it('renders 高级参数 in the persistent header and emits open-advanced while collapsed', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: { paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2' },
    })

    const header = wrapper.find('.ir-adjust__header')
    expect(wrapper.find('.ir-adjust__body').exists()).toBe(false)
    expect(header.find('.ir-adjust__advanced').exists()).toBe(true)
    await header.find('.ir-adjust__advanced').trigger('click')
    expect(wrapper.emitted('open-advanced')).toHaveLength(1)
  })

  it('exposes disclosure state and staged advanced-change count accessibly', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: {
        paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED,
        version: 'V2', advancedOverrideCount: 2,
      },
    })
    const toggle = wrapper.find('.ir-adjust__toggle')
    expect(toggle.attributes('aria-expanded')).toBe('false')
    expect(toggle.attributes('aria-controls')).toBe('ir-adjust-panel-body')
    expect(wrapper.find('.ir-adjust__draft-count').text()).toBe('2')
    expect(wrapper.find('.ir-adjust__advanced').attributes('aria-label')).toContain('已暂存 2 项修改')

    await toggle.trigger('click')
    expect(toggle.attributes('aria-expanded')).toBe('true')
    expect(wrapper.find('#ir-adjust-panel-body').exists()).toBe(true)
    expect(wrapper.text()).toContain('2 项高级修改将在重新测算时生效')
  })

  it('提交时携带面板当前完整值作为 overrides 与基础字段', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: { paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2' },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')

    await wrapper.find('.ir-adjust__submit').trigger('click')

    const emitted = wrapper.emitted('recalculate')
    expect(emitted).toHaveLength(1)
    expect(emitted[0][0]).toEqual({
      overrides: { epc_unit_price: 0.8, spot_charge_avg: 0.22, spot_discharge_avg: 0.61 },
      basics: { node_name: '祥泰站', capacity_mwh: 800, power_mw: 200 },
    })
  })

  it('V1 提交时携带用户修改后的节点、容量与功率', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: {
        paramDict: PARAM_DICT,
        switches: { switch_spot: 1 },
        seedInput: SEED,
        stationOptions: ['祥泰站', '新节点'],
        version: 'V1',
      },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')

    await wrapper.find('.ir-adjust__select').setValue('新节点')
    const projectInputs = wrapper.findAll('.ir-adjust__project-item input.ir-adjust__number')
    await projectInputs[0].setValue(250)
    await projectInputs[1].setValue(1000)
    await wrapper.find('.ir-adjust__submit').trigger('click')

    expect(wrapper.emitted('recalculate')[0][0].basics).toEqual({
      node_name: '新节点',
      capacity_mwh: 1000,
      power_mw: 250,
    })
  })

  it('恢复本次测算值只重置常用参数且不影响高级草稿', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: {
        paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2',
        advancedOverrides: { maint_cost: 0.006 }, advancedOverrideCount: 1,
      },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')
    const reset = wrapper.find('.ir-adjust__reset')
    expect(reset.attributes('disabled')).toBeDefined()

    const projectInputs = wrapper.findAll('.ir-adjust__project-item input.ir-adjust__number')
    await projectInputs[0].setValue(250)
    expect(reset.attributes('disabled')).toBeUndefined()
    await reset.trigger('click')

    expect(projectInputs[0].element.value).toBe('200')
    expect(reset.attributes('disabled')).toBeDefined()
    await wrapper.find('.ir-adjust__submit').trigger('click')
    expect(wrapper.emitted('recalculate')[0][0].overrides).toMatchObject({ maint_cost: 0.006 })
  })

  it('reports regular draft state after editing, resetting and receiving new frozen input', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: { paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2' },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')
    expect(wrapper.emitted('dirty-change')?.at(-1)).toEqual([false])

    await wrapper.find('.ps-val-input').setValue(0.82)
    expect(wrapper.emitted('dirty-change')?.at(-1)).toEqual([true])

    await wrapper.find('.ir-adjust__reset').trigger('click')
    expect(wrapper.emitted('dirty-change')?.at(-1)).toEqual([false])

    await wrapper.find('.ps-val-input').setValue(0.83)
    await wrapper.setProps({ seedInput: { ...SEED, epc_unit_price: 0.79 } })
    expect(wrapper.emitted('dirty-change')?.at(-1)).toEqual([false])
  })

  it('测算中禁用展开与提交按钮', () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: { paramDict: PARAM_DICT, switches: {}, seedInput: SEED, version: 'V2', responding: true },
    })
    expect(wrapper.find('.ir-adjust__toggle').attributes('disabled')).toBeDefined()
  })
})

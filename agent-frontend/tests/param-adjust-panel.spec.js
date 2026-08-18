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

const DELTA_PARAM_DICT = [
  ...PARAM_DICT,
  { id: 'daily_cycles', cn: '日均充放电次数', zone: 'revenue_boundary', control: 'slider', min: 1, max: 2, step: 0.1, default: 1, unit: '次/天' },
  { id: 'frequency_first_year_revenue', cn: '首年调频收益', zone: 'revenue_boundary', control: 'dynamic_slider', step: 0.01, unit: '万元' },
]

const SEED = {
  province: '甘肃', node_name: '祥泰站', capacity_mwh: 800, power_mw: 200,
  epc_unit_price: 0.8, spot_charge_avg: 0.22, spot_discharge_avg: 0.61,
}

const DELTA_SEED = {
  ...SEED,
  daily_cycles: 1,
  frequency_first_year_revenue: 2000,
}

describe('ParamAdjustPanel', () => {
  it('shows chat-driven changes against the previous calculation version', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: {
        paramDict: DELTA_PARAM_DICT,
        switches: { switch_frequency: 1, switch_spot: 1 },
        seedInput: { ...DELTA_SEED, daily_cycles: 2, frequency_first_year_revenue: 3000 },
        comparisonInput: DELTA_SEED,
        version: 'V2',
      },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')

    const fields = wrapper.findAll('.ir-adjust__field')
    const daily = fields.find((field) => field.text().includes('日均充放电次数'))
    const frequency = fields.find((field) => field.text().includes('首年调频收益'))

    expect(daily?.find('.ps-delta').text()).toBe('+1.0次/天')
    expect(frequency?.find('.ps-delta').text()).toBe('+1000.00万元')
  })

  it('default collapsed; expanding renders zones', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: { paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2' },
    })
    expect(wrapper.find('.ir-adjust__body').exists()).toBe(false)
    expect(wrapper.find('.ir-adjust__pending-bar').exists()).toBe(false)

    await wrapper.find('.ir-adjust__toggle').trigger('click')

    expect(wrapper.find('.ir-adjust__body').exists()).toBe(true)
    expect(wrapper.text()).toContain('项目信息')
    expect(wrapper.text()).toContain('金融边界')
    expect(wrapper.text()).toContain('收益边界')
    expect(wrapper.findAll('.ir-adjust__zone')).toHaveLength(3)
    expect(wrapper.findAll('.ir-adjust__project-item')).toHaveLength(4)
    expect(wrapper.find('.ir-adjust__zone-card').exists()).toBe(false)
    expect(wrapper.find('.ir-adjust__heading-copy small').text()).toBe('可修改项目、财务、收益及运营参数')
    expect(wrapper.findAll('.ir-adjust__tabs button').map((button) => button.text())).toEqual(['常用参数', '高级参数'])
    expect(wrapper.find('.ir-adjust__tab-toolbar').text()).toContain('常用参数暂无修改')
    expect(wrapper.find('.ir-adjust__scope-reset').attributes('disabled')).toBeDefined()
    const slider = wrapper.find('.ir-adjust__slider')
    await slider.trigger('pointerenter')
    expect(wrapper.find('.ps-input-hint').text()).toBe('点击数值可精确输入')
    await slider.trigger('pointerdown')
    await slider.trigger('focus')
    expect(wrapper.find('.ps-input-hint').exists()).toBe(false)
  })

  it('输入越界值时保留输入、保持滑块有效值并阻止重新测算', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: { paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2' },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')
    const input = wrapper.find('.ps-val-input')
    const slider = wrapper.find('.ir-adjust__slider')

    await input.setValue(0.9)

    expect(input.element.value).toBe('0.9')
    expect(input.attributes('aria-invalid')).toBe('true')
    expect(wrapper.find('.ps-validation').text()).toBe('不能高于 0.85')
    expect(slider.element.value).toBe('0.8')
    expect(wrapper.find('.ir-adjust__submit').attributes('disabled')).toBeDefined()
    await wrapper.find('.ir-adjust__submit').trigger('click')
    expect(wrapper.emitted('recalculate')).toBeUndefined()
  })

  it('修正输入或拖动滑块后清除越界提示并同步数值', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: { paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2' },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')
    const input = wrapper.find('.ps-val-input')
    const slider = wrapper.find('.ir-adjust__slider')

    await input.setValue(0.9)
    await input.setValue(0.82)
    await input.trigger('blur')
    expect(wrapper.find('.ps-validation').exists()).toBe(false)
    expect(slider.element.value).toBe('0.82')

    await input.setValue(0.9)
    await slider.setValue(0.81)
    expect(wrapper.find('.ps-validation').exists()).toBe(false)
    expect(input.element.value).toBe('0.81')
  })

  it('项目数字输入为空时显示统一错误并阻止重新测算', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: { paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2' },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')
    const input = wrapper.findAll('.ir-adjust__project-item input.ir-adjust__number')[0]

    await input.setValue('')

    expect(input.element.value).toBe('')
    expect(input.attributes('aria-invalid')).toBe('true')
    expect(wrapper.find('.ps-validation--project').text()).toBe('请输入有效数值')
    expect(wrapper.find('.ir-adjust__submit').attributes('disabled')).toBeDefined()

    await input.setValue(250)
    await input.trigger('blur')
    expect(input.attributes('aria-invalid')).toBe('false')
    expect(wrapper.find('.ps-validation--project').exists()).toBe(false)
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
    const nodeTrigger = wrapper.find('.ir-adjust__node-trigger')
    expect(nodeTrigger.exists()).toBe(true)
    expect(nodeTrigger.text()).toContain('祥泰站')
    expect(nodeTrigger.text()).toContain('更改')
    expect(nodeTrigger.attributes('aria-label')).toContain('当前为 祥泰站')
    expect(wrapper.findComponent({ name: 'ElSelect' }).exists()).toBe(false)

    wrapper.findComponent({ name: 'ElPopover' }).vm.$emit('update:visible', true)
    await wrapper.vm.$nextTick()
    const nodeSelect = wrapper.findComponent({ name: 'ElSelect' })
    expect(nodeSelect.exists()).toBe(true)
    expect(nodeSelect.props('filterable')).toBe(true)
    expect(nodeSelect.props('placeholder')).toBe('搜索或选择节点')
    expect(nodeSelect.props('noMatchText')).toBe('未找到匹配节点')
    expect(nodeSelect.props('popperClass')).toContain('ir-adjust__node-popper')

    const projectFields = wrapper.findAll('.ir-adjust__project-item')
    const capacityField = projectFields.find((field) => field.text().includes('装机容量'))
    const powerField = projectFields.find((field) => field.text().includes('储能装机功率'))
    expect(capacityField?.find('input.ir-adjust__number').exists()).toBe(true)
    expect(powerField?.find('input.ir-adjust__number').exists()).toBe(true)
  })

  it('节点选择器使用远程搜索，并转发打开、搜索和续载意图', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      attachTo: document.body,
      props: {
        paramDict: PARAM_DICT,
        switches: { switch_spot: 1 },
        seedInput: SEED,
        stationOptions: [],
        stationLoading: true,
        stationHasMore: true,
        stationError: '节点目录暂不可用',
        version: 'V2',
      },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')
    const nodePopover = wrapper.findComponent({ name: 'ElPopover' })
    nodePopover.vm.$emit('update:visible', true)
    await wrapper.vm.$nextTick()

    const nodeSelect = wrapper.findComponent({ name: 'ElSelect' })
    expect(nodeSelect.props('remote')).toBe(true)
    expect(nodeSelect.props('loading')).toBe(true)
    expect(nodeSelect.props('noDataText')).toBe('节点目录暂不可用')
    expect(wrapper.emitted('station-open')?.[0][0]).toEqual({
      province: '甘肃', selectedNode: '祥泰站',
    })

    nodeSelect.props('remoteMethod')('新')
    await new Promise((resolve) => setTimeout(resolve, 320))
    expect(wrapper.emitted('station-search')?.[0][0]).toEqual({
      province: '甘肃', keyword: '新', selectedNode: '祥泰站',
    })

    await wrapper.setProps({ stationOptions: ['新节点'], stationLoading: false })
    const scrollContainer = document.querySelector(
      `.${nodeSelect.props('popperClass').split(' ').at(-1)} .el-select-dropdown__wrap`,
    )
    Object.defineProperties(scrollContainer, {
      clientHeight: { configurable: true, value: 240 },
      scrollHeight: { configurable: true, value: 320 },
    })
    nodeSelect.vm.$emit('popup-scroll', { scrollTop: 80, scrollLeft: 0 })
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('station-load-more')?.[0][0]).toEqual({
      selectedNode: '祥泰站',
    })
  })

  it('节点选择器按实际滚动尺寸连续续载，不依赖选项数量估算高度', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      attachTo: document.body,
      props: {
        paramDict: PARAM_DICT,
        switches: { switch_spot: 1 },
        seedInput: SEED,
        stationOptions: Array.from({ length: 30 }, (_, index) => `节点${index + 1}`),
        stationHasMore: true,
        version: 'V2',
      },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')
    wrapper.findComponent({ name: 'ElPopover' }).vm.$emit('update:visible', true)
    await wrapper.vm.$nextTick()

    const nodeSelect = wrapper.findComponent({ name: 'ElSelect' })
    expect(nodeSelect.props('loading')).toBe(false)
    const popperClass = nodeSelect.props('popperClass').split(' ').at(-1)
    expect(document.querySelector(`.${popperClass} .ir-adjust__node-load-more`)).toBeNull()
    const scrollContainer = document.querySelector(
      `.${popperClass} .el-select-dropdown__wrap`,
    )
    Object.defineProperties(scrollContainer, {
      clientHeight: { configurable: true, value: 180 },
      scrollHeight: { configurable: true, value: 900 },
    })

    nodeSelect.vm.$emit('popup-scroll', { scrollTop: 500, scrollLeft: 0 })
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('station-load-more')).toBeUndefined()

    nodeSelect.vm.$emit('popup-scroll', { scrollTop: 720, scrollLeft: 0 })
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('station-load-more')).toHaveLength(1)

    await wrapper.setProps({ stationLoading: true })
    expect(nodeSelect.props('loading')).toBe(false)
    expect(document.querySelector(`.${popperClass} .ir-adjust__node-load-more`)?.textContent).toContain('加载更多节点')

    await wrapper.setProps({
      stationLoading: false,
      stationOptions: Array.from({ length: 60 }, (_, index) => `节点${index + 1}`),
    })
    Object.defineProperty(scrollContainer, 'scrollHeight', { configurable: true, value: 1800 })
    nodeSelect.vm.$emit('popup-scroll', { scrollTop: 1620, scrollLeft: 0 })
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('station-load-more')).toHaveLength(2)
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
    expect(wrapper.find('.ir-adjust__node-trigger').exists()).toBe(true)
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
        advancedOverrideCount: 2,
      },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')
    await wrapper.find('.ir-adjust__submit').trigger('click')

    expect(wrapper.emitted('recalculate')[0][0].overrides).toEqual({
      maint_cost: 0.006, strategy_achievement_rate: 0.85,
    })
  })

  it('折叠时可直接提交已暂存的高级参数修改', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: {
        paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2',
        advancedOverrides: { maint_cost: 0.006 }, advancedOverrideCount: 1,
      },
    })

    expect(wrapper.find('.ir-adjust__body').exists()).toBe(false)
    expect(wrapper.find('.ir-adjust__pending-bar').text()).toContain('1 项高级参数已修改')
    await wrapper.find('.ir-adjust__pending-bar .ir-adjust__submit').trigger('click')

    expect(wrapper.emitted('recalculate')).toHaveLength(1)
    expect(wrapper.emitted('recalculate')[0][0].overrides).toEqual({ maint_cost: 0.006 })
  })

  it('常用参数修改后收起面板仍可重新测算', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: { paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2' },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')
    await wrapper.find('.ps-val-input').setValue(0.82)
    await wrapper.find('.ir-adjust__toggle').trigger('click')

    expect(wrapper.find('.ir-adjust__body').exists()).toBe(false)
    expect(wrapper.find('.ir-adjust__pending-bar').text()).toContain('常用参数已修改')
    await wrapper.find('.ir-adjust__pending-bar .ir-adjust__submit').trigger('click')
    expect(wrapper.emitted('recalculate')[0][0].overrides.epc_unit_price).toBe(0.82)
  })

  it('撤销常用参数修改只恢复常用参数并保留高级参数草稿', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: {
        paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2',
        advancedOverrides: { maint_cost: 0.006 }, advancedOverrideCount: 1,
      },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')
    await wrapper.find('.ps-val-input').setValue(0.82)

    expect(wrapper.findAll('.ir-adjust__tabs button')[0].text()).toContain('1')
    expect(wrapper.find('.ir-adjust__tab-toolbar').text()).toContain('已修改 1 项常用参数')
    expect(wrapper.find('.ir-adjust__scope-reset').text()).toBe('撤销常用参数修改')
    expect(wrapper.find('.ir-adjust__scope-reset').attributes('disabled')).toBeUndefined()
    await wrapper.find('.ir-adjust__scope-reset').trigger('click')

    expect(wrapper.find('.ps-val-input').element.value).toBe('0.8')
    expect(wrapper.findAll('.ir-adjust__tabs button')[0].text()).toBe('常用参数')
    expect(wrapper.find('.ir-adjust__tab-toolbar').text()).toContain('常用参数暂无修改')
    expect(wrapper.find('.ir-adjust__scope-reset').attributes('disabled')).toBeDefined()
    expect(wrapper.emitted('discard-all-changes')).toBeUndefined()
    expect(wrapper.text()).toContain('1 项高级参数已修改，重新测算后生效')
    expect(wrapper.find('.ir-adjust__footer .ir-adjust__reset').text()).toBe('放弃全部修改')
    expect(wrapper.find('.ir-adjust__footer .ir-adjust__submit').attributes('disabled')).toBeUndefined()
  })

  it('常用参数标签显示实际修改项数并随改回冻结值更新', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: { paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2' },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')
    const inputs = wrapper.findAll('.ps-val-input')

    await inputs[0].setValue(0.82)
    await inputs[1].setValue(0.24)
    expect(wrapper.findAll('.ir-adjust__tabs button')[0].text()).toContain('2')
    expect(wrapper.find('.ir-adjust__tab-toolbar').text()).toContain('已修改 2 项常用参数')

    await inputs[0].setValue(0.8)
    expect(wrapper.findAll('.ir-adjust__tabs button')[0].text()).toContain('1')
    expect(wrapper.find('.ir-adjust__tab-toolbar').text()).toContain('已修改 1 项常用参数')
  })

  it('uses one explicit adjustment entry and reveals common/advanced tabs after expanding', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: { paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2' },
    })

    const header = wrapper.find('.ir-adjust__header')
    expect(wrapper.find('.ir-adjust__body').exists()).toBe(false)
    expect(header.find('.ir-adjust__toggle-action').text()).toContain('调整参数')
    expect(header.find('.ir-adjust__advanced').exists()).toBe(false)
    await header.find('.ir-adjust__toggle').trigger('click')
    expect(wrapper.findAll('.ir-adjust__tabs button')).toHaveLength(2)
    expect(wrapper.find('.ir-adjust__tabs button.is-active').text()).toBe('常用参数')
    await wrapper.findAll('.ir-adjust__tabs button')[1].trigger('click')
    expect(wrapper.find('.ir-adjust__tabs button.is-active').text()).toBe('高级参数')
    expect(wrapper.find('.ir-adjust__toggle-action').text()).toContain('收起')
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
    expect(wrapper.find('.ir-adjust__draft-count').exists()).toBe(false)

    await toggle.trigger('click')
    expect(toggle.attributes('aria-expanded')).toBe('true')
    expect(wrapper.find('#ir-adjust-panel-body').exists()).toBe(true)
    expect(wrapper.find('.ir-adjust__tabs .ir-adjust__draft-count').text()).toBe('2')
    expect(wrapper.findAll('.ir-adjust__tabs button')[1].attributes('aria-selected')).toBe('false')
    expect(wrapper.text()).toContain('2 项高级参数已修改，重新测算后生效')
  })

  it('没有参数修改时禁用重新测算且不会提交', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: { paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2' },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')

    const submit = wrapper.find('.ir-adjust__submit')
    expect(submit.attributes('disabled')).toBeDefined()
    await submit.trigger('click')
    expect(wrapper.emitted('recalculate')).toBeUndefined()
  })

  it('修改参数后提交当前完整值作为 overrides 与基础字段', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: { paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2' },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')
    await wrapper.find('.ps-val-input').setValue(0.82)

    await wrapper.find('.ir-adjust__submit').trigger('click')

    const emitted = wrapper.emitted('recalculate')
    expect(emitted).toHaveLength(1)
    expect(emitted[0][0]).toEqual({
      overrides: { epc_unit_price: 0.82 },
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

    wrapper.findComponent({ name: 'ElPopover' }).vm.$emit('update:visible', true)
    await wrapper.vm.$nextTick()
    const nodeSelect = wrapper.findComponent({ name: 'ElSelect' })
    nodeSelect.vm.$emit('update:modelValue', '新节点')
    nodeSelect.vm.$emit('change', '新节点')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.ir-adjust__node-trigger').text()).toContain('新节点')
    expect(wrapper.findComponent({ name: 'ElSelect' }).exists()).toBe(false)
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

  it('放弃全部修改会恢复常用参数并请求父组件清除高级草稿', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: {
        paramDict: PARAM_DICT, switches: { switch_spot: 1 }, seedInput: SEED, version: 'V2',
        advancedOverrides: { maint_cost: 0.006 }, advancedOverrideCount: 1,
      },
    })
    await wrapper.find('.ir-adjust__toggle').trigger('click')
    const discard = wrapper.find('.ir-adjust__reset')
    expect(discard.attributes('disabled')).toBeUndefined()
    expect(discard.text()).toBe('放弃全部修改')

    const projectInputs = wrapper.findAll('.ir-adjust__project-item input.ir-adjust__number')
    await projectInputs[0].setValue(250)
    await discard.trigger('click')

    expect(projectInputs[0].element.value).toBe('200')
    expect(wrapper.emitted('dirty-change')?.at(-1)).toEqual([false])
    expect(wrapper.emitted('discard-all-changes')).toHaveLength(1)
    await wrapper.setProps({ advancedOverrides: {}, advancedOverrideCount: 0 })
    expect(wrapper.find('.ir-adjust__submit').attributes('disabled')).toBeDefined()
    await wrapper.find('.ir-adjust__submit').trigger('click')
    expect(wrapper.emitted('recalculate')).toBeUndefined()
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

  it('测算中禁用折叠态与展开态的参数操作', async () => {
    const wrapper = mount(ParamAdjustPanel, {
      props: {
        paramDict: PARAM_DICT, switches: {}, seedInput: SEED, version: 'V2', responding: true,
        advancedOverrides: { maint_cost: 0.006 }, advancedOverrideCount: 1,
      },
    })
    expect(wrapper.find('.ir-adjust__toggle').attributes('disabled')).toBeDefined()
    expect(wrapper.find('.ir-adjust__pending-bar .ir-adjust__reset').attributes('disabled')).toBeDefined()
    expect(wrapper.find('.ir-adjust__pending-bar .ir-adjust__submit').attributes('disabled')).toBeDefined()
    await wrapper.find('.ir-adjust__pending-bar .ir-adjust__submit').trigger('click')
    expect(wrapper.emitted('recalculate')).toBeUndefined()

    await wrapper.setProps({ responding: false })
    await wrapper.find('.ir-adjust__toggle').trigger('click')
    await wrapper.setProps({ responding: true })
    expect(wrapper.find('.ir-adjust__footer .ir-adjust__reset').attributes('disabled')).toBeDefined()
    expect(wrapper.find('.ir-adjust__footer .ir-adjust__submit').attributes('disabled')).toBeDefined()
  })
})

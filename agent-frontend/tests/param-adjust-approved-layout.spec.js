import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ParamAdjustPanel from '@/views/home/components/ParamAdjustPanel.vue'

const PARAM_DICT = [
  { id: 'province', cn: '所在省份', zone: 'project_definition', control: 'fixed', default: null },
  { id: 'node_name', cn: '节点名称', zone: 'project_definition', control: 'select', default: null },
  { id: 'power_mw', cn: '装机功率', zone: 'project_definition', control: 'number', default: null, unit: 'MW' },
  { id: 'capacity_mwh', cn: '装机容量', zone: 'project_definition', control: 'number', default: null, unit: 'MWh' },
  // operation_years 仍可能出现在后端字典里（历史遗留字段），面板必须始终把它剔除，不展示在任何分区。
  { id: 'operation_years', cn: '项目运营期', zone: 'financial_boundary', control: 'fixed', default: 15, unit: '年' },
  { id: 'epc_unit_price', cn: 'EPC单价', zone: 'financial_boundary', control: 'slider', min: 0.7, max: 0.85, step: 0.01, default: 0.75 },
  { id: 'loan_rate', cn: '贷款利率', zone: 'financial_boundary', control: 'slider', min: 0.035, max: 0.045, step: 0.001, default: 0.04 },
  { id: 'loan_years', cn: '贷款年限', zone: 'financial_boundary', control: 'slider', min: 1, max: 20, step: 1, default: 10, unit: '年' },
  { id: 'spot_charge_avg', cn: '现货充电均价', zone: 'revenue_boundary', control: 'dynamic_slider', step: 0.0001, unit: '元/kWh' },
  { id: 'spot_discharge_avg', cn: '现货放电均价', zone: 'revenue_boundary', control: 'dynamic_slider', step: 0.0001, unit: '元/kWh' },
  { id: 'daily_cycles', cn: '日均充放电次数', zone: 'revenue_boundary', control: 'slider', min: 1, max: 2, step: 0.1, default: 1, unit: '次/天' },
  { id: 'mid_long_energy_revenue_first_year_tax', cn: '中长期电能量收入', zone: 'revenue_boundary', control: 'dynamic_slider', step: 0.01, unit: '万元' },
  { id: 'frequency_first_year_revenue', cn: '调频收入', zone: 'revenue_boundary', control: 'dynamic_slider', step: 0.01, unit: '万元' },
  { id: 'intervention_first_year_revenue', cn: '干预补偿', zone: 'revenue_boundary', control: 'dynamic_slider', step: 0.01, unit: '万元' },
  { id: 'lease_unit_price', cn: '租赁单价', zone: 'revenue_boundary', control: 'dynamic_slider', step: 0.01, unit: '元/kW·年' },
  { id: 'lease_achievement_rate', cn: '租赁达成率', zone: 'revenue_boundary', control: 'slider', min: 0.7, max: 0.95, step: 0.01, default: 0.9 },
]

const SEED = {
  province: '蒙西', node_name: '祥泰站', power_mw: 200, capacity_mwh: 800,
  spot_charge_avg: 0.22, spot_discharge_avg: 0.61,
  mid_long_energy_revenue_first_year_tax: 100, frequency_first_year_revenue: 200,
  intervention_first_year_revenue: 50, lease_unit_price: 20,
}

async function expandedPanel(stationOptions = []) {
  const wrapper = mount(ParamAdjustPanel, {
    props: {
      paramDict: PARAM_DICT,
      switches: {
        switch_spot: 1, switch_mid_long: 1, switch_frequency: 1,
        switch_intervention: 1, switch_lease: 1,
      },
      seedInput: SEED,
      stationOptions,
      version: 'V2',
    },
  })
  await wrapper.find('.ir-adjust__toggle').trigger('click')
  return wrapper
}

describe('ParamAdjustPanel approved layout', () => {
  it('renders 项目信息 as four evenly distributed information cards in one row, in the requested order', async () => {
    const wrapper = await expandedPanel(['祥泰站', '乌达站'])
    const project = wrapper.find('.ir-adjust__zone--project_definition')

    expect(project.find('.ir-adjust__zone-title').text()).toBe('项目信息')
    expect(project.findAll('.ir-adjust__field').map((field) => field.text())).toEqual([
      expect.stringContaining('所在省份'),
      expect.stringContaining('节点名称'),
      expect.stringContaining('装机功率'),
      expect.stringContaining('装机容量'),
    ])
    expect(project.findAll('.ir-adjust__info-card')).toHaveLength(4)
    // 单行分布容器：卡片宽度贴合内容、由 CSS space-between 均匀分布，而非堆叠在最左侧
    expect(project.find('.ir-adjust__row--cards').exists()).toBe(true)
    expect(project.findAll('.ir-adjust__row--cards > .ir-adjust__field')).toHaveLength(4)
    expect(project.find('.ir-adjust__select').exists()).toBe(true)
    expect(project.findAll('.ir-adjust__select option').map((option) => option.text())).toEqual(['祥泰站', '乌达站'])
  })

  it('hides 节点名称 entirely when the selected province has no station options', async () => {
    const wrapper = await expandedPanel([])
    const project = wrapper.find('.ir-adjust__zone--project_definition')

    expect(project.text()).not.toContain('节点名称')
    expect(project.findAll('.ir-adjust__info-card')).toHaveLength(3)
  })

  it('drops 项目运营期 everywhere even though the backend dictionary still returns it', async () => {
    const wrapper = await expandedPanel(['祥泰站'])

    expect(wrapper.text()).not.toContain('项目运营期')
  })

  it('puts EPC单价 alone on its own half-width row, and 贷款利率/贷款年限 paired on the next row', async () => {
    const wrapper = await expandedPanel(['祥泰站'])
    const financial = wrapper.find('.ir-adjust__zone--financial_boundary')
    const rows = financial.findAll('.ir-adjust__row')

    expect(rows).toHaveLength(2)
    expect(rows[0].classes()).toContain('ir-adjust__row--single')
    expect(rows[0].findAll('.ir-adjust__field')).toHaveLength(1)
    expect(rows[0].text()).toContain('EPC单价')

    expect(rows[1].classes()).not.toContain('ir-adjust__row--single')
    expect(rows[1].findAll('.ir-adjust__field').map((field) => field.text())).toEqual([
      expect.stringContaining('贷款利率'),
      expect.stringContaining('贷款年限'),
    ])
  })

  it('pairs 现货充电均价/现货放电均价 on one row and keeps other revenue sliders one-per-row', async () => {
    const wrapper = await expandedPanel(['祥泰站'])
    const revenue = wrapper.find('.ir-adjust__zone--revenue_boundary')
    const rows = revenue.findAll('.ir-adjust__row')

    expect(rows[0].classes()).not.toContain('ir-adjust__row--single')
    expect(rows[0].findAll('.ir-adjust__field').map((field) => field.text())).toEqual([
      expect.stringContaining('现货充电均价'),
      expect.stringContaining('现货放电均价'),
    ])

    const singleRowTexts = rows.filter((row) => row.classes().includes('ir-adjust__row--single')).map((row) => row.text())
    expect(singleRowTexts).toEqual([
      expect.stringContaining('日均充放电次数'),
      expect.stringContaining('中长期电能量收入'),
      expect.stringContaining('调频收入'),
      expect.stringContaining('干预补偿'),
    ])

    const lastRow = rows[rows.length - 1]
    expect(lastRow.classes()).not.toContain('ir-adjust__row--single')
    expect(lastRow.findAll('.ir-adjust__field').map((field) => field.text())).toEqual([
      expect.stringContaining('租赁单价'),
      expect.stringContaining('租赁达成率'),
    ])
  })
})

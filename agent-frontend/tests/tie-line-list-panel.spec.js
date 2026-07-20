import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import TieLineListPanel from '@/views/tie-line/components/TieLineListPanel.vue'

const lines = [
  { id: 1, name: '甲乙线', startPoint: '甲站', endPoint: '乙站', lengthText: '100 km', voltageText: '500 kV' },
  { id: 2, name: '乙丙线', startPoint: '乙站', endPoint: '丙站', lengthText: '200 km', voltageText: '±800 kV' },
]

function mountPanel(props = {}) {
  return mount(TieLineListPanel, {
    props: { open: true, lines, voltageOptions: ['500 kV', '±800 kV'], ...props },
  })
}

describe('联络线线路列表', () => {
  it('渲染当前可见线路并反映选中态', () => {
    const wrapper = mountPanel({ selectedId: 2 })

    expect(wrapper.find('[role="listbox"]').exists()).toBe(true)
    expect(wrapper.findAll('[role="option"]')).toHaveLength(2)
    expect(wrapper.findAll('[role="option"]')[1].attributes('aria-selected')).toBe('true')
    expect(wrapper.findAll('[role="option"]')[1].attributes('tabindex')).toBe('0')
  })

  it('支持点击、Enter 与 Space 选择线路', async () => {
    const wrapper = mountPanel()
    const items = wrapper.findAll('[role="option"]')

    await items[0].trigger('click')
    await wrapper.find('[role="listbox"]').trigger('keydown', { key: 'ArrowDown' })
    await wrapper.find('[role="listbox"]').trigger('keydown', { key: 'Enter' })
    await wrapper.find('[role="listbox"]').trigger('keydown', { key: ' ' })

    expect(wrapper.emitted('select')).toEqual([[1], [2], [2]])
  })

  it('支持方向键循环、Home、End 和 Escape', async () => {
    const wrapper = mountPanel()
    const listbox = wrapper.find('[role="listbox"]')

    await listbox.trigger('keydown', { key: 'ArrowUp' })
    expect(wrapper.findAll('[role="option"]')[1].attributes('tabindex')).toBe('0')
    await listbox.trigger('keydown', { key: 'Home' })
    expect(wrapper.findAll('[role="option"]')[0].attributes('tabindex')).toBe('0')
    await listbox.trigger('keydown', { key: 'End' })
    expect(wrapper.findAll('[role="option"]')[1].attributes('tabindex')).toBe('0')
    await listbox.trigger('keydown', { key: 'Escape' })
    expect(wrapper.emitted('close')).toHaveLength(1)
  })

  it('空线路时显示空态而不渲染 option', () => {
    const wrapper = mountPanel({ lines: [] })

    expect(wrapper.findAll('[role="option"]')).toHaveLength(0)
    expect(wrapper.text()).toContain('当前筛选条件下暂无线路')
  })
})

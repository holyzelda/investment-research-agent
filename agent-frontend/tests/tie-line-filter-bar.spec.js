import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import TieLineFilterBar from '@/views/tie-line/components/TieLineFilterBar.vue'

function mountBar(props = {}) {
  return mount(TieLineFilterBar, {
    props: { startRegion: '西北', endRegion: '华南', minCapacityMw: 0, maxCapacityMw: 8000, regionOptions: ['西北', '华南'], ...props },
  })
}

describe('联络线筛选栏', () => {
  it('渲染容量区间输入并派发受控更新事件', async () => {
    const wrapper = mountBar()
    const inputs = wrapper.findAll('input')

    expect(inputs).toHaveLength(2)
    expect(inputs[0].attributes('type')).toBe('number')
    expect(inputs[0].attributes('min')).toBe('0')
    expect(inputs[0].attributes('step')).toBe('1')
    expect(inputs[0].element.value).toBe('0')

    await inputs[0].setValue('4000')
    await inputs[1].setValue('')
    expect(wrapper.emitted('update:min-capacity-mw')).toEqual([['4000']])
    expect(wrapper.emitted('update:max-capacity-mw')).toEqual([['']])
  })

  it('派发区域交换和筛选重置事件', async () => {
    const wrapper = mountBar()

    await wrapper.find('.tl-filter__swap').trigger('click')
    await wrapper.find('.tl-filter__reset').trigger('click')

    expect(wrapper.emitted('swap-regions')).toHaveLength(1)
    expect(wrapper.emitted('reset-filters')).toHaveLength(1)
    expect(wrapper.props('startRegion')).toBe('西北')
    expect(wrapper.find('.xc-input').exists()).toBe(true)
    expect(wrapper.find('.xc-btn--icon').exists()).toBe(true)
    expect(wrapper.find('svg.lucide-arrow-left-right').exists()).toBe(true)
    expect(wrapper.find('.xc-input').exists()).toBe(true)
    expect(wrapper.find('.xc-btn--icon').exists()).toBe(true)
    expect(wrapper.find('svg.lucide-arrow-left-right').exists()).toBe(true)
  })
})

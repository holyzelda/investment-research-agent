import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import TieLineFilterBar from '@/views/tie-line/components/TieLineFilterBar.vue'
import tieLineFilterBarSource from '@/views/tie-line/components/TieLineFilterBar.vue?raw'

function mountBar(props = {}) {
  return mount(TieLineFilterBar, {
    props: {
      startRegion: '',
      endRegion: '',
      minCapacityMw: null,
      maxCapacityMw: null,
      regionOptions: ['西北', '华南', '华东'],
      visibleCount: 41,
      totalCount: 41,
      ...props,
    },
    global: {
      stubs: {
        ElPopover: {
          template: '<div><slot name="reference" /><div class="el-popover-stub"><slot /></div></div>',
        },
      },
    },
  })
}

describe('联络线筛选栏', () => {
  it('区域下拉使用深色 Popover 选项并派发受控更新事件', async () => {
    const wrapper = mountBar()
    const triggers = wrapper.findAll('.tl-filter-control--select')
    const options = wrapper.findAll('.tl-region-menu__option')
    const styles = tieLineFilterBarSource.match(/<style scoped>([\s\S]*)<\/style>/)?.[1] || ''

    expect(triggers).toHaveLength(2)
    expect(triggers[0].text()).toContain('全部地区')
    expect(options[0].text()).toContain('全部地区')
    expect(tieLineFilterBarSource).not.toContain('<select')
    expect(styles).toContain('.tl-region-menu__option')
    expect(styles).toContain('background: var(--xc-surface-raised)')

    await wrapper.find('[data-test="start-region-西北"]').trigger('click')
    await wrapper.find('[data-test="end-region-华南"]').trigger('click')

    expect(wrapper.emitted('update:start-region')).toEqual([['西北']])
    expect(wrapper.emitted('update:end-region')).toEqual([['华南']])
  })

  it('交换按钮只显示图标并派发交换事件', async () => {
    vi.stubGlobal('requestAnimationFrame', (callback) => callback())
    const wrapper = mountBar({ startRegion: '西北', endRegion: '华南' })
    const swap = wrapper.find('.tl-filterbar__swap')

    expect(swap.attributes('aria-label')).toBe('交换起点和终点区域')
    expect(swap.attributes('title')).toBe('交换起点与终点')
    expect(swap.text()).toBe('')
    expect(wrapper.find('svg.lucide-arrow-left-right').exists()).toBe(true)

    await swap.trigger('click')

    expect(wrapper.emitted('swap-regions')).toHaveLength(1)
    expect(swap.classes()).toContain('is-spinning')
    vi.unstubAllGlobals()
  })

  it('容量触发器展示不同范围文案', () => {
    expect(mountBar().find('.tl-filter-control--capacity .tl-filter-control__value').text()).toBe('不限')
    expect(mountBar({ minCapacityMw: 2000, maxCapacityMw: 5000 }).find('.tl-filter-control--capacity .tl-filter-control__value').text()).toBe('2,000-5,000 MW')
    expect(mountBar({ minCapacityMw: null, maxCapacityMw: 2000 }).find('.tl-filter-control--capacity .tl-filter-control__value').text()).toBe('≤ 2,000 MW')
    expect(mountBar({ minCapacityMw: 5000, maxCapacityMw: null }).find('.tl-filter-control--capacity .tl-filter-control__value').text()).toBe('≥ 5,000 MW')
  })

  it('容量 Popover 确定和清除仍派发原容量更新事件', async () => {
    const wrapper = mountBar()
    const inputs = wrapper.findAll('.tl-capacity-popover__input')

    expect(inputs).toHaveLength(2)
    expect(inputs[0].attributes('type')).toBe('number')
    expect(inputs[0].attributes('min')).toBe('0')
    expect(inputs[0].attributes('step')).toBe('1')

    await inputs[0].setValue('2000')
    await inputs[1].setValue('5000')
    await wrapper.find('[data-test="capacity-apply"]').trigger('click')

    expect(wrapper.emitted('update:min-capacity-mw')).toEqual([['2000']])
    expect(wrapper.emitted('update:max-capacity-mw')).toEqual([['5000']])

    await wrapper.find('[data-test="capacity-clear"]').trigger('click')

    expect(wrapper.emitted('update:min-capacity-mw')).toEqual([['2000'], ['']])
    expect(wrapper.emitted('update:max-capacity-mw')).toEqual([['5000'], ['']])
  })

  it('常用容量范围只更新 Popover 临时输入，确定后应用', async () => {
    const wrapper = mountBar()

    await wrapper.find('[data-test="capacity-preset-mid"]').trigger('click')

    const inputs = wrapper.findAll('.tl-capacity-popover__input')
    expect(inputs[0].element.value).toBe('2000')
    expect(inputs[1].element.value).toBe('5000')
    expect(wrapper.emitted('update:min-capacity-mw')).toBeUndefined()

    await wrapper.find('[data-test="capacity-apply"]').trigger('click')

    expect(wrapper.emitted('update:min-capacity-mw')).toEqual([['2000']])
    expect(wrapper.emitted('update:max-capacity-mw')).toEqual([['5000']])
  })

  it('筛选控件在深色主题下使用深色控件底和浅色文字', () => {
    const wrapper = mountBar({ startRegion: '西北', minCapacityMw: 2000 })
    const styles = tieLineFilterBarSource.match(/<style scoped>([\s\S]*)<\/style>/)?.[1] || ''

    expect(wrapper.find('.tl-filter-control.is-active').exists()).toBe(true)
    expect(styles).toContain('--tl-filter-bg: rgba(255, 255, 255, 0.035)')
    expect(styles).toContain('--tl-filter-bg-hover: rgba(255, 255, 255, 0.065)')
    expect(styles).toContain('color: var(--xc-text-default)')
    expect(styles).not.toContain('background: rgba(255, 255, 255, 0.94)')
  })

  it('结果文案按筛选状态展示，重置按钮仅在有筛选时启用', async () => {
    const idle = mountBar({ visibleCount: 41, totalCount: 41 })
    expect(idle.find('.tl-filterbar__result').text()).toBe('显示 41 条线路')
    expect(idle.find('.tl-filterbar__reset').attributes('disabled')).toBeDefined()

    const filtered = mountBar({ startRegion: '西北', visibleCount: 8, totalCount: 41 })
    expect(filtered.find('.tl-filterbar__result').text()).toBe('显示 8 / 41 条线路')
    expect(filtered.find('.tl-filterbar__reset').attributes('disabled')).toBeUndefined()

    await filtered.find('.tl-filterbar__reset').trigger('click')
    expect(filtered.emitted('reset-filters')).toHaveLength(1)

    const empty = mountBar({ startRegion: '西北', visibleCount: 0, totalCount: 41 })
    expect(empty.find('.tl-filterbar__result').text()).toBe('未找到符合条件的线路')
  })
})

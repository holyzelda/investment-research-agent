import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import MapToolbar from '@/views/tie-line/components/MapToolbar.vue'

describe('联络线地图工具栏', () => {
  it('提供五个可访问的工具操作', () => {
    const wrapper = mount(MapToolbar)

    expect(wrapper.findAll('button')).toHaveLength(5)
    expect(wrapper.find('[data-action="zoom-in"]').attributes('aria-label')).toBe('放大地图')
    expect(wrapper.find('[data-action="list"]').attributes('aria-pressed')).toBe('false')
  })

  it('派发地图控制事件并同步开关状态', async () => {
    const wrapper = mount(MapToolbar, { props: { isFullscreen: true, isListOpen: true } })

    await wrapper.find('[data-action="zoom-in"]').trigger('click')
    await wrapper.find('[data-action="zoom-out"]').trigger('click')
    await wrapper.find('[data-action="reset"]').trigger('click')
    await wrapper.find('[data-action="fullscreen"]').trigger('click')
    await wrapper.find('[data-action="list"]').trigger('click')

    expect(wrapper.emitted('zoom-in')).toHaveLength(1)
    expect(wrapper.emitted('zoom-out')).toHaveLength(1)
    expect(wrapper.emitted('reset')).toHaveLength(1)
    expect(wrapper.emitted('toggle-fullscreen')).toHaveLength(1)
    expect(wrapper.emitted('toggle-list')).toHaveLength(1)
    expect(wrapper.find('[data-action="fullscreen"]').attributes('aria-label')).toBe('退出全屏地图')
    expect(wrapper.find('[data-action="list"]').attributes('aria-pressed')).toBe('true')
  })
})

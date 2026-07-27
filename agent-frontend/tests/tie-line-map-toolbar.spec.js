import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import MapToolbar from '@/views/tie-line/components/MapToolbar.vue'
import mapToolbarSource from '@/views/tie-line/components/MapToolbar.vue?raw'

describe('联络线地图工具栏', () => {
  it('提供五个可访问的工具操作', () => {
    const wrapper = mount(MapToolbar)

    expect(wrapper.findAll('button')).toHaveLength(5)
    expect(wrapper.find('[data-action="zoom-in"]').attributes('aria-label')).toBe('放大地图')
    expect(wrapper.find('[data-action="list"]').attributes('aria-pressed')).toBe('false')
    expect(wrapper.find('svg.lucide-zoom-in').exists()).toBe(true)
    expect(wrapper.find('svg.lucide-list').exists()).toBe(true)
    expect(wrapper.find('.xc-btn--icon').exists()).toBe(true)
    expect(wrapper.find('svg.lucide-zoom-in').exists()).toBe(true)
    expect(wrapper.find('svg.lucide-list').exists()).toBe(true)
    expect(wrapper.find('.xc-btn--icon').exists()).toBe(true)
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
  })

  it('地图浅色区域上使用高对比深色图标和浅色工具底', () => {
    const styles = mapToolbarSource.match(/<style scoped>([\s\S]*)<\/style>/)?.[1] || ''

    expect(styles).toContain('gap: var(--xc-space-2)')
    expect(styles).toContain('background: rgba(245, 239, 220, 0.88)')
    expect(styles).toContain('color: var(--xc-map-ocean)')
    expect(styles).toContain('box-shadow: 0 8px 22px rgba(9, 24, 43, 0.22)')
    expect(styles).not.toContain('overflow: hidden')
    expect(styles).not.toContain('color: var(--xc-text-soft)')
    expect(styles).not.toContain('background: var(--xc-surface-glass)')
  })
})

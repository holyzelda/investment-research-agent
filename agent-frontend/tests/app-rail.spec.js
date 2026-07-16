import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AppRail from '@/layout/components/AppRail.vue'

describe('AppRail (outer module rail)', () => {
  it('renders 首页 plus the three not-yet-built modules in order', () => {
    const wrapper = mount(AppRail)

    const labels = wrapper.findAll('.ir-rail-btn').map((btn) => btn.attributes('aria-label'))
    expect(labels).toEqual(['首页', '全国指数地图', '联络线地图', '政策与市场'])
  })

  it('marks only the active item and leaves the rest clickable-disabled', () => {
    const wrapper = mount(AppRail, { props: { active: 'home' } })

    const buttons = wrapper.findAll('.ir-rail-btn')
    expect(buttons[0].classes()).toContain('is-active')
    expect(buttons[0].attributes('disabled')).toBeUndefined()
    for (const btn of buttons.slice(1)) {
      expect(btn.classes()).not.toContain('is-active')
      expect(btn.classes()).toContain('is-disabled')
      expect(btn.attributes('disabled')).toBeDefined()
    }
  })

  it('emits nav only for the enabled item, never for disabled placeholders', async () => {
    const wrapper = mount(AppRail)
    const buttons = wrapper.findAll('.ir-rail-btn')

    await buttons[0].trigger('click')
    expect(wrapper.emitted('nav')?.[0]).toEqual(['home'])

    await buttons[1].trigger('click')
    await buttons[2].trigger('click')
    await buttons[3].trigger('click')
    expect(wrapper.emitted('nav')).toHaveLength(1)
  })

  it('tags disabled items with a 待建 hint for the hover tooltip', () => {
    const wrapper = mount(AppRail)
    const buttons = wrapper.findAll('.ir-rail-btn')

    expect(buttons[0].attributes('data-tip')).toBe('首页')
    expect(buttons[1].attributes('data-tip')).toBe('全国指数地图（待建）')
  })
})

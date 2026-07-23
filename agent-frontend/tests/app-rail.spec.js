import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AppRail from '@/layout/components/AppRail.vue'

describe('AppRail (outer module rail)', () => {
  it('renders 首页 plus the three not-yet-built modules in order', () => {
    const wrapper = mount(AppRail)

    const labels = wrapper.findAll('.ir-rail-btn').map((btn) => btn.attributes('aria-label'))
    expect(labels).toEqual(['首页', '全国指数地图', '联络线地图', '政策与市场'])
  })

  it('marks the active item and keeps only the nationwide index module disabled', () => {
    const wrapper = mount(AppRail, { props: { active: 'home' } })

    const buttons = wrapper.findAll('.ir-rail-btn')
    expect(buttons[0].classes()).toContain('is-active')
    expect(buttons[0].attributes('disabled')).toBeUndefined()
    expect(buttons[1].classes()).toContain('is-disabled')
    expect(buttons[1].attributes('disabled')).toBeDefined()
    expect(buttons[2].classes()).not.toContain('is-active')
    expect(buttons[2].classes()).not.toContain('is-disabled')
    expect(buttons[2].attributes('disabled')).toBeUndefined()
    expect(buttons[3].classes()).not.toContain('is-disabled')
    expect(buttons[3].attributes('disabled')).toBeUndefined()
  })

  it('emits nav for enabled modules only', async () => {
    const wrapper = mount(AppRail)
    const buttons = wrapper.findAll('.ir-rail-btn')

    await buttons[0].trigger('click')
    await buttons[1].trigger('click')
    await buttons[2].trigger('click')
    await buttons[3].trigger('click')
    expect(wrapper.emitted('nav')).toEqual([['home'], ['line'], ['policy']])
  })

  it('tags disabled items with a 待建 hint for the hover tooltip', () => {
    const wrapper = mount(AppRail)
    const buttons = wrapper.findAll('.ir-rail-btn')

    expect(buttons[0].attributes('data-tip')).toBe('首页')
    expect(buttons[1].attributes('data-tip')).toBe('全国指数地图（待建）')
  })
})

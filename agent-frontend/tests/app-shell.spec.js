import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AppSidebar from '@/layout/components/AppSidebar.vue'

const navItems = [
  { key: 'home', path: '/home', label: '对话首页', icon: 'home' },
  { key: 'line', path: '/tie-line', label: '联络线地图', icon: 'line' },
]

describe('AppShell left sidebar', () => {
  it('orders the primary action, module navigation, history, and user identity', () => {
    const wrapper = mount(AppSidebar, {
      props: {
        items: navItems,
        active: 'line',
        history: [{ conversationId: 7, title: '甘肃储能测算' }],
        username: '研究员',
        userAvatar: '/avatar.png',
      },
    })

    const shell = wrapper.find('[data-testid="app-shell"]')
    const nav = shell.find('.ir-shell__nav')
    const history = shell.find('.ir-shell__history')
    expect(shell.find('.ir-shell__brand').exists()).toBe(true)
    expect(shell.find('.ir-shell__new').text()).toContain('新建会话')
    expect(shell.findAll('.ir-shell__nav-item')).toHaveLength(2)
    expect(shell.find('.ir-shell__nav-item.is-active').text()).toContain('联络线地图')
    expect(shell.find('.ir-shell__nav-item.is-active').attributes('aria-current')).toBe('page')
    expect(history.find('.ir-shell__history-title').text()).toBe('历史测算')
    expect(shell.find('.ir-shell__user').text()).toContain('研究员')
    expect(shell.find('.ir-shell__user-avatar').attributes('src')).toBe('/avatar.png')
    expect(nav.element.compareDocumentPosition(history.element) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('uses the existing four-module fallback when backend menu data is unavailable', () => {
    const wrapper = mount(AppSidebar)

    const labels = wrapper.findAll('.ir-shell__nav-item').map((button) => button.text())
    expect(labels).toEqual(['朱雀星核引擎', '朱雀寻龙图MAP', '联络线地图', '专业数据速查'])
  })

  it('normalizes approved menu names and right-side markers by route', () => {
    const wrapper = mount(AppSidebar, {
      props: {
        items: [
          { key: 'home', path: '/home', label: '首页', icon: 'home' },
          { key: 'index', path: '/index-map', label: '全国指数地图', icon: 'index' },
          { key: 'policy', path: '/policy-market', label: '政策与市场', icon: 'policy' },
        ],
      },
    })

    const items = wrapper.findAll('.ir-shell__nav-item')
    expect(items.map((item) => item.text())).toEqual(['朱雀星核引擎', '朱雀寻龙图MAP', '专业数据速查'])
    expect(wrapper.findAll('.ir-shell__nav-meta').map((item) => item.text())).toEqual(['引擎', 'MAP'])
    expect(items[2].find('.ir-shell__nav-meta').exists()).toBe(false)
  })

  it('emits a route target only for enabled module items', async () => {
    const wrapper = mount(AppSidebar, {
      props: {
        items: [
          ...navItems,
          { key: 'disabled', path: '/disabled', label: '未开放', icon: 'default', disabled: true },
        ],
      },
    })
    const buttons = wrapper.findAll('.ir-shell__nav-item')

    await buttons[1].trigger('click')
    await buttons[2].trigger('click')

    expect(wrapper.emitted('nav')).toEqual([['/tie-line']])
  })

  it('emits compact-state changes from the desktop toggle', async () => {
    const wrapper = mount(AppSidebar, {
      props: { collapsed: false },
    })

    await wrapper.find('.ir-shell__toggle').trigger('click')

    expect(wrapper.emitted('update:collapsed')).toEqual([[true]])
  })

  it('closes the mobile drawer from both its header control and scrim', async () => {
    const wrapper = mount(AppSidebar, {
      props: { collapsed: true, drawerOpen: true },
    })

    expect(wrapper.find('.ir-shell-wrap').classes()).toContain('is-drawer-open')
    expect(wrapper.find('.ir-shell__toggle').attributes('aria-label')).toBe('关闭菜单')
    await wrapper.find('.ir-shell__toggle').trigger('click')
    await wrapper.find('.ir-shell__drawer-scrim').trigger('click')

    expect(wrapper.emitted('close-drawer')).toEqual([[], []])
    expect(wrapper.emitted('update:collapsed')).toBeUndefined()
  })
})

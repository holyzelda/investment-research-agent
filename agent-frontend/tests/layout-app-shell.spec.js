import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const state = vi.hoisted(() => {
  const route = { name: 'Home', path: '/home', fullPath: '/home', meta: {} }
  return {
    route,
    router: {
      push: vi.fn().mockResolvedValue(undefined),
      currentRoute: { value: route },
    },
    session: { username: 'researcher', nickname: '研究员昵称', loadUserInfo: vi.fn() },
    calc: {
      messages: [],
      history: [{ conversationId: 7, title: '甘肃储能测算' }],
      conversationId: null,
      loadHistory: vi.fn().mockResolvedValue(undefined),
      resetConversation: vi.fn(),
      openConversation: vi.fn().mockResolvedValue(undefined),
      removeConversation: vi.fn().mockResolvedValue(undefined),
      renameConversation: vi.fn().mockResolvedValue(undefined),
    },
    permission: {
      railRoutes: [
        { path: '/home', title: '对话首页', icon: 'home' },
        { path: '/tie-line', title: '联络线地图', icon: 'line' },
      ],
    },
  }
})

vi.mock('vue-router', async () => {
  const { reactive } = await import('vue')
  state.route = reactive(state.route)
  return {
    useRoute: () => state.route,
    useRouter: () => state.router,
  }
})

vi.mock('@/store/modules/session', () => ({
  useSessionStore: () => state.session,
}))

vi.mock('@/store/modules/calculation', () => ({
  useCalculationStore: () => state.calc,
}))

vi.mock('@/store/modules/permission', () => ({
  usePermissionStore: () => state.permission,
}))

import Layout from '@/layout/index.vue'

const mountLayout = () => mount(Layout, { global: { stubs: { 'router-view': true } } })

describe('left AppShell layout', () => {
  beforeEach(() => {
    state.route.name = 'Home'
    state.route.path = '/home'
    state.route.fullPath = '/home'
    state.route.meta = {}
    state.calc.messages = []
    state.calc.conversationId = null
    vi.clearAllMocks()
  })

  it('renders one shell beside the content instead of a top bar and AppRail', () => {
    const wrapper = mountLayout()

    expect(wrapper.find('.ir-layout__topbar').exists()).toBe(false)
    expect(wrapper.find('.ir-rail').exists()).toBe(false)
    expect(wrapper.find('[data-testid="app-shell"]').exists()).toBe(true)
    expect(wrapper.find('.ir-layout__content').exists()).toBe(true)
    expect(wrapper.find('.ir-shell__user').text()).toContain('研究员昵称')
    expect(wrapper.find('.ir-shell__user').text()).not.toContain('researcher')
  })

  it('places welcome metrics inside the content column', () => {
    const wrapper = mountLayout()
    const metrics = wrapper.find('.ir-layout__welcome-metrics')

    expect(metrics.exists()).toBe(true)
    expect(metrics.element.closest('.ir-layout__content')).not.toBeNull()
    expect(wrapper.findAll('.ir-layout__welcome-metric')).toHaveLength(5)
  })

  it('returns to home after starting a new chat from another module', async () => {
    const wrapper = mountLayout()
    state.route.path = '/tie-line'
    state.route.fullPath = '/tie-line'

    await wrapper.find('.ir-shell__new').trigger('click')
    await flushPromises()

    expect(state.calc.resetConversation).toHaveBeenCalledTimes(1)
    expect(state.router.push).toHaveBeenCalledWith('/home')
  })

  it('returns to home after replaying a conversation from another module', async () => {
    const wrapper = mountLayout()
    state.route.path = '/tie-line'
    state.route.fullPath = '/tie-line'

    await wrapper.find('.ir-shell__history-item').trigger('click')
    await flushPromises()

    expect(state.calc.openConversation).toHaveBeenCalledWith(7)
    expect(state.router.push).toHaveBeenCalledWith('/home')
  })

  it('opens and closes the mobile drawer without removing the shell', async () => {
    const wrapper = mountLayout()

    await wrapper.find('.ir-layout__menu-trigger').trigger('click')
    expect(wrapper.find('.ir-shell-wrap').classes()).toContain('is-drawer-open')

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await flushPromises()
    expect(wrapper.find('.ir-shell-wrap').classes()).not.toContain('is-drawer-open')
  })

  it('keeps an explicitly expanded sidebar open when the route changes', async () => {
    state.route.name = 'IndexMap'
    state.route.path = '/index-map'
    state.route.fullPath = '/index-map'
    state.route.meta = { collapseSidebar: true }
    const wrapper = mountLayout()

    expect(wrapper.find('.ir-shell-wrap').classes()).toContain('is-collapsed')
    await wrapper.find('.ir-shell__toggle').trigger('click')
    expect(wrapper.find('.ir-shell-wrap').classes()).not.toContain('is-collapsed')

    state.route.name = 'TieLine'
    state.route.path = '/tie-line'
    state.route.fullPath = '/tie-line'
    state.route.meta = { collapseSidebar: true }
    await flushPromises()

    expect(wrapper.find('.ir-shell-wrap').classes()).not.toContain('is-collapsed')
    expect(wrapper.find('.ir-shell__toggle').attributes('aria-label')).toBe('折叠侧栏')
  })

  it('keeps report detail as a shell-free full-width view', () => {
    state.route.name = 'ReportDetail'
    state.route.path = '/reports/1'
    state.route.fullPath = '/reports/1'
    state.route.meta = { collapseSidebar: true }
    const wrapper = mountLayout()

    expect(wrapper.find('[data-testid="app-shell"]').exists()).toBe(false)
    expect(wrapper.find('.ir-layout__menu-trigger').exists()).toBe(false)
    expect(wrapper.find('.ir-layout__body').classes()).toContain('is-report-view')
  })
})

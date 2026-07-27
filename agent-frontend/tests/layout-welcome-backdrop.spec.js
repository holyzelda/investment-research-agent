import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

const layoutSource = readFileSync(resolve(process.cwd(), 'src/layout/index.vue'), 'utf8')
const welcomeBackdropStyles = layoutSource.slice(
  layoutSource.indexOf('.ir-layout__welcome-backdrop {'),
  layoutSource.indexOf('.ir-layout__topbar {'),
)

// 可变的路由与会话状态：每个用例重挂载前调整
const route = { name: 'Home', path: '/home', fullPath: '/home', meta: {} }
const calc = {
  messages: [],
  history: [],
  conversationId: null,
  loadHistory: vi.fn().mockResolvedValue(undefined),
  resetConversation: vi.fn(),
  openConversation: vi.fn().mockResolvedValue(undefined),
  removeConversation: vi.fn().mockResolvedValue(undefined),
}

vi.mock('@/store/modules/session', () => ({
  useSessionStore: () => ({ username: 'admin', loadUserInfo: vi.fn() }),
}))

vi.mock('@/store/modules/calculation', () => ({
  useCalculationStore: () => calc,
}))

vi.mock('@/store/modules/permission', () => ({
  usePermissionStore: () => ({ railRoutes: [] }),
}))

vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => ({ push: vi.fn(), currentRoute: { value: route } }),
}))

vi.mock('@/layout/components/AppRail.vue', () => ({
  default: { template: '<div class="app-rail-stub" />' },
}))

vi.mock('@/layout/components/AppSidebar.vue', () => ({
  default: { template: '<div class="app-sidebar-stub" />' },
}))

import Layout from '@/layout/index.vue'

const mountLayout = () =>
  mount(Layout, { global: { stubs: { 'router-view': true } } })

describe('layout 首页欢迎态全屏背景', () => {
  beforeEach(() => {
    route.name = 'Home'
    route.path = '/home'
    route.fullPath = '/home'
    route.meta = {}
    calc.messages = []
  })

  it('首页且无会话时铺满全屏背景层', () => {
    const wrapper = mountLayout()

    const backdrop = wrapper.find('.ir-layout__welcome-backdrop')
    expect(backdrop.exists()).toBe(true)
    expect(backdrop.attributes('aria-hidden')).toBe('true')
    // 通过 CSS 变量注入图片，供 background 合成使用
    expect(backdrop.attributes('style')).toContain('--ir-welcome-bg')
    expect(welcomeBackdropStyles).not.toContain('filter: blur(')
    expect(welcomeBackdropStyles).not.toContain('transform: scale(')
    expect(welcomeBackdropStyles).toContain('.ir-layout__welcome-backdrop::after')
    expect(welcomeBackdropStyles).toContain('linear-gradient(90deg, var(--xc-surface-workspace) 0%, transparent 72%)')
    expect(welcomeBackdropStyles).toContain('linear-gradient(0deg, var(--xc-surface-workspace) 0%, var(--xc-surface-workspace) 100%)')
    expect(welcomeBackdropStyles).toContain('var(--ir-welcome-bg) 150% center / cover no-repeat')
  })

  it('首页欢迎态在顶部栏展示五项平台指标', () => {
    const wrapper = mountLayout()

    expect(wrapper.find('.ir-layout__welcome-metrics').exists()).toBe(true)
    expect(wrapper.findAll('.ir-layout__welcome-metric')).toHaveLength(5)
    expect(wrapper.text()).toContain('累计测算次数')
    expect(wrapper.text()).toContain('覆盖省份')
  })

  it('存在会话时隐藏背景层和顶部指标', () => {
    calc.messages = [{ id: 'user-1', role: 'user', kind: 'text', text: '测试' }]
    const wrapper = mountLayout()

    expect(wrapper.find('.ir-layout__welcome-backdrop').exists()).toBe(false)
    expect(wrapper.find('.ir-layout__welcome-metrics').exists()).toBe(false)
  })

  it('非首页路由不显示背景层和顶部指标', () => {
    route.name = 'ReportDetail'
    route.path = '/reports/1'
    route.fullPath = '/reports/1'
    const wrapper = mountLayout()

    expect(wrapper.find('.ir-layout__welcome-backdrop').exists()).toBe(false)
    expect(wrapper.find('.ir-layout__welcome-metrics').exists()).toBe(false)
  })
})

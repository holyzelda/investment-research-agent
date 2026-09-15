import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

const layoutSource = readFileSync(resolve(process.cwd(), 'src/layout/index.vue'), 'utf8')
const welcomeBackdropStyles = layoutSource.slice(
  layoutSource.indexOf('.ir-layout__welcome-backdrop {'),
  layoutSource.indexOf('.ir-layout__body {'),
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
  useSessionStore: () => ({ username: 'admin', loadUserInfo: vi.fn().mockResolvedValue(undefined) }),
}))

vi.mock('@/store/modules/calculation', () => ({
  useCalculationStore: () => calc,
}))

vi.mock('@/store/modules/permission', () => ({
  usePermissionStore: () => ({ railRoutes: [] }),
}))

vi.mock('@/store/modules/trialQuota', () => ({
  useTrialQuotaStore: () => ({ isTrial: false, quota: null, load: vi.fn(), refresh: vi.fn() }),
}))

vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => ({ push: vi.fn(), currentRoute: { value: route } }),
}))

vi.mock('@/layout/components/AppSidebar.vue', () => ({
  default: { template: '<div class="app-sidebar-stub" />' },
}))

// 场景组件依赖 canvas / matchMedia，jsdom 下为空实现；布局测试只需验证其被挂载
vi.mock('@/views/home/components/WelcomeScene.vue', () => ({
  default: { template: '<div class="ir-welcome-scene-stub" />' },
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

  it('首页且无会话时挂载全屏图片背景层', () => {
    const wrapper = mountLayout()

    const backdrop = wrapper.find('.ir-layout__welcome-backdrop')
    expect(backdrop.exists()).toBe(true)
    expect(backdrop.attributes('aria-hidden')).toBe('true')
    expect(wrapper.find('.ir-layout__welcome-image').exists()).toBe(true)
    expect(layoutSource).toContain("@/assets/home-welcome-background.png")
    expect(layoutSource).toContain('--ir-welcome-bg')
    expect(welcomeBackdropStyles).not.toContain('filter: blur(')
    expect(welcomeBackdropStyles).not.toContain('transform: scale(')
    expect(welcomeBackdropStyles).toContain('.ir-layout__welcome-backdrop::after')
    expect(welcomeBackdropStyles).toContain('var(--xc-surface-workspace)')
  })

  it('场景图按高度等比缩放并锚定右下，且只绘制一层', () => {
    expect(welcomeBackdropStyles).toContain('right bottom / auto 95% no-repeat')
    // cover 会把图放大到铺满视口，正是首页显得过大的原因
    expect(welcomeBackdropStyles).not.toContain('cover')
    // 背景层自身不再重复绘制同一张图，图片只由 .ir-layout__welcome-image 承担
    expect(welcomeBackdropStyles.match(/var\(--ir-welcome-bg\)/g)).toHaveLength(1)
  })

  it('五项平台指标已迁移至首页欢迎组件，layout 不再渲染', () => {
    const wrapper = mountLayout()

    expect(wrapper.find('.ir-layout__welcome-metrics').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('累计测算次数')
  })

  it('存在会话时隐藏背景层', () => {
    calc.messages = [{ id: 'user-1', role: 'user', kind: 'text', text: '测试' }]
    const wrapper = mountLayout()

    expect(wrapper.find('.ir-layout__welcome-backdrop').exists()).toBe(false)
  })

  it('非首页路由不显示背景层', () => {
    route.name = 'ReportDetail'
    route.path = '/reports/1'
    route.fullPath = '/reports/1'
    const wrapper = mountLayout()

    expect(wrapper.find('.ir-layout__welcome-backdrop').exists()).toBe(false)
  })
})

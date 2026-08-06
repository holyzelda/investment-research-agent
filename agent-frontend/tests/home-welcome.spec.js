import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

const calc = {
  messages: [],
  versions: [],
  reports: [],
  selectedVersion: null,
  latestVersion: null,
  responding: false,
  paramDict: [],
  switches: {},
  stationOptions: [],
  sendAndCalculate: vi.fn(),
  recalculate: vi.fn(),
  generateReport: vi.fn(),
  selectVersion: vi.fn(),
}

vi.mock('@/store/modules/session', () => ({
  useSessionStore: () => ({ username: 'admin' }),
}))

vi.mock('@/store/modules/calculation', () => ({
  useCalculationStore: () => calc,
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/views/home/components/ChatComposer.vue', () => ({
  default: {
    template: `
      <button
        data-testid="welcome-send"
        @click="$emit('send', '测算甘肃 200MW/800MWh 独立储能项目')"
      />
    `,
  },
}))

vi.mock('@/views/home/components/ResultCard.vue', () => ({
  default: { template: '<div class="result-card-stub" />' },
}))

import Home from '@/views/home/index.vue'

describe('home welcome presentation', () => {
  it('does not render a home-local welcome background (carried by global layout)', () => {
    const wrapper = mount(Home, { global: { stubs: {} } })

    const welcome = wrapper.find('.ir-welcome')
    expect(welcome.exists()).toBe(true)
    // 背景由全局 layout 全屏承载，首页欢迎区不自带背景变量
    expect(welcome.attributes('style') || '').not.toContain('--ir-welcome-bg')
  })

  it('renders the five platform metrics below the input area', () => {
    const wrapper = mount(Home, { global: { stubs: {} } })

    expect(wrapper.find('.ir-welcome__metrics').exists()).toBe(true)
    expect(wrapper.findAll('.ir-welcome__metric')).toHaveLength(5)
    expect(wrapper.text()).toContain('累计测算次数')
    expect(wrapper.text()).toContain('覆盖省份')
  })

  it('example chips fill the composer instead of sending immediately', async () => {
    const wrapper = mount(Home, {
      global: { stubs: {} },
    })

    const chips = wrapper.findAll('.ir-chip')
    expect(chips.length).toBeGreaterThan(0)

    await chips[0].trigger('click')

    expect(calc.sendAndCalculate).not.toHaveBeenCalled()
  })

  it('sends a welcome example through the existing calculation flow', async () => {
    const wrapper = mount(Home, {
      global: { stubs: {} },
    })

    await wrapper.get('[data-testid="welcome-send"]').trigger('click')

    expect(calc.sendAndCalculate).toHaveBeenCalledWith(
      '测算甘肃 200MW/800MWh 独立储能项目',
    )
  })
})

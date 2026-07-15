import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { useCalculationStore } from '@/store/modules/calculation'
import HomeView from '@/views/home/index.vue'

vi.mock('@/api/calc', () => ({
  createCalculationTask: vi.fn(), getCalculationTask: vi.fn(), getCalculationResult: vi.fn(),
}))
vi.mock('@/api/session', () => ({ getUserInfo: vi.fn() }))
vi.mock('@/views/home/components/ChatComposer.vue', () => ({
  default: { template: '<div class="composer-stub" />' },
}))
vi.mock('@/views/home/components/ResultCard.vue', () => ({
  default: { props: ['result', 'version'], template: '<div class="result-stub">{{ version }}-{{ result.basicInfo.province }}</div>' },
}))

describe('calculation version list', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('keeps message order fixed while selection border follows the clicked version', async () => {
    const store = useCalculationStore()
    store.messages = [
      { id: 'u1', role: 'user', kind: 'text', text: '第一次测算' },
      { id: 'r1', role: 'assistant', kind: 'result', version: 'V1', result: { basicInfo: { province: '甘肃' } } },
      { id: 'u2', role: 'user', kind: 'text', text: '第二次测算' },
      { id: 'r2', role: 'assistant', kind: 'result', version: 'V2', result: { basicInfo: { province: '宁夏' } } },
    ]
    store.versions = [
      { version: 'V1', result: { basicInfo: { province: '甘肃' }, financial: { capitalIrr: 8 } } },
      { version: 'V2', result: { basicInfo: { province: '宁夏' }, financial: { capitalIrr: 9 } } },
    ]
    store.selectedVersion = 'V2'
    const wrapper = mount(HomeView, {
      global: { stubs: { ChatComposer: true } },
    })

    const items = wrapper.findAll('.ir-ver__item')
    expect(items.map((item) => item.find('.ir-ver__tag').text())).toEqual(['V2', 'V1'])
    expect(items[0].text()).toContain('最新')
    expect(items[0].classes()).not.toContain('ir-ver__item--latest')
    expect(items[0].classes()).toContain('ir-ver__item--selected')
    expect(items[1].classes()).not.toContain('ir-ver__item--selected')
    expect(wrapper.findAll('.ir-msg').map((message) => message.text())).toEqual([
      '第一次测算', 'V1-甘肃', '第二次测算', 'V2-宁夏',
    ])

    await items[1].trigger('click')

    expect(store.selectedVersion).toBe('V1')
    expect(items[0].classes()).not.toContain('ir-ver__item--selected')
    expect(items[1].classes()).toContain('ir-ver__item--selected')
    expect(items[0].text()).toContain('最新')
    expect(wrapper.findAll('.ir-msg').map((message) => message.text())).toEqual([
      '第一次测算', 'V1-甘肃', '第二次测算', 'V2-宁夏',
    ])
    expect(wrapper.find('.ir-msg--selected-result .result-stub').text()).toBe('V1-甘肃')
  })
})

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
    Element.prototype.scrollIntoView = vi.fn()
  })

  it('keeps message order fixed while the selected version owns the expanded archive details', async () => {
    const store = useCalculationStore()
    store.messages = [
      { id: 'u1', role: 'user', kind: 'text', text: '第一次测算' },
      { id: 'r1', role: 'assistant', kind: 'result', taskId: 11, version: 'V1', result: { basicInfo: { province: '甘肃' } } },
      { id: 'u2', role: 'user', kind: 'text', text: '第二次测算' },
      { id: 'r2', role: 'assistant', kind: 'result', taskId: 12, version: 'V2', result: { basicInfo: { province: '宁夏' } } },
    ]
    store.versions = [
      {
        taskId: 11, version: 'V1', calculatedAt: '2026-07-27T10:00:00',
        result: { basicInfo: { province: '甘肃' }, financial: { projectIrr: 8.1 } },
      },
      {
        taskId: 12, version: 'V2', calculatedAt: '2026-07-28T10:00:00',
        result: { basicInfo: { province: '宁夏' }, financial: { projectIrr: 9.2 } },
      },
    ]
    store.selectedVersion = 'V2'
    const wrapper = mount(HomeView, {
      global: { stubs: { ChatComposer: true } },
    })

    const items = wrapper.findAll('.ir-ver__item')
    expect(items.map((item) => item.find('.ir-ver__tag').text())).toEqual(['V2', 'V1'])
    expect(items[0].text()).toContain('最新')
    expect(items[0].classes()).toContain('ir-ver__item--selected')
    expect(items[0].text()).toContain('项目全投资 IRR')
    expect(items[0].text()).toContain('9.20%')
    expect(items[1].classes()).not.toContain('ir-ver__item--selected')
    expect(items[1].text()).toContain('查看结果')
    expect(items[1].text()).not.toContain('项目全投资 IRR')
    expect(items[1].get('.ir-ver__select').element.tagName).toBe('BUTTON')
    expect(wrapper.findAll('.ir-msg').map((message) => message.text())).toEqual([
      '第一次测算', 'V1-甘肃', '第二次测算', 'V2-宁夏',
    ])

    const stream = wrapper.find('.ir-home__stream').element
    const v1Message = wrapper.findAll('.ir-msg')[1].element
    Object.defineProperties(stream, {
      clientHeight: { configurable: true, value: 400 },
      scrollHeight: { configurable: true, value: 1200 },
      scrollTop: { configurable: true, writable: true, value: 200 },
    })
    stream.getBoundingClientRect = () => ({ top: 100, bottom: 500 })
    v1Message.getBoundingClientRect = () => ({ top: 650, bottom: 850 })

    await items[1].get('.ir-ver__select').trigger('click')

    expect(store.selectedVersion).toBe('V1')
    expect(items[0].classes()).not.toContain('ir-ver__item--selected')
    expect(items[0].text()).toContain('最新')
    expect(items[0].text()).toContain('查看结果')
    expect(items[1].classes()).toContain('ir-ver__item--selected')
    expect(items[1].text()).toContain('项目全投资 IRR')
    expect(items[1].text()).not.toContain('查看结果')
    expect(wrapper.findAll('.ir-msg').map((message) => message.text())).toEqual([
      '第一次测算', 'V1-甘肃', '第二次测算', 'V2-宁夏',
    ])
    expect(wrapper.find('.ir-msg--selected-result .result-stub').text()).toBe('V1-甘肃')
    expect(stream.scrollTop).toBe(750)
    wrapper.unmount()
  })

  it('scrolls the live conversation stream to an assistant-stream result', async () => {
    const store = useCalculationStore()
    store.messages = [
      { id: 'u1', role: 'user', kind: 'text', text: '第一次测算' },
      {
        id: 'stream-v1', role: 'assistant', kind: 'assistant-stream', phase: 'completed',
        taskId: 11, version: 'V1', result: { basicInfo: { province: '甘肃' } },
      },
      { id: 'u2', role: 'user', kind: 'text', text: '第二次测算' },
      {
        id: 'stream-v2', role: 'assistant', kind: 'assistant-stream', phase: 'completed',
        taskId: 12, version: 'V2', result: { basicInfo: { province: '宁夏' } },
      },
    ]
    store.versions = [
      { taskId: 11, version: 'V1', result: { basicInfo: { province: '甘肃' } } },
      { taskId: 12, version: 'V2', result: { basicInfo: { province: '宁夏' } } },
    ]
    store.selectedVersion = 'V2'
    const wrapper = mount(HomeView, {
      global: { stubs: { ChatComposer: true } },
    })
    const stream = wrapper.find('.ir-home__stream').element
    const v1Message = wrapper.findAll('.ir-msg')[1].element
    Object.defineProperties(stream, {
      clientHeight: { configurable: true, value: 400 },
      scrollHeight: { configurable: true, value: 1200 },
      scrollTop: { configurable: true, writable: true, value: 200 },
    })
    stream.getBoundingClientRect = () => ({ top: 100, bottom: 500 })
    v1Message.getBoundingClientRect = () => ({ top: 650, bottom: 850 })

    await wrapper.findAll('.ir-ver__item')[1].get('.ir-ver__select').trigger('click')

    expect(store.selectedVersion).toBe('V1')
    expect(stream.scrollTop).toBe(750)
    wrapper.unmount()
  })
})

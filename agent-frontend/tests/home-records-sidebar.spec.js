import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

const calc = {
  messages: [{ id: 'm-1', role: 'user', kind: 'text', text: '测算' }],
  selectedVersion: 'V2',
  latestVersion: { version: 'V2' },
  versions: [
    {
      version: 'V1', taskId: 1, calculatedAt: '2026-07-27T14:10:56',
      result: { financial: { projectIrr: 8.1 }, basicInfo: { province: '甘肃', powerMw: 100, capacityMwh: 200 } },
    },
    {
      version: 'V2', taskId: 2, calculatedAt: null,
      report: { reportId: 'new', status: 'completed' },
      result: { financial: { projectIrr: 8.2 }, basicInfo: { province: '甘肃', powerMw: 100, capacityMwh: 200 } },
    },
  ],
  reports: [
    { reportId: 'old', status: 'completed', version: 'V1', title: '旧报告', createdAt: '2026-07-26T14:10:56' },
    { reportId: 'new', status: 'completed', version: 'V2', title: '新报告', createdAt: '2026-07-27T14:10:56' },
    { reportId: 'unknown', status: 'completed', version: 'V1', title: '无时间报告', createdAt: null },
  ],
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
  default: { template: '<div />' },
}))
vi.mock('@/views/home/components/ResultCard.vue', () => ({
  default: { template: '<div />' },
}))

import Home from '@/views/home/index.vue'

describe('home records sidebar', () => {
  it('shows second-level times and sorts completed reports newest first', () => {
    const wrapper = mount(Home)

    expect(wrapper.text()).toContain('测算时间：2026-07-27 14:10:56')
    expect(wrapper.text()).toContain('测算时间：—')
    expect(wrapper.text()).toContain('2026-07-27 14:10:56')
    expect(wrapper.text()).not.toContain('2026-07-27T14:10:56')
    const titles = wrapper.findAll('.ir-report-list__item strong').map((node) => node.text())
    expect(titles).toEqual(['新报告', '旧报告', '无时间报告'])
    const versionText = wrapper.findAll('.ir-ver__item')[0].text()
    expect(versionText.indexOf('项目全投资IRR')).toBeLessThan(versionText.indexOf('测算时间：—'))
    expect(wrapper.findAll('.ir-ver__item')[0].get('.ir-report-list__view').text()).toBe('跳转报告记录')
  })

  it('keeps section titles outside their scrollable record lists', () => {
    const wrapper = mount(Home)

    expect(wrapper.findAll('.ir-home__side-scroll')).toHaveLength(2)
    expect(wrapper.findAll('.ir-home__side-section > .ir-home__side-title')).toHaveLength(2)
    expect(wrapper.find('.ir-report-list__view').exists()).toBe(true)
    expect(wrapper.findAll('.ir-report-list__view--full')).toHaveLength(5)
  })

  it('scrolls and highlights the matching report card from a completed calculation', async () => {
    const scrollIntoView = vi.fn()
    Element.prototype.scrollIntoView = scrollIntoView
    const wrapper = mount(Home)

    await wrapper.findAll('.ir-ver__item')[0].get('.ir-report-list__view').trigger('click')

    const target = wrapper.get('[data-report-id="new"]')
    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'nearest' })
    expect(target.classes()).toContain('ir-report-list__item--highlighted')
  })
})

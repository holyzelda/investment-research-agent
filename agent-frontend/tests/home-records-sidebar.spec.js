import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

const router = vi.hoisted(() => ({
  resolve: vi.fn(({ params }) => ({ href: `/reports/${params.reportId}` })),
}))
const message = vi.hoisted(() => ({ warning: vi.fn() }))
const calc = {
  messages: [{ id: 'm-1', role: 'user', kind: 'text', text: '测算' }],
  selectedVersion: 'V2',
  latestVersion: { version: 'V2' },
  versions: [],
  reports: [],
  responding: false,
  paramDict: [],
  switches: {},
  stationOptions: [],
  disposeActiveTurn: vi.fn(),
  disposeReportStreams: vi.fn(),
  sendAndCalculate: vi.fn(),
  recalculate: vi.fn(),
  generateReport: vi.fn(),
  selectVersion: vi.fn(),
}

function resetRecords() {
  calc.selectedVersion = 'V2'
  calc.latestVersion = { version: 'V2' }
  calc.versions = [
    {
      version: 'V1', taskId: 1, calculatedAt: '2026-07-27T14:10:56',
      result: { financial: { projectIrr: 8.1 }, basicInfo: { province: '甘肃', powerMw: 100, capacityMwh: 200 } },
    },
    {
      version: 'V2', taskId: 2, calculatedAt: null,
      report: { reportId: 'new', status: 'completed' },
      result: { financial: { projectIrr: 8.2 }, basicInfo: { province: '甘肃', powerMw: 100, capacityMwh: 200 } },
    },
  ]
  calc.reports = [
    { reportId: 'old', status: 'completed', version: 'V1', title: '旧报告', createdAt: '2026-07-26T14:10:56' },
    { reportId: 'new', status: 'completed', version: 'V2', title: '新报告', createdAt: '2026-07-27T14:10:56' },
    { reportId: 'unknown', status: 'completed', version: 'V1', title: '无时间报告', createdAt: null },
    { reportId: 'pending', status: 'generating', version: 'V2', title: '生成中报告', createdAt: '2026-07-28T14:10:56' },
  ]
}

vi.mock('element-plus', () => ({ ElMessage: message }))
vi.mock('@/store/modules/session', () => ({
  useSessionStore: () => ({ username: 'admin' }),
}))
vi.mock('@/store/modules/calculation', () => ({
  useCalculationStore: () => calc,
}))
vi.mock('vue-router', () => ({
  useRouter: () => router,
}))
vi.mock('@/views/home/components/ChatComposer.vue', () => ({
  default: { template: '<div />' },
}))
vi.mock('@/views/home/components/ResultCard.vue', () => ({
  default: { template: '<div />' },
}))

import Home from '@/views/home/index.vue'

describe('home records sidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    resetRecords()
    Element.prototype.scrollIntoView = vi.fn()
    vi.stubGlobal('open', vi.fn(() => ({})))
  })

  it('renders one project archive with counts, selected details, and newest completed reports first', () => {
    const wrapper = mount(Home)

    expect(wrapper.findAll('.ir-home__ledger')).toHaveLength(1)
    expect(wrapper.get('.ir-home__ledger-header').text()).toContain('项目档案')
    expect(wrapper.get('.ir-home__ledger-count').text()).toBe('2 次测算 · 3 份报告')
    expect(wrapper.findAll('.ir-home__side-scroll')).toHaveLength(2)
    expect(wrapper.findAll('.ir-home__side-section > .ir-home__side-title')).toHaveLength(2)

    const items = wrapper.findAll('.ir-ver__item')
    expect(items[0].text()).toContain('项目全投资 IRR')
    expect(items[0].text()).toContain('8.20%')
    expect(items[0].text()).toContain('测算时间 —')
    expect(items[0].get('.ir-ver__report-action').text()).toContain('跳转报告记录')
    expect(items[1].text()).toContain('查看结果')
    expect(items[1].text()).not.toContain('项目全投资 IRR')

    expect(wrapper.text()).toContain('2026-07-27 14:10:56')
    expect(wrapper.text()).not.toContain('2026-07-27T14:10:56')
    const titles = wrapper.findAll('.ir-report-list__item strong').map((node) => node.text())
    expect(titles).toEqual(['新报告', '旧报告', '无时间报告'])
    expect(wrapper.find('[data-report-id="pending"]').exists()).toBe(false)
  })

  it('scrolls and highlights the matching report row from a completed calculation', async () => {
    const wrapper = mount(Home)

    await wrapper.get('.ir-ver__report-action').trigger('click')

    const target = wrapper.get('[data-report-id="new"]')
    expect(Element.prototype.scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'nearest' })
    expect(target.classes()).toContain('ir-report-list__item--highlighted')
  })

  it('opens a report from its document row in a new tab', async () => {
    const wrapper = mount(Home)

    await wrapper.get('[data-report-id="new"] .ir-report-list__view').trigger('click')

    expect(router.resolve).toHaveBeenCalledWith({ name: 'ReportDetail', params: { reportId: 'new' } })
    expect(window.open).toHaveBeenCalledWith('/reports/new', '_blank')
  })

  it('warns when the browser blocks the report tab', async () => {
    vi.mocked(window.open).mockReturnValueOnce(null)
    const wrapper = mount(Home)

    await wrapper.get('[data-report-id="new"] .ir-report-list__view').trigger('click')

    expect(message.warning).toHaveBeenCalledWith('浏览器阻止了新标签页，请允许弹窗后重试')
  })

  it('preserves generating and failed report actions on the selected version', async () => {
    calc.versions[1].report = { status: 'generating' }
    let wrapper = mount(Home)

    const generating = wrapper.get('.ir-ver__report-action')
    expect(generating.text()).toBe('报告生成中')
    expect(generating.attributes('disabled')).toBeDefined()
    wrapper.unmount()

    calc.versions[1].report = { status: 'failed' }
    wrapper = mount(Home)
    const retry = wrapper.get('.ir-ver__report-action')
    expect(retry.text()).toContain('重新生成报告')
    await retry.trigger('click')
    expect(calc.generateReport).toHaveBeenCalledWith(2)
  })
})

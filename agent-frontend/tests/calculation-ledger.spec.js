import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CalculationLedger from '@/views/calculation-ledger/index.vue'

const push = vi.fn()
const resolve = vi.fn(() => ({ href: '/investment/reports/report-1' }))

vi.mock('@/api/ledger', () => ({
  getLedgerProvinces: vi.fn(() => Promise.resolve({ data: { items: ['甘肃', '宁夏'] } })),
  getLedgerRecords: vi.fn(() => Promise.resolve({
    data: {
      total: 1,
      page: 1,
      pageSize: 10,
      items: [{
        taskId: 42,
        conversationId: 'conversation-1',
        title: '甘肃 储能测算',
        version: 'V2',
        calculatedAt: '2026-08-12T10:30:00',
        province: '甘肃',
        nodeName: null,
        powerMw: 200,
        capacityMwh: 800,
        projectIrr: 8.5,
        projectStaticPayback: 9.2,
        report: { status: 'completed', reportId: 'report-1' },
      }],
    },
  })),
}))

vi.mock('vue-router', () => ({ useRouter: () => ({ push, resolve }) }))

afterEach(() => {
  push.mockReset()
  resolve.mockClear()
  vi.restoreAllMocks()
})

describe('CalculationLedger', () => {
  it('loads the default ledger and routes result/report actions to their exact targets', async () => {
    const open = vi.spyOn(window, 'open').mockImplementation(() => null)
    const wrapper = mount(CalculationLedger)
    await flushPromises()

    expect(wrapper.text()).toContain('测算台账')
    expect(wrapper.text()).toContain('甘肃 储能测算')
    expect(wrapper.text()).toContain('省级测算')
    expect(wrapper.text()).toContain('已生成')

    const actionButtons = wrapper.findAll('.ledger-icon-button')
    await actionButtons[0].trigger('click')
    expect(push).toHaveBeenLastCalledWith({
      path: '/home', query: { conversationId: 'conversation-1', taskId: 42 },
    })

    await actionButtons[1].trigger('click')
    expect(open).toHaveBeenLastCalledWith('/investment/reports/report-1', '_blank', 'noopener,noreferrer')
  })

  it('renders the province picker and themed calendar instead of native controls', async () => {
    const wrapper = mount(CalculationLedger)
    await flushPromises()

    expect(wrapper.find('.ledger-province-trigger').exists()).toBe(true)
    expect(wrapper.find('select[multiple]').exists()).toBe(false)
    expect(wrapper.find('input[type="date"]').exists()).toBe(false)

    await wrapper.find('.ledger-date-trigger').trigger('click')
    expect(wrapper.find('.ledger-calendar').exists()).toBe(true)
    expect(wrapper.find('.ledger-calendar__days').exists()).toBe(true)
  })

})

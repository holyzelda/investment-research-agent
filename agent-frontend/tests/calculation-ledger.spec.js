import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CalculationLedger from '@/views/calculation-ledger/index.vue'

const push = vi.fn()
const resolve = vi.fn((location) => {
  if (location?.name === 'ReportDetail') return { href: '/investment/reports/report-1' }
  if (location?.name === 'CalculationResultReadonly') {
    return { href: `/investment/calculation-results/${location.params.conversationId}/${location.params.taskId}` }
  }
  return { href: '/investment/home?conversationId=conversation-1&taskId=42' }
})

const api = vi.hoisted(() => ({
  getLedgerBootstrap: vi.fn(),
  getLedgerUsers: vi.fn(),
  getLedgerProvinces: vi.fn(),
  getLedgerRecords: vi.fn(),
}))
const message = vi.hoisted(() => ({ error: vi.fn() }))

vi.mock('@/api/ledger', () => api)
vi.mock('element-plus', () => ({ ElMessage: message }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push, resolve }) }))
vi.mock('@/utils/auth', () => ({ getUserIdentity: () => ({ userId: '119', username: 'bjjzA' }) }))

const OWN_RECORD = {
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
}

function records(items) {
  return Promise.resolve({ data: { total: items.length, page: 1, pageSize: 10, items } })
}

function bootstrap(items, { isAdmin = false, users = [] } = {}) {
  return Promise.resolve({
    data: {
      users: { isAdmin, users },
      provinces: { items: ['甘肃', '宁夏'] },
      records: { total: items.length, page: 1, pageSize: 10, items },
    },
  })
}

beforeEach(() => {
  api.getLedgerBootstrap.mockImplementation(() => bootstrap([OWN_RECORD], {
    users: [{ userId: '119', nickName: '北京金租管理员' }],
  }))
  api.getLedgerRecords.mockImplementation(() => records([OWN_RECORD]))
})

afterEach(() => {
  push.mockReset()
  resolve.mockClear()
  vi.clearAllMocks()
})

describe('CalculationLedger', () => {
  it('loads the default ledger and renders result/report actions as exact new-tab links', async () => {
    const wrapper = mount(CalculationLedger)
    await flushPromises()

    expect(wrapper.text()).toContain('测算台账')
    expect(wrapper.text()).toContain('查询已完成测算')
    expect(wrapper.text()).toContain('甘肃 储能测算')
    expect(wrapper.text()).toContain('省级测算')
    expect(wrapper.text()).toContain('已生成')

    const actionLinks = wrapper.findAll('.ledger-icon-button')
    expect(actionLinks[0].attributes()).toMatchObject({
      href: '/investment/home?conversationId=conversation-1&taskId=42',
      target: '_blank',
      rel: 'noopener noreferrer',
    })
    expect(resolve).toHaveBeenCalledWith({
      path: '/home', query: { conversationId: 'conversation-1', taskId: 42 },
    })

    expect(actionLinks[1].attributes()).toMatchObject({
      href: '/investment/reports/report-1',
      target: '_blank',
      rel: 'noopener noreferrer',
    })
    expect(resolve).toHaveBeenCalledWith({ name: 'ReportDetail', params: { reportId: 'report-1' } })
    expect(push).not.toHaveBeenCalled()
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

  it('hides the initiator filter and column for an ordinary user', async () => {
    const wrapper = mount(CalculationLedger)
    await flushPromises()

    expect(wrapper.find('.ledger-field--initiator').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('发起人')
    expect(api.getLedgerBootstrap.mock.calls[0][0]).not.toHaveProperty('initiator_user_ids')
    expect(api.getLedgerUsers).not.toHaveBeenCalled()
    expect(api.getLedgerProvinces).not.toHaveBeenCalled()
    expect(api.getLedgerRecords).not.toHaveBeenCalled()
  })
})

describe('CalculationLedger · administrator', () => {
  beforeEach(() => {
    const users = [
      { userId: '119', nickName: '北京金租管理员' },
      { userId: '120', nickName: '北京金租普通账号' },
    ]
    const items = [
      { ...OWN_RECORD, initiator: { userId: '119', nickName: '北京金租管理员' } },
      {
        ...OWN_RECORD,
        taskId: 77,
        conversationId: 'conversation-2',
        title: '宁夏 独立储能',
        report: { status: 'not_generated', reportId: null },
        initiator: { userId: '120', nickName: '北京金租普通账号' },
      },
    ]
    api.getLedgerBootstrap.mockImplementation(() => bootstrap(items, { isAdmin: true, users }))
    api.getLedgerRecords.mockImplementation(() => records(items))
  })

  it('loads users, provinces and records with one bootstrap request', async () => {
    const wrapper = mount(CalculationLedger)
    await flushPromises()

    expect(wrapper.find('.ledger-field--initiator').exists()).toBe(true)
    expect(wrapper.text()).toContain('发起人')
    expect(wrapper.text()).toContain('北京金租普通账号')
    expect(api.getLedgerBootstrap).toHaveBeenCalledTimes(1)
    expect(api.getLedgerUsers).not.toHaveBeenCalled()
    expect(api.getLedgerProvinces).not.toHaveBeenCalled()
    expect(api.getLedgerRecords).not.toHaveBeenCalled()
  })

  it('clears the initial state and reports a bootstrap failure', async () => {
    api.getLedgerBootstrap.mockRejectedValue(new Error('unavailable'))

    const wrapper = mount(CalculationLedger)
    await flushPromises()

    expect(wrapper.find('.ledger-field--initiator').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('甘肃 储能测算')
    expect(message.error).toHaveBeenCalledWith('测算台账加载失败，请稍后重试')
  })

  it('sends the selected initiators as one comma separated parameter', async () => {
    const wrapper = mount(CalculationLedger)
    await flushPromises()

    await wrapper.find('.ledger-field--initiator .ledger-province-trigger').trigger('click')
    const options = wrapper.findAll('.ledger-field--initiator .ledger-province-option input')
    await options[1].trigger('change')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    const params = api.getLedgerRecords.mock.calls.at(-1)[0]
    expect(params.initiator_user_ids).toBe('120')
  })

  it('omits the parameter once the initiator selection is cleared', async () => {
    const wrapper = mount(CalculationLedger)
    await flushPromises()

    await wrapper.find('.ledger-field--initiator .ledger-province-trigger').trigger('click')
    const options = wrapper.findAll('.ledger-field--initiator .ledger-province-option input')
    await options[1].trigger('change')
    await wrapper.find('.ledger-field--initiator .ledger-province-menu__tools button').trigger('click')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(api.getLedgerRecords.mock.calls.at(-1)[0]).not.toHaveProperty('initiator_user_ids')
  })

  it('routes other people records to the read-only page and keeps own records on home', async () => {
    const wrapper = mount(CalculationLedger)
    await flushPromises()

    const rows = wrapper.findAll('tbody tr')
    const ownResult = rows[0].find('.ledger-icon-button')
    const otherResult = rows[1].find('.ledger-icon-button')

    expect(ownResult.attributes('href')).toBe('/investment/home?conversationId=conversation-1&taskId=42')
    expect(otherResult.attributes('href')).toBe('/investment/calculation-results/conversation-2/77')
    expect(otherResult.attributes()).toMatchObject({ target: '_blank', rel: 'noopener noreferrer' })
    expect(resolve).toHaveBeenCalledWith({
      name: 'CalculationResultReadonly',
      params: { conversationId: 'conversation-2', taskId: 77 },
    })
  })
})

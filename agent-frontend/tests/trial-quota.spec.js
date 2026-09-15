import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import TrialQuotaBadge from '@/components/TrialQuotaBadge.vue'
import TrialQuotaNotice from '@/components/TrialQuotaNotice.vue'

const api = vi.hoisted(() => ({ getTrialQuota: vi.fn() }))
vi.mock('@/api/trialQuota', () => api)

import { useTrialQuotaStore } from '@/store/modules/trialQuota'

const TRIAL_QUOTA = {
  isTrial: true,
  usageDate: '2026-09-15',
  calculation: { used: 2, limit: 5, remaining: 3 },
  report: { used: 1, limit: 5, remaining: 4 },
  consultation: { used: 3, limit: 5, remaining: 2 },
}

const EXHAUSTED_QUOTA = {
  isTrial: true,
  usageDate: '2026-09-15',
  calculation: { used: 5, limit: 5, remaining: 0 },
  report: { used: 5, limit: 5, remaining: 0 },
  consultation: { used: 5, limit: 5, remaining: 0 },
}

describe('trial quota store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads the backend payload and derives isTrial from it', async () => {
    api.getTrialQuota.mockResolvedValue(TRIAL_QUOTA)
    const store = useTrialQuotaStore()

    await store.load()

    expect(api.getTrialQuota).toHaveBeenCalledTimes(1)
    expect(store.quota).toEqual(TRIAL_QUOTA)
    expect(store.isTrial).toBe(true)
    expect(store.loading).toBe(false)
  })

  it('treats a normal-account payload as non-trial', async () => {
    api.getTrialQuota.mockResolvedValue({ isTrial: false })
    const store = useTrialQuotaStore()

    await store.load()

    expect(store.isTrial).toBe(false)
    expect(store.quota.calculation).toBeUndefined()
  })

  it('a refreshed response replaces all three counters', async () => {
    api.getTrialQuota.mockResolvedValueOnce(TRIAL_QUOTA)
    const store = useTrialQuotaStore()
    await store.load()

    const refreshed = {
      ...TRIAL_QUOTA,
      calculation: { used: 5, limit: 5, remaining: 0 },
      report: { used: 5, limit: 5, remaining: 0 },
      consultation: { used: 5, limit: 5, remaining: 0 },
    }
    api.getTrialQuota.mockResolvedValue(refreshed)

    await store.refresh()

    expect(store.quota).toEqual(refreshed)
    expect(store.quota.calculation.remaining).toBe(0)
  })

  it('refresh swallows fetch errors and reset clears state', async () => {
    api.getTrialQuota.mockRejectedValue(new Error('network'))
    const store = useTrialQuotaStore()

    await expect(store.refresh()).resolves.toBeNull()
    expect(store.error).toBeTruthy()

    store.reset()
    expect(store.quota).toBeNull()
    expect(store.error).toBe('')
    expect(store.loading).toBe(false)
  })
})

describe('TrialQuotaBadge component', () => {
  it('renders the compact sidebar card with remaining counters for a trial account', () => {
    const wrapper = mount(TrialQuotaBadge, { props: { quota: TRIAL_QUOTA } })

    expect(wrapper.find('.ir-trial-badge').exists()).toBe(true)
    expect(wrapper.text()).toContain('试用版')
    expect(wrapper.text()).toContain('每日重置')
    expect(wrapper.text()).toContain('测算')
    expect(wrapper.text()).toContain('报告')
    expect(wrapper.text()).toContain('咨询')
    expect(wrapper.find('.ir-trial-badge__fill').attributes('style')).toContain('width: 40%')
  })

  it('switches to the exhausted message when all counters are zero', () => {
    const wrapper = mount(TrialQuotaBadge, { props: { quota: EXHAUSTED_QUOTA } })

    expect(wrapper.find('.ir-trial-badge').classes()).toContain('is-exhausted')
    expect(wrapper.text()).toContain('今日已用完')
    expect(wrapper.text()).toContain('今日额度已用完，明日恢复')
  })

  it('stays hidden for normal accounts', () => {
    const wrapper = mount(TrialQuotaBadge, { props: { quota: { isTrial: false } } })

    expect(wrapper.find('.ir-trial-badge').exists()).toBe(false)
  })

  it('fills missing counters with zero when any counter remains', () => {
    const wrapper = mount(TrialQuotaBadge, {
      props: { quota: { isTrial: true, calculation: { remaining: 1 } } },
    })

    expect(wrapper.text()).toContain('测算')
    expect(wrapper.text()).not.toContain('今日额度已用完')
  })

  it('collapses into a compact status pill with a tooltip summary', () => {
    const wrapper = mount(TrialQuotaBadge, { props: { quota: TRIAL_QUOTA, collapsed: true } })

    expect(wrapper.find('.ir-trial-badge--compact').exists()).toBe(true)
    expect(wrapper.find('.ir-trial-badge__stats').exists()).toBe(false)
    expect(wrapper.find('.ir-trial-badge__mini-fill').exists()).toBe(true)
    expect(wrapper.find('.ir-trial-badge__mini-fill').attributes('style')).toContain('width: 40%')
    expect(wrapper.attributes('data-tip')).toContain('试用版')
    expect(wrapper.attributes('data-tip')).toContain('测算3/5')
    expect(wrapper.attributes('data-tip')).toContain('报告4/5')
    expect(wrapper.attributes('data-tip')).toContain('咨询2/5')
  })

  it('collapsed tooltip shows exhausted copy when the quota is used up', () => {
    const wrapper = mount(TrialQuotaBadge, { props: { quota: EXHAUSTED_QUOTA, collapsed: true } })

    expect(wrapper.find('.ir-trial-badge--compact.is-exhausted').exists()).toBe(true)
    expect(wrapper.find('.ir-trial-badge__mini-fill').attributes('style')).toContain('width: 100%')
    expect(wrapper.attributes('data-tip')).toBe('试用版 · 今日额度已用完')
  })
})

describe('TrialQuotaNotice component', () => {
  it('shows the quiet inline quota line for a trial account', () => {
    const wrapper = mount(TrialQuotaNotice, { props: { quota: TRIAL_QUOTA, feature: 'calculation' } })

    expect(wrapper.find('.ir-trial-notice').exists()).toBe(true)
    expect(wrapper.find('.ir-trial-notice.is-alert').exists()).toBe(false)
    expect(wrapper.text()).toContain('今日试用额度')
    expect(wrapper.text()).toContain('每日重置')
    expect(wrapper.text()).toContain('3/5')
  })

  it('turns into an alert only when the targeted feature is exhausted', () => {
    const wrapper = mount(TrialQuotaNotice, {
      props: { quota: { isTrial: true, calculation: { used: 5, remaining: 0 }, report: { used: 0, remaining: 5 }, consultation: { used: 0, remaining: 5 } }, feature: 'calculation' },
    })

    expect(wrapper.find('.ir-trial-notice').classes()).toContain('is-alert')
    expect(wrapper.text()).toContain('今日测算额度已用完，明日 00:00 自动恢复')
  })

  it('maps report and consultation feature labels in the alert copy', () => {
    const report = mount(TrialQuotaNotice, { props: { quota: EXHAUSTED_QUOTA, feature: 'report' } })
    expect(report.text()).toContain('今日报告生成额度已用完')

    const consultation = mount(TrialQuotaNotice, { props: { quota: EXHAUSTED_QUOTA, feature: 'consultation' } })
    expect(consultation.text()).toContain('今日政策咨询额度已用完')
  })

  it('stays hidden for normal accounts', () => {
    const wrapper = mount(TrialQuotaNotice, { props: { quota: { isTrial: false } } })

    expect(wrapper.find('.ir-trial-notice').exists()).toBe(false)
  })
})
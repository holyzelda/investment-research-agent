import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import * as api from '@/api/policyMarket'
import { usePolicyMarketStore } from '@/store/modules/policyMarket'

vi.mock('@/api/policyMarket', () => ({
  getConsultations: vi.fn(),
  submitConsultation: vi.fn(),
  getMarketNews: vi.fn(),
  getConsultationStats: vi.fn(),
}))

describe('政策与市场 Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  it('初始化时加载咨询、资讯和默认统计', async () => {
    api.getConsultations.mockResolvedValue([{ id: 'c-1', title: '问题', status: 'completed' }])
    api.getMarketNews.mockResolvedValue([{ id: 'n-1', title: '资讯' }])
    api.getConsultationStats.mockResolvedValue({ total: 10, trend: 12.6, rangeLabel: '全部省份' })
    const store = usePolicyMarketStore()

    await store.loadInitialData()

    expect(store.consultations).toHaveLength(1)
    expect(store.news).toHaveLength(1)
    expect(store.stats.total).toBe(10)
    expect(store.selectedConsultationId).toBe('c-1')
  })

  it('提交时先插入处理中记录，成功后以 API 回答替换', async () => {
    let resolveSubmit
    api.submitConsultation.mockImplementation(() => new Promise((resolve) => { resolveSubmit = resolve }))
    const store = usePolicyMarketStore()

    const pending = store.submitQuestion('储能行业的投资机会')
    expect(store.selectedConsultation.status).toBe('processing')

    resolveSubmit({ id: 'c-new', title: '储能行业的投资机会', question: '储能行业的投资机会', answer: '结构化分析', status: 'completed', createdAt: '2026-07-23T12:00:00+08:00', sourceScope: [] })
    await pending

    expect(store.selectedConsultation).toMatchObject({ id: 'c-new', status: 'completed', answer: '结构化分析' })
  })

  it('提交失败时保留问题并记录错误，不伪造回答', async () => {
    api.submitConsultation.mockRejectedValue(new Error('服务暂不可用'))
    const store = usePolicyMarketStore()

    await expect(store.submitQuestion('现货市场运行情况')).rejects.toThrow('服务暂不可用')

    expect(store.selectedConsultation).toMatchObject({ question: '现货市场运行情况', status: 'failed' })
    expect(store.selectedConsultation.answer).toBe('')
    expect(store.submitError).toBe('服务暂不可用')
  })

  it('筛选变化时将当前参数传递给统计 API', async () => {
    api.getConsultationStats.mockResolvedValue({ total: 186, trend: 9.3, rangeLabel: '内蒙古' })
    const store = usePolicyMarketStore()

    await store.setStatsFilters({ province: '内蒙古', period: 'month', topic: '政策' })

    expect(api.getConsultationStats).toHaveBeenCalledWith({ province: '内蒙古', period: 'month', topic: '政策' })
    expect(store.stats.total).toBe(186)
  })
})

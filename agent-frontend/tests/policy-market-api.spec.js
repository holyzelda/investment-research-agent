import { describe, expect, it } from 'vitest'
import {
  getConsultationStats,
  getConsultations,
  getMarketNews,
  submitConsultation,
} from '@/api/policyMarket'

describe('政策与市场模拟 API', () => {
  it('返回可直接映射为页面 DTO 的咨询记录', async () => {
    const records = await getConsultations()

    expect(records.length).toBeGreaterThan(0)
    expect(records[0]).toMatchObject({
      id: expect.any(String),
      title: expect.any(String),
      question: expect.any(String),
      answer: expect.any(String),
      status: 'completed',
      createdAt: expect.any(String),
      sourceScope: expect.any(Array),
    })
  })

  it('提交咨询后返回已完成的结构化回答', async () => {
    const consultation = await submitConsultation({ question: '储能行业的投资机会' })

    expect(consultation).toMatchObject({
      id: expect.any(String),
      title: '储能行业的投资机会',
      question: '储能行业的投资机会',
      status: 'completed',
      answer: expect.any(String),
    })
  })

  it('按筛选参数聚合统计结果', async () => {
    const all = await getConsultationStats({ province: 'all', period: 'all', topic: 'all' })
    const innerMongolia = await getConsultationStats({ province: '内蒙古', period: 'month', topic: '政策' })

    expect(all).toMatchObject({ total: expect.any(Number), trend: expect.any(Number), rangeLabel: '全部省份' })
    expect(innerMongolia).toMatchObject({ total: 186, rangeLabel: '内蒙古' })
    expect(innerMongolia.total).toBeLessThan(all.total)
  })

  it('返回带来源和正文的市场资讯', async () => {
    const news = await getMarketNews()

    expect(news[0]).toMatchObject({
      id: expect.any(String),
      category: expect.any(String),
      title: expect.any(String),
      publishedAt: expect.any(String),
      content: expect.any(String),
      source: expect.any(String),
    })
  })
})

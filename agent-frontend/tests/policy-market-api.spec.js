import { describe, expect, it, vi } from 'vitest'

vi.mock('@/utils/request', () => ({ default: vi.fn() }))

import request from '@/utils/request'
import {
  getMarketOverview,
  getConsultations,
  getMarketNews,
  submitConsultation,
} from '@/api/policyMarket'

describe('政策与市场 API', () => {
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

  it('按筛选参数获取真实市场资讯概览', async () => {
    const overview = {
      total: 12,
      trendPercent: -8.3,
      rangeLabel: '内蒙古 · 本月',
      topicOptions: [{ value: '储能', label: '储能', count: 8 }],
    }
    request.mockResolvedValue({ code: 200, msg: 'success', data: overview })

    await expect(getMarketOverview({ province: '内蒙古', period: 'month', topic: '储能' })).resolves.toEqual(overview)
    expect(request).toHaveBeenCalledWith({
      url: '/ir/policy-market/messages/overview',
      method: 'get',
      params: { province: '内蒙古', period: 'month', topic: '储能' },
    })
  })

  it('读取市场脉搏消息时解包后端响应数据', async () => {
    const messages = [{ id: 1, title: '置顶资讯', tags: ['政策'] }]
    request.mockResolvedValue({ code: 200, msg: 'success', data: messages })

    await expect(getMarketNews({ province: '内蒙古', period: 'month', topic: '储能' })).resolves.toEqual(messages)
    expect(request).toHaveBeenCalledWith({
      url: '/ir/policy-market/messages',
      method: 'get',
      params: { province: '内蒙古', period: 'month', topic: '储能' },
    })
  })
})

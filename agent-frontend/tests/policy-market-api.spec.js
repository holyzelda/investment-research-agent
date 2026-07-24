import { describe, expect, it, vi } from 'vitest'

vi.mock('@/utils/request', () => ({ default: vi.fn() }))

import request from '@/utils/request'
import {
  getConsultation,
  getConsultations,
  getMarketNews,
  getMarketOverview,
  submitConsultation,
} from '@/api/policyMarket'

describe('政策与市场 API', () => {
  it('咨询 API 使用后端列表、详情和创建端点', async () => {
    request
      .mockResolvedValueOnce({ data: [{ id: 1 }] })
      .mockResolvedValueOnce({ data: { id: 1, answer: '回答' } })
      .mockResolvedValueOnce({ data: { id: 2, answer: '新回答' } })

    await expect(getConsultations()).resolves.toEqual([{ id: 1 }])
    await expect(getConsultation(1)).resolves.toEqual({ id: 1, answer: '回答' })
    await expect(submitConsultation({ question: '宁夏政策' })).resolves.toEqual({ id: 2, answer: '新回答' })

    expect(request).toHaveBeenNthCalledWith(1, {
      url: '/ir/policy-market/consultations', method: 'get',
    })
    expect(request).toHaveBeenNthCalledWith(2, {
      url: '/ir/policy-market/consultations/1', method: 'get',
    })
    expect(request).toHaveBeenNthCalledWith(3, {
      url: '/ir/policy-market/consultations', method: 'post', data: { question: '宁夏政策' },
    })
  })

  it('按筛选参数获取真实市场资讯概览', async () => {
    const overview = {
      total: 12,
      trendPercent: -8.3,
      rangeLabel: '内蒙古 · 本月',
      topicOptions: [{ value: '储能', label: '储能', count: 8 }],
    }
    request.mockResolvedValue({ data: overview })

    await expect(getMarketOverview({ province: '内蒙古', period: 'month', topic: '储能' })).resolves.toEqual(overview)
    expect(request).toHaveBeenCalledWith({
      url: '/ir/policy-market/messages/overview',
      method: 'get',
      params: { province: '内蒙古', period: 'month', topic: '储能' },
    })
  })

  it('读取市场脉搏消息时解包后端响应数据', async () => {
    const messages = [{ id: 1, title: '置顶资讯', tags: ['政策'] }]
    request.mockResolvedValue({ data: messages })

    await expect(getMarketNews({ province: '内蒙古', period: 'month', topic: '储能' })).resolves.toEqual(messages)
    expect(request).toHaveBeenCalledWith({
      url: '/ir/policy-market/messages',
      method: 'get',
      params: { province: '内蒙古', period: 'month', topic: '储能' },
    })
  })
})

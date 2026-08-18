import { beforeEach, describe, expect, it, vi } from 'vitest'

const request = vi.hoisted(() => vi.fn())
vi.mock('@/utils/request', () => ({ default: request }))

import { createCalculationTask, getStations } from '@/api/calc'

describe('calc api', () => {
  beforeEach(() => {
    request.mockReset()
  })

  it('创建后续测算版本时通过标准 header 传递会话标识', () => {
    const payload = { province: '甘肃', param_overrides: { epc_unit_price: 0.8 } }

    createCalculationTask(payload, 'conversation-1')

    expect(request).toHaveBeenCalledWith({
      url: '/ir/calc/tasks',
      method: 'post',
      data: payload,
      headers: { 'X-IR-Conversation-Id': 'conversation-1' },
    })
    expect(payload).not.toHaveProperty('conversation_id')
  })

  it('创建新会话首个测算版本时不发送会话标识 header', () => {
    const payload = { province: '甘肃' }

    createCalculationTask(payload)

    expect(request).toHaveBeenCalledWith({
      url: '/ir/calc/tasks',
      method: 'post',
      data: payload,
      headers: undefined,
    })
  })

  it('按省份、关键字和游标分批查询节点并传递取消信号', () => {
    const signal = new AbortController().signal

    getStations({ province: '甘肃', keyword: '兰州', cursor: '兰州东', limit: 30, signal })

    expect(request).toHaveBeenCalledWith({
      url: '/ir/calc/stations',
      method: 'get',
      params: { province: '甘肃', keyword: '兰州', cursor: '兰州东', limit: 30 },
      signal,
    })
  })

  it('节点查询不发送空的可选参数', () => {
    getStations({ province: '甘肃', keyword: '', cursor: null })

    expect(request).toHaveBeenCalledWith({
      url: '/ir/calc/stations',
      method: 'get',
      params: { province: '甘肃' },
      signal: undefined,
    })
  })
})

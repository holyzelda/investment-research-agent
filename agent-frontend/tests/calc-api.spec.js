import { beforeEach, describe, expect, it, vi } from 'vitest'

const request = vi.hoisted(() => vi.fn())
vi.mock('@/utils/request', () => ({ default: request }))

import { createCalculationTask } from '@/api/calc'

describe('calc api', () => {
  beforeEach(() => {
    request.mockReset()
  })

  it('创建后续测算版本时通过 header 传递 conversation_id', () => {
    const payload = { province: '甘肃', param_overrides: { epc_unit_price: 0.8 } }

    createCalculationTask(payload, 'conversation-1')

    expect(request).toHaveBeenCalledWith({
      url: '/ir/calc/tasks',
      method: 'post',
      data: payload,
      headers: { conversation_id: 'conversation-1' },
    })
    expect(payload).not.toHaveProperty('conversation_id')
  })

  it('创建新会话首个测算版本时不发送 conversation_id header', () => {
    const payload = { province: '甘肃' }

    createCalculationTask(payload)

    expect(request).toHaveBeenCalledWith({
      url: '/ir/calc/tasks',
      method: 'post',
      data: payload,
      headers: undefined,
    })
  })
})

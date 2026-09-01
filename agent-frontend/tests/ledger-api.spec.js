import { beforeEach, describe, expect, it, vi } from 'vitest'

const request = vi.hoisted(() => vi.fn())
vi.mock('@/utils/request', () => ({ default: request }))

import { getLedgerBootstrap } from '@/api/ledger'

describe('ledger api', () => {
  beforeEach(() => {
    request.mockReset()
  })

  it('uses repeated query parameters for the bootstrap filters', () => {
    const params = { page: 1, page_size: 10, province: ['甘肃', '宁夏'] }

    getLedgerBootstrap(params)

    expect(request).toHaveBeenCalledWith({
      url: '/ir/calc/ledger/bootstrap',
      method: 'get',
      params,
      paramsSerializer: { indexes: null },
    })
  })
})

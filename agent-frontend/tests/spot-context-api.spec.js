import { describe, expect, it, vi } from 'vitest'

const request = vi.hoisted(() => vi.fn())
vi.mock('@/utils/request', () => ({ default: request }))

import { createNdjsonParser, prepareSpotContext } from '@/api/spotContext'

describe('spot context progress API', () => {
  it('parses NDJSON events split across arbitrary download chunks', () => {
    const events = []
    const parser = createNdjsonParser((event) => events.push(event))

    parser.consume('{"phase":"valid')
    parser.consume('ating"}\n{"phase":"computing","completedDays":1')
    parser.consume(',"totalDays":2}\n')
    const parsed = parser.flush()

    expect(events).toEqual([
      { phase: 'validating' },
      { phase: 'computing', completedDays: 1, totalDays: 2 },
    ])
    expect(parsed).toEqual(events)
  })

  it('uses the terminal ready frame as the response', async () => {
    const frames = [
      '{"phase":"validating"}\n',
      '{"phase":"computing","completedDays":1,"totalDays":1}\n',
      '{"phase":"ready","data":{"status":"ready","validDays":1}}\n',
    ]
    request.mockImplementation(async (config) => {
      let responseText = ''
      for (const frame of frames) {
        responseText += frame
        config.onDownloadProgress({ event: { target: { responseText } } })
      }
      return responseText
    })
    const progress = []

    const response = await prepareSpotContext(
      new File(['xlsx'], 'spot.xlsx'),
      null,
      new AbortController().signal,
      { onProgress: (event) => progress.push(event) },
    )

    expect(progress.map((event) => event.phase)).toEqual(['validating', 'computing', 'ready'])
    expect(response.data).toEqual({ status: 'ready', validDays: 1 })
  })

  it('surfaces a terminal streamed validation error', async () => {
    request.mockResolvedValue('{"phase":"error","message":"表头不匹配"}')

    await expect(prepareSpotContext(new File(['xlsx'], 'spot.xlsx'))).rejects.toThrow('表头不匹配')
  })
})

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const auth = vi.hoisted(() => ({
  getToken: vi.fn(() => 'token-1'),
  getUserIdentity: vi.fn(() => ({ userId: 'u1', username: '张三' })),
}))

vi.mock('@/utils/auth', () => auth)
vi.mock('@/utils/request', () => ({ isRelogin: { show: false } }))
vi.mock('element-plus', () => ({ ElMessageBox: { confirm: vi.fn() } }))

import { openChatStream } from '@/utils/chatSse'

const encoder = new TextEncoder()
function responseFromChunks(chunks, headers = {}) {
  let index = 0
  return {
    ok: true,
    status: 200,
    headers: new Headers(headers),
    body: {
      getReader: () => ({
        read: vi.fn(async () => (
          index < chunks.length
            ? { done: false, value: encoder.encode(chunks[index++]) }
            : { done: true, value: undefined }
        )),
      }),
    },
  }
}

async function flush() {
  await Promise.resolve()
  await Promise.resolve()
  await new Promise((resolve) => setTimeout(resolve, 0))
}

describe('openChatStream', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(() => vi.unstubAllGlobals())

  it('dispatches a completed frame before the stream ends', async () => {
    let releaseSecondRead
    let readCount = 0
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers(),
      body: {
        getReader: () => ({
          read: vi.fn(() => {
            readCount += 1
            if (readCount === 1) {
              return Promise.resolve({
                done: false,
                value: encoder.encode('event: thinking\nid: 1\ndata: {"data":{"text":"第一帧"}}\n\n'),
              })
            }
            if (readCount === 2) {
              return new Promise((resolve) => { releaseSecondRead = resolve })
            }
            return Promise.resolve({ done: true, value: undefined })
          }),
        }),
      },
    }))
    const events = []

    openChatStream('/ir/chat/diag', {}, { onEvent: (event) => events.push(event) })
    for (let attempt = 0; attempt < 10 && !releaseSecondRead; attempt += 1) {
      await Promise.resolve()
    }

    expect(releaseSecondRead).toBeTypeOf('function')
    expect(events).toEqual([{
      type: 'thinking',
      id: '1',
      data: { data: { text: '第一帧' } },
    }])

    releaseSecondRead({ done: true, value: undefined })
    await flush()
  })

  it('parses split CRLF frames and falls back to data.event', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responseFromChunks([
      'id: 1\r\ndata: {"event":"think',
      'ing","data":{"text":"甲"}}\r\n\r\n',
    ], { 'X-IR-Conversation-Id': 'c1' })))
    const events = []
    const completed = []
    const opened = []

    openChatStream('/ir/chat/diag', { message: 'x' }, {
      onEvent: (event) => events.push(event),
      onOpen: (info) => opened.push(info),
      onComplete: (info) => completed.push(info),
    })
    await flush()

    expect(events).toEqual([{ type: 'thinking', id: '1', data: { event: 'thinking', data: { text: '甲' } } }])
    expect(opened).toEqual([{ conversationId: 'c1' }])
    expect(completed).toEqual([{ reason: 'eof' }])
    expect(fetch.mock.calls[0][1].headers).toMatchObject({
      Authorization: 'Bearer token-1', userId: 'u1', username: encodeURIComponent('张三'),
    })
  })

  it('keeps event field priority and flushes a final frame without blank line', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responseFromChunks([
      'event: answer\ndata: {"event":"thinking","data":{"answer":"完成"}}',
    ])))
    const events = []
    openChatStream('/ir/chat/diag', {}, { onEvent: (event) => events.push(event) })
    await flush()
    expect(events[0].type).toBe('answer')
    expect(events[0].data.data.answer).toBe('完成')
  })

  it('reports abort as completion without an error event', async () => {
    let signal
    vi.stubGlobal('fetch', vi.fn((_url, init) => {
      signal = init.signal
      return new Promise((_resolve, reject) => {
        signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
      })
    }))
    const events = []
    const completed = []
    const stream = openChatStream('/ir/chat/diag', {}, {
      onEvent: (event) => events.push(event),
      onComplete: (info) => completed.push(info),
    })
    stream.close()
    await flush()
    expect(signal.aborted).toBe(true)
    expect(events).toEqual([])
    expect(completed).toEqual([{ reason: 'aborted' }])
  })
})

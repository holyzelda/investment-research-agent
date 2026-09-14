import request from '@/utils/request'

export function createNdjsonParser(onEvent) {
  let buffer = ''
  const parsedEvents = []

  function consume(text = '', { flush = false } = {}) {
    buffer += text
    const lines = buffer.split('\n')
    buffer = flush ? '' : (lines.pop() || '')
    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed) continue
      try {
        const event = JSON.parse(trimmed)
        parsedEvents.push(event)
        onEvent?.(event)
      } catch {
        // A malformed frame must not hide a later valid ready/error event.
      }
    }
  }

  return {
    consume,
    flush() {
      consume('', { flush: true })
      return parsedEvents
    },
  }
}

export async function prepareSpotContext(file, conversationId, signal, { onUploadProgress, onProgress } = {}) {
  const data = new FormData()
  data.append('file', file)
  if (conversationId) data.append('conversation_id', conversationId)
  let responseText = ''
  const parser = createNdjsonParser(onProgress)
  const response = await request({
    url: '/ir/calc/spot-context/prepare',
    method: 'post',
    data,
    signal,
    timeout: 5 * 60 * 1000,
    responseType: 'text',
    __rawResponse: true,
    onUploadProgress,
    onDownloadProgress: (progressEvent) => {
      const target = progressEvent?.event?.target || progressEvent?.target
      const nextText = target?.responseText || ''
      if (!nextText || nextText.length <= responseText.length) return
      const chunk = nextText.slice(responseText.length)
      responseText = nextText
      parser.consume(chunk)
    },
  })
  const remainingResponse = String(response || '').slice(responseText.length)
  if (remainingResponse) parser.consume(remainingResponse)
  const events = parser.flush()
  const finalEvent = events.findLast((event) => event.phase === 'ready' || event.phase === 'error')
  if (!finalEvent || finalEvent.phase === 'error') {
    throw new Error(finalEvent?.message || '电价文件处理失败，请稍后重试')
  }
  return { data: finalEvent.data }
}

export function getSpotContext(conversationId) {
  return request({
    url: '/ir/calc/spot-context',
    method: 'get',
    params: { conversation_id: conversationId },
  })
}

export function removeSpotContext({ conversationId, contextToken }) {
  return request({
    url: '/ir/calc/spot-context',
    method: 'delete',
    params: conversationId
      ? { conversation_id: conversationId }
      : { context_token: contextToken },
  })
}

export function downloadSpotContextTemplate() {
  return request({
    url: '/ir/calc/spot-context/template',
    method: 'get',
    responseType: 'blob',
  })
}

import request from '@/utils/request'

export function prepareSpotContext(file, conversationId, signal) {
  const data = new FormData()
  data.append('file', file)
  if (conversationId) data.append('conversation_id', conversationId)
  return request({
    url: '/ir/calc/spot-context/prepare',
    method: 'post',
    data,
    signal,
    timeout: 5 * 60 * 1000,
  })
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

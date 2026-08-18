import request from '@/utils/request'

export function createCalculationTask(payload, conversationId) {
  return request({
    url: '/ir/calc/tasks',
    method: 'post',
    data: payload,
    headers: conversationId ? { 'X-IR-Conversation-Id': conversationId } : undefined,
  })
}

export function getCalculationTask(taskId) {
  return request({
    url: `/ir/calc/tasks/${taskId}`,
    method: 'get',
  })
}

export function getCalculationResult(taskId) {
  return request({
    url: `/ir/calc/tasks/${taskId}/result`,
    method: 'get',
  })
}

export function listConversations(cursor) {
  return request({
    url: '/ir/conversations',
    method: 'get',
    params: cursor ? { cursor } : undefined,
  })
}

export function getConversation(conversationId) {
  return request({
    url: `/ir/conversations/${conversationId}`,
    method: 'get',
  })
}

export function getParamDict(province) {
  return request({
    url: '/ir/calc/param-dict',
    method: 'get',
    params: province ? { province } : undefined,
  })
}

export function getStations({ province, keyword, cursor, limit, signal }) {
  const params = { province }
  if (keyword) params.keyword = keyword
  if (cursor) params.cursor = cursor
  if (limit) params.limit = limit
  return request({
    url: '/ir/calc/stations',
    method: 'get',
    params,
    signal,
  })
}

export function getPlatformStats() {
  return request({
    url: '/ir/calc/stats',
    method: 'get',
  })
}

export function deleteConversation(conversationId) {
  return request({
    url: `/ir/conversations/${conversationId}`,
    method: 'delete',
  })
}

export function renameConversation(conversationId, title) {
  return request({
    url: `/ir/conversations/${conversationId}`,
    method: 'patch',
    data: { title },
  })
}

export function createShare(taskId, durationDays = 7) {
  return request({
    url: '/ir/calc/shares',
    method: 'post',
    data: { task_id: taskId, duration_days: durationDays },
  })
}

export function listShares(conversationId, taskId) {
  return request({
    url: '/ir/calc/shares',
    method: 'get',
    params: { conversation_id: conversationId, task_id: taskId },
  })
}

export function revokeShare(shareId, taskId) {
  return request({
    url: '/ir/calc/shares/revoke',
    method: 'post',
    params: { share_id: shareId, task_id: taskId },
  })
}

export function getPublicShare(shareCode) {
  return request({
    url: `/ir/public/calculation-shares/${shareCode}`,
    method: 'get',
    headers: { isToken: false },
  })
}

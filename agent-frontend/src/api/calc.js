import request from '@/utils/request'

export function createCalculationTask(payload, conversationId) {
  return request({
    url: '/ir/calc/tasks',
    method: 'post',
    data: payload,
    headers: conversationId ? { 'conversation-id': conversationId } : undefined,
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

export function listConversations() {
  return request({
    url: '/ir/conversations',
    method: 'get',
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

export function getStations(province) {
  return request({
    url: '/ir/calc/stations',
    method: 'get',
    params: { province },
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

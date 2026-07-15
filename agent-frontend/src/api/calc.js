import request from '@/utils/request'

export function createCalculationTask(payload) {
  return request({
    url: '/ir/calc/tasks',
    method: 'post',
    data: payload,
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

export function deleteConversation(conversationId) {
  return request({
    url: `/ir/conversations/${conversationId}`,
    method: 'delete',
  })
}

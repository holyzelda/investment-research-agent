import request from '@/utils/request'

export function getConsultations() {
  return request({ url: '/ir/policy-market/consultations', method: 'get' }).then((response) => response.data)
}

export function getConsultation(id) {
  return request({ url: `/ir/policy-market/consultations/${id}`, method: 'get' }).then((response) => response.data)
}

export function submitConsultation({ question }) {
  const normalizedQuestion = String(question || '').trim()
  if (!normalizedQuestion) return Promise.reject(new Error('请输入政策或市场问题'))

  return request({
    url: '/ir/policy-market/consultations',
    method: 'post',
    data: { question: normalizedQuestion },
  }).then((response) => response.data)
}

export function getMarketNews(params = {}) {
  return request({ url: '/ir/policy-market/messages', method: 'get', params }).then((response) => response.data)
}

export function getMarketOverview(params = {}) {
  return request({
    url: '/ir/policy-market/messages/overview',
    method: 'get',
    params,
  }).then((response) => response.data)
}

import request from '@/utils/request'

export function getConsultations() {
  return request({ url: '/ir/policy-market/consultations', method: 'get' }).then((response) => response.data)
}

export function getConsultation(id) {
  return request({ url: `/ir/policy-market/consultations/${id}`, method: 'get' }).then((response) => response.data)
}

export function deleteConsultation(id) {
  return request({ url: `/ir/policy-market/consultations/${id}`, method: 'delete' }).then((response) => response.data)
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

// 知识库源文件在飞书上，外部用户打不开原链接；经后端代理取回二进制。
// 必须走 request 实例而不是 window.open：平台身份是请求头，裸开新窗口带不上，会 401。
export function downloadSourceFile(token) {
  const normalizedToken = String(token || '').trim()
  if (!normalizedToken) return Promise.reject(new Error('缺少源文件标识'))

  return request({
    url: `/ir/policy-market/source-files/${encodeURIComponent(normalizedToken)}`,
    method: 'get',
    responseType: 'blob',
  })
}

export function getMarketOverview(params = {}) {
  return request({
    url: '/ir/policy-market/messages/overview',
    method: 'get',
    params,
  }).then((response) => response.data)
}

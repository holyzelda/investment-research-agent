import request from '@/utils/request'

const delay = (value, ms = 180) => new Promise((resolve) => window.setTimeout(() => resolve(value), ms))

const consultations = [
  {
    id: 'consultation-001',
    title: '新能源消纳政策有何变化？',
    question: '新能源消纳政策有何变化？',
    answer: '近期政策重点已从单纯扩大新能源装机，转向提升系统消纳能力。项目投资应重点关注并网条件、消纳责任权重和峰谷价差变化。',
    status: 'completed',
    createdAt: '2026-07-23T10:42:00+08:00',
    sourceScope: ['政策文件', '市场行情', '行业资讯'],
  },
  {
    id: 'consultation-002',
    title: '本月电价机制如何影响制造业？',
    question: '本月电价机制如何影响制造业？',
    answer: '峰谷价差扩大与市场化交易比例提升，使制造企业更需要评估中长期合约与现货采购的组合，并通过柔性负荷和错峰生产降低综合用能成本。',
    status: 'completed',
    createdAt: '2026-07-22T16:18:00+08:00',
    sourceScope: ['政策文件', '市场行情', '行业资讯'],
  },
  {
    id: 'consultation-003',
    title: '绿电交易与碳市场的关系',
    question: '绿电交易与碳市场的关系',
    answer: '绿电交易证明可再生能源电力消费，碳市场通过配额约束与碳价形成减排成本信号。企业应分别留存绿电交易凭证与碳排放核算材料，避免环境权益重复计算。',
    status: 'completed',
    createdAt: '2026-07-18T09:30:00+08:00',
    sourceScope: ['政策文件', '市场行情', '行业资讯'],
  },
]

export function getConsultations() {
  return delay(consultations.map((item) => ({ ...item, sourceScope: [...item.sourceScope] })))
}

export function submitConsultation({ question }) {
  const normalizedQuestion = String(question || '').trim()
  if (!normalizedQuestion) return Promise.reject(new Error('请输入政策或市场问题'))

  return delay({
    id: `consultation-${Date.now()}`,
    title: normalizedQuestion,
    question: normalizedQuestion,
    answer: '已收到你的咨询。系统将结合政策原文、市场数据与相关行业动态进行整理，为你生成结构化分析。',
    status: 'completed',
    createdAt: new Date().toISOString(),
    sourceScope: ['政策文件', '市场行情', '行业资讯'],
  }, 420)
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

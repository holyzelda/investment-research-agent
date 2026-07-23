import request from '@/utils/request'

// 咨询与统计暂保持模拟实现；市场脉搏由后端接口提供真实数据。
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

const marketNews = [
  {
    id: 'news-001',
    category: '政策',
    title: '国家能源局：加快推动新型储能规模化发展',
    publishedAt: '2026-07-23T09:00:00+08:00',
    content: '国家能源局近日发布相关工作安排，提出完善新型储能参与电力市场和调度运行机制，进一步释放储能的灵活调节价值。',
    source: '政策与市场研究台公开信息整理',
  },
  {
    id: 'news-002',
    category: '市场',
    title: '2026 年上半年绿电交易规模同比增长 43%',
    publishedAt: '2026-07-22T09:00:00+08:00',
    content: '上半年绿色电力交易保持活跃，交易品种和参与主体持续扩展，制造业企业的绿电消费需求成为重要增长动力。',
    source: '政策与市场研究台公开信息整理',
  },
  {
    id: 'news-003',
    category: '观察',
    title: '现货市场连续运行试点进入关键阶段',
    publishedAt: '2026-07-21T09:00:00+08:00',
    content: '多地电力现货市场建设进入新阶段，价格发现与风险管理机制成为市场主体近期关注重点。',
    source: '政策与市场研究台公开信息整理',
  },
  {
    id: 'news-004',
    category: '政策',
    title: '工信部发布工业领域碳达峰实施方案',
    publishedAt: '2026-07-18T09:00:00+08:00',
    content: '方案围绕重点行业节能降碳、绿色低碳技术装备与数字化转型提出系统性安排。',
    source: '政策与市场研究台公开信息整理',
  },
]

const consultationStats = [
  { province: '内蒙古', period: 'month', topic: '政策', count: 186 },
  { province: '内蒙古', period: 'quarter', topic: '市场', count: 258 },
  { province: '山东', period: 'month', topic: '市场', count: 143 },
  { province: '山东', period: 'quarter', topic: '行业', count: 219 },
  { province: '江苏', period: 'month', topic: '行业', count: 127 },
  { province: '江苏', period: 'quarter', topic: '政策', count: 198 },
  { province: '广东', period: 'month', topic: '市场', count: 164 },
  { province: '广东', period: 'quarter', topic: '政策', count: 241 },
  { province: '河北', period: 'month', topic: '政策', count: 96 },
  { province: '浙江', period: 'month', topic: '行业', count: 112 },
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

export function getMarketNews() {
  return request({ url: '/ir/policy-market/messages', method: 'get' }).then((response) => response.data)
}

export function getConsultationStats({ province = 'all', period = 'all', topic = 'all' } = {}) {
  const matched = consultationStats.filter((item) =>
    (province === 'all' || item.province === province)
    && (period === 'all' || item.period === period || (period === 'quarter' && item.period === 'month'))
    && (topic === 'all' || item.topic === topic),
  )

  return delay({
    total: matched.reduce((sum, item) => sum + item.count, 0),
    trend: matched.length ? Number((8 + matched.length * 1.3).toFixed(1)) : 0,
    rangeLabel: province === 'all' ? '全部省份' : province,
  })
}

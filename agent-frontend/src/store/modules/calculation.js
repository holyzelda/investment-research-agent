import { defineStore } from 'pinia'
import {
  createCalculationTask,
  deleteConversation,
  getCalculationResult,
  getCalculationTask,
  getConversation,
  getParamDict,
  getStations,
  listConversations,
} from '@/api/calc'

const PROVINCES = [
  ['内蒙古自治区', '内蒙古'], ['广西壮族自治区', '广西'], ['宁夏回族自治区', '宁夏'],
  ['新疆维吾尔自治区', '新疆'], ['西藏自治区', '西藏'],
  ...[
    '北京', '天津', '上海', '重庆', '河北', '山西', '辽宁', '吉林', '黑龙江',
    '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南', '湖北', '湖南',
    '广东', '海南', '四川', '贵州', '云南', '陕西', '甘肃', '青海', '台湾',
    '香港', '澳门',
  ].map((name) => [name, name]),
]

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
let messageId = 0
const nextId = () => `m${++messageId}`

export function extractMinInput(text) {
  const content = String(text || '')
  const province = PROVINCES.find(([full, short]) => content.includes(full) || content.includes(short))?.[1]
  const power = content.match(/(\d+(?:\.\d+)?)\s*MW(?!H)/i)
  const capacity = content.match(/(\d+(?:\.\d+)?)\s*MWH/i)
  const powerMw = power ? Number(power[1]) : null
  const capacityMwh = capacity ? Number(capacity[1]) : null
  const missing = []

  if (!province) missing.push('省份')
  if (!(powerMw > 0)) missing.push('项目功率（MW）')
  if (!(capacityMwh > 0)) missing.push('项目容量（MWh）')

  return {
    province: province || null,
    power_mw: powerMw > 0 ? powerMw : null,
    capacity_mwh: capacityMwh > 0 ? capacityMwh : null,
    missing,
  }
}

function failureText(message, requestId) {
  return `测算失败：${message || '未知错误'}\nrequest_id：${requestId || '未返回'}`
}

export const useCalculationStore = defineStore('calculation', {
  state: () => ({
    messages: [],
    versions: [],
    history: [],
    conversationId: null,
    selectedVersion: null,
    responding: false,
    paramDict: [],
    switches: {},
    stationOptions: [],
  }),
  getters: {
    latestVersion: (state) => state.versions[state.versions.length - 1] || null,
    selectedVersionEntry: (state) => (
      state.versions.find((item) => item.version === state.selectedVersion) || null
    ),
  },
  actions: {
    resetConversation() {
      this.messages = []
      this.versions = []
      this.conversationId = null
      this.selectedVersion = null
      this.responding = false
    },
    selectVersion(version) {
      if (this.versions.some((item) => item.version === version)) this.selectedVersion = version
    },
    async loadHistory() {
      const response = await listConversations()
      this.history = response.data?.items || []
    },
    async loadParamMeta(province) {
      if (!province) return
      const paramResponse = await getParamDict(province)
      this.paramDict = paramResponse.data?.parameters || []
      this.switches = paramResponse.data?.switches || {}
      try {
        const stationResponse = await getStations(province)
        this.stationOptions = stationResponse.data?.items || []
      } catch (error) {
        // 节点维表或 stations 接口不可用时，仍可展示和调整其他参数；节点卡片自然隐藏。
        this.stationOptions = []
      }
    },
    async openConversation(conversationId) {
      const response = await getConversation(conversationId)
      const detail = response.data || {}
      const completed = (detail.versions || []).filter((version) => version.result)
      let cursor = 0
      this.messages = (detail.messages || []).map((message) => {
        if (message.role === 'assistant' && cursor < completed.length) {
          const version = completed[cursor]
          cursor += 1
          return {
            id: nextId(), role: 'assistant', kind: 'result',
            version: version.version, result: version.result, input: version.input,
          }
        }
        return { id: nextId(), role: message.role, kind: 'text', text: message.content }
      })
      this.versions = completed.map((version) => ({
        conversationId,
        taskId: version.taskId,
        version: version.version,
        status: version.status,
        result: version.result,
        input: version.input,
      }))
      this.conversationId = conversationId
      this.selectedVersion = this.versions.length
        ? this.versions[this.versions.length - 1].version
        : null
      this.responding = false
      const province = completed.length ? completed[completed.length - 1].input?.province : null
      if (province) this.loadParamMeta(province).catch(() => {})
    },
    async removeConversation(conversationId) {
      await deleteConversation(conversationId)
      this.history = this.history.filter((item) => item.conversationId !== conversationId)
      if (this.conversationId === conversationId) this.resetConversation()
    },
    _pushUser(text) {
      this.messages.push({ id: nextId(), role: 'user', kind: 'text', text })
    },
    _pushAssistantText(text) {
      const message = { id: nextId(), role: 'assistant', kind: 'text', text }
      this.messages.push(message)
      return message
    },
    async _waitForTerminal(task) {
      if (task.status === 'completed' || task.status === 'failed') return task
      for (let attempt = 0; attempt < 60; attempt += 1) {
        await wait(1000)
        const response = await getCalculationTask(task.taskId)
        const current = response.data || {}
        if (current.status === 'completed' || current.status === 'failed') return current
      }
      return {
        status: 'failed',
        requestId: task.requestId,
        error: { message: '测算等待超时' },
      }
    },
    async sendAndCalculate(text) {
      if (this.responding) return
      const content = String(text || '').trim()
      if (!content) return

      this._pushUser(content)
      const input = extractMinInput(content)
      if (input.missing.length) {
        this._pushAssistantText(`请补充${input.missing.join('、')}。`)
        return
      }

      const payload = {
        province: input.province,
        capacity_mwh: input.capacity_mwh,
        power_mw: input.power_mw,
      }
      if (this.conversationId) payload.conversation_id = this.conversationId
      await this._submitAndTrack(payload)
    },
    async recalculate({ overrides, basics }) {
      if (this.responding || !this.conversationId) return
      // 省份在会话内永久锁定：以任一已成功版本的冻结入参为准，不允许调整面板改动
      const province = this.versions.find((v) => v.input)?.input?.province
      if (!province) return
      await this._submitAndTrack({
        province,
        capacity_mwh: basics.capacity_mwh,
        power_mw: basics.power_mw,
        node_name: basics.node_name || null,
        conversation_id: this.conversationId,
        param_overrides: overrides,
      })
    },
    async _submitAndTrack(payload) {
      this.responding = true
      const pending = this._pushAssistantText('测算中…')
      try {
        const createdResponse = await createCalculationTask(payload)
        const created = createdResponse.data || {}
        if (created.conversationId) this.conversationId = created.conversationId

        const terminal = await this._waitForTerminal(created)
        if (terminal.status !== 'completed') {
          const error = terminal.error || created.error || {}
          pending.text = failureText(error.message, error.requestId || terminal.requestId)
          return
        }

        const resultResponse = await getCalculationResult(created.taskId)
        const result = resultResponse.data || {}
        const version = created.version || result.version
        const entry = {
          conversationId: created.conversationId,
          taskId: created.taskId,
          version,
          status: 'completed',
          result,
          input: created.input,
        }
        this.versions.push(entry)
        this.selectedVersion = version
        pending.kind = 'result'
        pending.text = undefined
        pending.result = result
        pending.version = version
        pending.input = created.input
        // 成功后刷新左侧历史（新会话出现、既有会话最新版本/排序更新）与调整面板元数据
        this.loadHistory().catch(() => {})
        if (result.basicInfo?.province) this.loadParamMeta(result.basicInfo.province).catch(() => {})
      } catch (error) {
        pending.text = failureText(error?.response?.data?.msg || error?.message)
      } finally {
        this.responding = false
      }
    },
  },
})

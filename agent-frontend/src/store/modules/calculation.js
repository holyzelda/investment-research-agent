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
  renameConversation,
} from '@/api/calc'
import { createReport, getReportTask } from '@/api/report'
import { streamReportEvents } from '@/utils/reportSse'
import { openChatStream } from '@/utils/chatSse'
import {
  createThinkingState,
  applyThinkingFrame,
  finalizeThinking,
  thinkingNodes,
  hasActiveNode,
} from '@/utils/thinkingChain'

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
let messageId = 0
const nextId = () => `m${++messageId}`

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
    reports: [],
    reportTasks: {},
    activeStream: null,
  }),
  getters: {
    latestVersion: (state) => state.versions[state.versions.length - 1] || null,
    selectedVersionEntry: (state) => (
      state.versions.find((item) => item.version === state.selectedVersion) || null
    ),
  },
  actions: {
    resetConversation() {
      this.stopStream()
      this.messages = []
      this.versions = []
      this.conversationId = null
      this.selectedVersion = null
      this.responding = false
      this.reports = []
      this.reportTasks = {}
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
            report: version.report, calculatedAt: version.calculatedAt,
          }
        }
        if (message.messageType === 'report_generated') {
          return { id: nextId(), role: message.role, kind: 'report-generated', text: message.content, payload: message.payload }
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
        report: version.report,
        calculatedAt: version.calculatedAt,
      }))
      this.reports = detail.reports || []
      this.reportTasks = Object.fromEntries(
        [...this.reports, ...completed.map((version) => version.report)].filter(Boolean)
          .filter((report) => report.reportTaskId)
          .map((report) => [report.reportTaskId, report]),
      )
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
    async renameConversation(conversationId, title) {
      const cleaned = String(title || '').trim()
      if (!cleaned) return
      await renameConversation(conversationId, cleaned)
      const item = this.history.find((entry) => entry.conversationId === conversationId)
      if (item) item.title = cleaned
    },
    _pushUser(text) {
      this.messages.push({ id: nextId(), role: 'user', kind: 'text', text })
    },
    stopStream() {
      if (this.activeStream) {
        this.activeStream.close()
        this.activeStream = null
      }
    },
    // 主对话：经我方 /ir/chat/diag 流式接入中台。前端不做参数解析/校验，原样发送。
    async sendAndCalculate(text) {
      if (this.responding) return
      const content = String(text || '').trim()
      if (!content) return

      this._pushUser(content)

      // 流式助手消息：承载思考节点链、流式文本、以及测算完成后内嵌的结果卡片。
      const streamMsg = {
        id: nextId(),
        role: 'assistant',
        kind: 'assistant-stream',
        thinkingState: createThinkingState(),
        answerText: '',
        recommendedQuestions: [],
        result: null,
        version: null,
        input: null,
        calculatedAt: null,
        taskId: null,
        done: false,
        error: null,
      }
      this.messages.push(streamMsg)
      this.responding = true

      await new Promise((resolve) => {
        const finish = () => {
          finalizeThinking(streamMsg.thinkingState)
          streamMsg.done = true
          this.responding = false
          this.activeStream = null
          resolve()
        }

        this.activeStream = openChatStream(
          '/ir/chat/diag',
          { message: content, conversation_id: this.conversationId || undefined },
          {
            onOpen: ({ conversationId }) => {
              // 我方会话 id 以响应头为准（中台 session_id 不暴露给前端）
              if (conversationId && !this.conversationId) this.conversationId = conversationId
            },
            onEvent: (e) => {
              const data = e.data && typeof e.data === 'object' ? e.data : {}
              const inner = data.data && typeof data.data === 'object' ? data.data : {}

              switch (e.type) {
                case 'session_start':
                  // 会话 id 已由响应头确定；此处无需额外处理
                  break
                case 'thinking':
                  // 节点字段位于 data.data（node_id/node_status/text/substeps）
                  applyThinkingFrame(streamMsg.thinkingState, e.id, inner)
                  break
                case 'answer':
                  this._applyAnswerEvent(streamMsg, inner).catch(() => {})
                  break
                case 'recommended_questions':
                  streamMsg.recommendedQuestions = inner.recommended_questions || []
                  break
                case 'error':
                  streamMsg.error = data.msg || '对话出错'
                  streamMsg.answerText = failureText(streamMsg.error)
                  finish()
                  break
                case 'done':
                  finish()
                  break
                default:
                  break
              }
            },
          },
        )
      })
    },
    // 处理 answer 事件：命中测算工具则据 taskId 拉结果并升级为版本；否则累加文本答案。
    async _applyAnswerEvent(streamMsg, inner) {
      const answerText = inner.answer || ''
      if (answerText) streamMsg.answerText += answerText

      const biz = Array.isArray(inner.biz) ? inner.biz : []
      const calcTool = biz.find((item) => item.tool === 'create_calculation_task')
      if (!calcTool) return

      const created = calcTool.payload?.data || {}
      if (!created.taskId || created.status !== 'completed') {
        // 未完成或无 taskId：仅记录冻结入参，结果留待后续
        if (created.conversationId && !this.conversationId) this.conversationId = created.conversationId
        return
      }
      if (created.conversationId && !this.conversationId) this.conversationId = created.conversationId

      // 方案1：据 taskId 另调 result 接口取三模块
      const resultResponse = await getCalculationResult(created.taskId)
      const result = resultResponse.data || {}
      const version = created.version || result.version
      const entry = {
        conversationId: created.conversationId || this.conversationId,
        taskId: created.taskId,
        version,
        status: 'completed',
        result,
        input: created.input,
        calculatedAt: result.calculatedAt,
      }
      this.versions.push(entry)
      this.selectedVersion = version
      streamMsg.result = result
      streamMsg.version = version
      streamMsg.input = created.input
      streamMsg.calculatedAt = result.calculatedAt
      streamMsg.taskId = created.taskId
      // 成功后刷新左侧历史与调整面板元数据（尽力而为）
      this.loadHistory().catch(() => {})
      if (result.basicInfo?.province) this.loadParamMeta(result.basicInfo.province).catch(() => {})
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
    // 重新测算：保留直调 /ir/calc/tasks，但用与思考过程一致的进度态展示。
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
    // 直调测算 + 统一进度展示：以「测算进行中」思考样式占位，完成后升级为结果卡片。
    async _submitAndTrack(payload) {
      this.responding = true
      const streamMsg = {
        id: nextId(),
        role: 'assistant',
        kind: 'assistant-stream',
        thinkingState: createThinkingState(),
        answerText: '',
        recommendedQuestions: [],
        result: null,
        version: null,
        input: null,
        calculatedAt: null,
        taskId: null,
        done: false,
        error: null,
      }
      // 单节点进度占位（与思考链同款展示）
      applyThinkingFrame(streamMsg.thinkingState, '1', {
        node_id: 'recalc',
        node_seq: 0,
        node_title: '重新测算',
        node_status: 'active',
        node_subtitle: '正在按调整后的参数重新测算…',
      })
      this.messages.push(streamMsg)
      try {
        const createdResponse = await createCalculationTask(payload)
        const created = createdResponse.data || {}
        if (created.conversationId) this.conversationId = created.conversationId

        const terminal = await this._waitForTerminal(created)
        if (terminal.status !== 'completed') {
          const error = terminal.error || created.error || {}
          applyThinkingFrame(streamMsg.thinkingState, '2', {
            node_id: 'recalc', node_status: 'aborted', node_subtitle: '测算失败',
          })
          finalizeThinking(streamMsg.thinkingState)
          streamMsg.error = error.message
          streamMsg.answerText = failureText(error.message, error.requestId || terminal.requestId)
          streamMsg.done = true
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
          calculatedAt: result.calculatedAt,
        }
        this.versions.push(entry)
        this.selectedVersion = version
        applyThinkingFrame(streamMsg.thinkingState, '2', {
          node_id: 'recalc', node_status: 'completed', node_subtitle: '测算完成',
        })
        finalizeThinking(streamMsg.thinkingState)
        streamMsg.result = result
        streamMsg.version = version
        streamMsg.input = created.input
        streamMsg.calculatedAt = result.calculatedAt
        streamMsg.taskId = created.taskId
        streamMsg.done = true
        this.loadHistory().catch(() => {})
        if (result.basicInfo?.province) this.loadParamMeta(result.basicInfo.province).catch(() => {})
      } catch (error) {
        applyThinkingFrame(streamMsg.thinkingState, '3', {
          node_id: 'recalc', node_status: 'aborted', node_subtitle: '测算失败',
        })
        finalizeThinking(streamMsg.thinkingState)
        streamMsg.error = error?.response?.data?.msg || error?.message
        streamMsg.answerText = failureText(streamMsg.error)
        streamMsg.done = true
      } finally {
        this.responding = false
      }
    },
    async generateReport(taskId) {
      const created = (await createReport(taskId)).data || {}
      if (created.status === 'completed') {
        const report = { reportId: created.reportId, taskId, status: 'completed' }
        this._applyReport(report)
        return report
      }
      this.reportTasks[created.reportTaskId] = created
      const progressMessage = {
        id: nextId(), role: 'assistant', kind: 'report-progress', taskId,
        reportTaskId: created.reportTaskId, steps: created.steps || [],
      }
      this.messages.push(progressMessage)
      this._applyReport({ taskId, reportTaskId: created.reportTaskId, status: 'generating' })
      const controller = new AbortController()
      try {
        await streamReportEvents(created.reportTaskId, {
          signal: controller.signal,
          onEvent: ({ type, data }) => {
            if (type === 'complete' || type === 'failed') {
              const observedSteps = this.reportTasks[created.reportTaskId]?.steps || []
              this._applyReport(data)
              progressMessage.steps = [...observedSteps, ...((data.steps || []).filter((step) => step.state !== 'active'))]
              if (type === 'complete' && data.reportId) {
                progressMessage.kind = 'report-generated'
                progressMessage.text = '报告已生成'
                progressMessage.payload = { event_type: 'report_generated', report_id: data.reportId, task_id: taskId }
                this.syncReportsFromConversation().catch(() => {})
              }
            } else {
              const next = { ...this.reportTasks[created.reportTaskId], steps: [...(this.reportTasks[created.reportTaskId]?.steps || []), data] }
              this.reportTasks[created.reportTaskId] = next
              progressMessage.steps = next.steps
            }
          },
        })
      } catch (error) {
        const recovered = (await getReportTask(created.reportTaskId)).data || {}
        this._applyReport(recovered)
      }
      return this.reportTasks[created.reportTaskId]
    },
    async syncReportsFromConversation() {
      if (!this.conversationId) return
      const response = await getConversation(this.conversationId)
      const detail = response.data || {}
      this.reports = detail.reports || []
      for (const version of this.versions) {
        const remote = (detail.versions || []).find((item) => item.taskId === version.taskId)
        if (remote?.report) version.report = remote.report
      }
      this.reportTasks = Object.fromEntries(
        [...this.reports, ...this.versions.map((version) => version.report)].filter(Boolean)
          .filter((report) => report.reportTaskId)
          .map((report) => [report.reportTaskId, report]),
      )
    },
    _applyReport(report) {
      if (report.reportTaskId) this.reportTasks[report.reportTaskId] = report
      const index = this.reports.findIndex((item) => item.taskId === report.taskId)
      const prior = index >= 0 ? this.reports[index] : {}
      const merged = { ...prior, ...report }
      if (index >= 0) this.reports.splice(index, 1, merged)
      else this.reports.push(merged)
      const version = this.versions.find((item) => item.taskId === report.taskId)
      if (version) version.report = merged
    },
  },
})

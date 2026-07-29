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
let turnId = 0
const nextId = () => `m${++messageId}`
const nextTurnId = () => ++turnId
const answerTimers = new Map()
const reportStreams = new Map()

function createReportStreamMessage(taskId) {
  return {
    ...createStreamMessage(),
    flow: 'report',
    taskId,
    reportTaskId: null,
    reportId: null,
    steps: [],
  }
}

function reportStepStatus(state) {
  if (['completed', 'succeeded', 'done'].includes(state)) return 'completed'
  if (['failed', 'error', 'cancelled'].includes(state)) return 'aborted'
  return 'active'
}

function createStreamMessage(id = nextTurnId()) {
  return {
    id: nextId(),
    turnId: id,
    role: 'assistant',
    kind: 'assistant-stream',
    phase: 'streaming',
    startedAt: Date.now(),
    finishedAt: null,
    hasThinkingStarted: false,
    thinkingState: createThinkingState(),
    answerBuffer: '',
    answerText: '',
    pendingRecommendedQuestions: [],
    recommendedQuestions: [],
    pendingResult: null,
    result: null,
    version: null,
    input: null,
    calculatedAt: null,
    taskId: null,
    handledTaskIds: [],
    doneReceived: false,
    done: false,
    cancelled: false,
    error: null,
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
    reports: [],
    reportTasks: {},
    activeReportCount: 0,
    activeStream: null,
    activeTurnId: null,
    conversationEpoch: 0,
    historyOpenEpoch: 0,
  }),
  getters: {
    latestVersion: (state) => state.versions[state.versions.length - 1] || null,
    selectedVersionEntry: (state) => (
      state.versions.find((item) => item.version === state.selectedVersion) || null
    ),
    hasActiveReportGeneration: (state) => state.activeReportCount > 0,
  },
  actions: {
    resetConversation() {
      this.disposeActiveTurn({ visible: false })
      this.disposeReportStreams()
      this.conversationEpoch += 1
      this.historyOpenEpoch += 1
      this.messages = []
      this.versions = []
      this.conversationId = null
      this.selectedVersion = null
      this.responding = false
      this.reports = []
      this.reportTasks = {}
      this.activeReportCount = 0
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
      this.disposeActiveTurn({ visible: false })
      this.disposeReportStreams()
      const openEpoch = ++this.historyOpenEpoch
      const conversationEpoch = ++this.conversationEpoch
      const response = await getConversation(conversationId)
      if (openEpoch !== this.historyOpenEpoch || conversationEpoch !== this.conversationEpoch) return
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
    _messageForTurn(id) {
      return this.messages.find((message) => message.turnId === id) || null
    },
    _isCurrentTurn(id, epoch) {
      return this.activeTurnId === id && this.conversationEpoch === epoch
    },
    _clearAnswerTimer(id) {
      const timer = answerTimers.get(id)
      if (timer) clearInterval(timer)
      answerTimers.delete(id)
    },
    _releaseTurn(id) {
      this._clearAnswerTimer(id)
      if (this.activeTurnId !== id) return
      this.activeTurnId = null
      this.activeStream = null
      this.responding = false
    },
    _finishTyping(streamMsg) {
      if (!streamMsg || streamMsg.done || streamMsg.error || streamMsg.cancelled) return
      streamMsg.recommendedQuestions = [...streamMsg.pendingRecommendedQuestions]
      streamMsg.pendingRecommendedQuestions = []
      streamMsg.phase = 'completed'
      streamMsg.done = true
      this._releaseTurn(streamMsg.turnId)
    },
    _startAnswerTyping(streamMsg, epoch) {
      if (!this._isCurrentTurn(streamMsg.turnId, epoch) || streamMsg.error || streamMsg.cancelled) return
      if (!streamMsg.answerBuffer) {
        this._finishTyping(streamMsg)
        return
      }
      if (answerTimers.has(streamMsg.turnId)) return
      const chars = streamMsg.answerBuffer.split('')
      streamMsg.answerBuffer = ''
      const timer = setInterval(() => {
        if (!this._isCurrentTurn(streamMsg.turnId, epoch) || streamMsg.error || streamMsg.cancelled) {
          this._clearAnswerTimer(streamMsg.turnId)
          return
        }
        if (!chars.length) {
          this._clearAnswerTimer(streamMsg.turnId)
          this._finishTyping(streamMsg)
          return
        }
        const pending = chars.length
        const batchSize = pending > 300 ? 15 : pending > 100 ? 6 : pending > 30 ? 2 : 1
        streamMsg.answerText += chars.splice(0, batchSize).join('')
      }, 16)
      answerTimers.set(streamMsg.turnId, timer)
    },
    _showPendingResult(streamMsg, epoch) {
      if (!streamMsg.doneReceived || !streamMsg.pendingResult || streamMsg.result) return
      if (this.conversationEpoch !== epoch || streamMsg.cancelled || streamMsg.error) return
      const { entry, result } = streamMsg.pendingResult
      if (!this.versions.some((item) => item.taskId === entry.taskId)) this.versions.push(entry)
      this.selectedVersion = entry.version
      streamMsg.result = result
      streamMsg.version = entry.version
      streamMsg.input = entry.input
      streamMsg.calculatedAt = entry.calculatedAt
      streamMsg.taskId = entry.taskId
      streamMsg.pendingResult = null
      this.loadHistory().catch(() => {})
      if (result.basicInfo?.province) this.loadParamMeta(result.basicInfo.province).catch(() => {})
    },
    _failTurn(streamMsg, message) {
      if (!streamMsg || streamMsg.done || streamMsg.cancelled) return
      this._clearAnswerTimer(streamMsg.turnId)
      finalizeThinking(streamMsg.thinkingState)
      streamMsg.finishedAt ||= Date.now()
      streamMsg.error = message || '对话出错'
      streamMsg.answerBuffer = ''
      streamMsg.pendingResult = null
      streamMsg.pendingRecommendedQuestions = []
      streamMsg.answerText = failureText(streamMsg.error)
      streamMsg.phase = 'error'
      streamMsg.done = true
      this._releaseTurn(streamMsg.turnId)
    },
    disposeActiveTurn({ visible = false } = {}) {
      const id = this.activeTurnId
      if (!id) return
      const streamMsg = this._messageForTurn(id)
      if (this.activeStream?.turnId === id) this.activeStream.close?.()
      this._clearAnswerTimer(id)
      if (streamMsg && !streamMsg.done) {
        finalizeThinking(streamMsg.thinkingState)
        streamMsg.finishedAt ||= Date.now()
        streamMsg.cancelled = true
        streamMsg.phase = 'cancelled'
        streamMsg.answerBuffer = ''
        streamMsg.pendingResult = null
        streamMsg.pendingRecommendedQuestions = []
        streamMsg.done = true
        if (visible && !streamMsg.answerText && !streamMsg.result) streamMsg.answerText = '已停止生成'
      }
      this.activeTurnId = null
      this.activeStream = null
      this.responding = false
    },
    stopStream() {
      this.disposeActiveTurn({ visible: true })
    },
    disposeReportStreams() {
      for (const stream of reportStreams.values()) stream.controller.abort()
      reportStreams.clear()
      this.activeReportCount = 0
    },
    // 主对话：经我方 /ir/chat/diag 流式接入中台。前端不做参数解析/校验，原样发送。
    async sendAndCalculate(text) {
      if (this.responding) return
      const content = String(text || '').trim()
      if (!content) return

      this._pushUser(content)
      const epoch = this.conversationEpoch
      const pendingStreamMsg = createStreamMessage()
      const currentTurnId = pendingStreamMsg.turnId
      this.messages.push(pendingStreamMsg)
      const streamMsg = this._messageForTurn(currentTurnId)
      if (!streamMsg) return
      this.activeTurnId = currentTurnId
      this.responding = true

      await new Promise((resolve) => {
        let resolved = false
        const resolveOnce = () => {
          if (resolved) return
          resolved = true
          resolve()
        }
        const releaseAndResolve = () => {
          this._releaseTurn(currentTurnId)
          resolveOnce()
        }
        const fail = (message) => {
          if (!this._isCurrentTurn(currentTurnId, epoch)) {
            resolveOnce()
            return
          }
          this._failTurn(streamMsg, message)
          resolveOnce()
        }
        const completeSuccess = () => {
          if (!this._isCurrentTurn(currentTurnId, epoch) || streamMsg.doneReceived) return
          streamMsg.doneReceived = true
          streamMsg.finishedAt = Date.now()
          streamMsg.phase = 'typing'
          finalizeThinking(streamMsg.thinkingState)
          this._showPendingResult(streamMsg, epoch)
          const recommendations = streamMsg.pendingRecommendedQuestions
          streamMsg.pendingRecommendedQuestions = Array.isArray(recommendations) ? recommendations : []
          this._startAnswerTyping(streamMsg, epoch)
          resolveOnce()
        }

        const handle = openChatStream(
          '/ir/chat/diag',
          { message: content, conversation_id: this.conversationId || undefined },
          {
            onOpen: ({ conversationId }) => {
              if (!this._isCurrentTurn(currentTurnId, epoch)) return
              if (conversationId && !this.conversationId) this.conversationId = conversationId
            },
            onEvent: (e) => {
              if (!this._isCurrentTurn(currentTurnId, epoch)) return
              const data = e.data && typeof e.data === 'object' ? e.data : {}
              const inner = data.data && typeof data.data === 'object' ? data.data : {}

              switch (e.type) {
                case 'session_start':
                  break
                case 'thinking':
                  streamMsg.hasThinkingStarted = true
                  applyThinkingFrame(streamMsg.thinkingState, e.id, inner)
                  break
                case 'answer':
                  this._applyAnswerEvent(streamMsg, inner, epoch).catch((error) => {
                    if (this._isCurrentTurn(currentTurnId, epoch)) fail(error?.message || '测算结果读取失败')
                  })
                  break
                case 'recommended_questions':
                  streamMsg.pendingRecommendedQuestions = inner.recommended_questions || []
                  break
                case 'error':
                  fail(data.msg || inner.message || '对话出错')
                  break
                case 'done':
                  if (Array.isArray(inner.suggestions) && inner.suggestions.length) {
                    streamMsg.pendingRecommendedQuestions = inner.suggestions
                  }
                  completeSuccess()
                  break
                default:
                  break
              }
            },
            onComplete: ({ reason }) => {
              if (!this._isCurrentTurn(currentTurnId, epoch)) {
                resolveOnce()
                return
              }
              if (reason === 'eof' && streamMsg.doneReceived) return
              if (reason === 'aborted') {
                releaseAndResolve()
                return
              }
              if (!streamMsg.doneReceived && !streamMsg.error) fail('连接已中断，请重试')
            },
          },
        )
        this.activeStream = { turnId: currentTurnId, close: handle.close }
      })
    },
    // 处理 answer：文本先缓冲；测算结果据 taskId 预取，done 后再展示。
    async _applyAnswerEvent(streamMsg, inner, epoch) {
      const answerText = inner.answer || ''
      if (answerText) streamMsg.answerBuffer += answerText

      const biz = Array.isArray(inner.biz) ? inner.biz : []
      const calcTool = biz.find((item) => item.tool === 'create_calculation_task')
      if (!calcTool) return

      const created = calcTool.payload?.data || {}
      if (created.conversationId && !this.conversationId && this.conversationEpoch === epoch) {
        this.conversationId = created.conversationId
      }
      if (!created.taskId || created.status !== 'completed') return
      if (streamMsg.handledTaskIds.includes(created.taskId)) return
      streamMsg.handledTaskIds.push(created.taskId)

      const resultResponse = await getCalculationResult(created.taskId)
      if (this.conversationEpoch !== epoch || streamMsg.cancelled || streamMsg.error) return
      const result = resultResponse.data || {}
      const version = created.version || result.version
      streamMsg.pendingResult = {
        result,
        entry: {
          conversationId: created.conversationId || this.conversationId,
          taskId: created.taskId,
          version,
          status: 'completed',
          result,
          input: created.input,
          calculatedAt: result.calculatedAt,
        },
      }
      this._showPendingResult(streamMsg, epoch)
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
        param_overrides: overrides,
      }, this.conversationId)
    },
    // 直调测算 + 统一进度展示：以「测算进行中」思考样式占位，完成后升级为结果卡片。
    async _submitAndTrack(payload, conversationId) {
      const epoch = this.conversationEpoch
      const pendingStreamMsg = createStreamMessage()
      const currentTurnId = pendingStreamMsg.turnId
      this.messages.push(pendingStreamMsg)
      const streamMsg = this._messageForTurn(currentTurnId)
      if (!streamMsg) return
      this.activeTurnId = currentTurnId
      this.activeStream = { turnId: currentTurnId, close: null }
      this.responding = true
      // 单节点进度占位（与思考链同款展示）
      applyThinkingFrame(streamMsg.thinkingState, '1', {
        node_id: 'recalc',
        node_seq: 0,
        node_title: '重新测算',
        node_status: 'active',
        node_subtitle: '正在按调整后的参数重新测算…',
      })
      try {
        const createdResponse = await createCalculationTask(payload, conversationId)
        if (!this._isCurrentTurn(currentTurnId, epoch)) return
        const created = createdResponse.data || {}
        if (created.conversationId) this.conversationId = created.conversationId

        const terminal = await this._waitForTerminal(created)
        if (!this._isCurrentTurn(currentTurnId, epoch)) return
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
        if (!this._isCurrentTurn(currentTurnId, epoch)) return
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
        streamMsg.phase = 'completed'
        streamMsg.finishedAt = Date.now()
        this.loadHistory().catch(() => {})
        if (result.basicInfo?.province) this.loadParamMeta(result.basicInfo.province).catch(() => {})
      } catch (error) {
        if (!this._isCurrentTurn(currentTurnId, epoch)) return
        applyThinkingFrame(streamMsg.thinkingState, '3', {
          node_id: 'recalc', node_status: 'aborted', node_subtitle: '测算失败',
        })
        finalizeThinking(streamMsg.thinkingState)
        streamMsg.error = error?.response?.data?.msg || error?.message
        streamMsg.answerText = failureText(streamMsg.error)
        streamMsg.done = true
        streamMsg.phase = 'error'
        streamMsg.finishedAt = Date.now()
      } finally {
        if (this.activeTurnId === currentTurnId) this._releaseTurn(currentTurnId)
      }
    },
    async generateReport(taskId) {
      if (!taskId) return null
      const active = reportStreams.get(taskId)
      if (active) return active.promise

      const epoch = this.conversationEpoch
      const pendingMessage = createReportStreamMessage(taskId)
      this.messages.push(pendingMessage)
      const progressMessage = this._messageForTurn(pendingMessage.turnId)
      if (!progressMessage) return null
      applyThinkingFrame(progressMessage.thinkingState, 1, {
        node_id: 'report:prepare',
        node_seq: 1,
        node_title: '读取冻结测算快照',
        node_status: 'active',
        node_subtitle: '正在准备正式报告…',
      })
      progressMessage.hasThinkingStarted = true

      const controller = new AbortController()
      let frameId = 1
      const isCurrent = () => (
        this.conversationEpoch === epoch
        && reportStreams.get(taskId)?.messageId === progressMessage.id
      )
      const applyStep = (step) => {
        if (!step || !isCurrent()) return
        const key = step.key || `step-${step.seq || frameId + 1}`
        frameId += 1
        applyThinkingFrame(progressMessage.thinkingState, frameId, {
          node_id: `report:${key}`,
          node_seq: Number.isFinite(step.seq) ? step.seq : frameId,
          node_title: step.title || '生成正式报告',
          node_status: reportStepStatus(step.state),
          node_subtitle: step.state === 'completed' ? '已完成' : step.state === 'failed' ? '执行失败' : '正在执行…',
        })
      }
      const finish = (report, failed = false) => {
        if (!isCurrent()) return
        for (const step of report.steps || []) applyStep(step)
        if (failed) {
          const activeNode = thinkingNodes(progressMessage.thinkingState).find((node) => node.status === 'active')
          if (activeNode) {
            frameId += 1
            applyThinkingFrame(progressMessage.thinkingState, frameId, {
              node_id: activeNode.nodeId,
              node_status: 'aborted',
              node_subtitle: '报告生成失败',
            })
          }
        }
        finalizeThinking(progressMessage.thinkingState)
        progressMessage.finishedAt = Date.now()
        progressMessage.phase = failed ? 'error' : 'completed'
        progressMessage.error = failed ? (report.error?.message || '报告生成失败') : null
        progressMessage.answerText = failed
          ? `报告生成失败：${progressMessage.error}`
          : '正式报告已生成，可查看完整报告。'
        progressMessage.reportId = report.reportId || null
        progressMessage.payload = report.reportId
          ? { event_type: 'report_generated', report_id: report.reportId, task_id: taskId }
          : null
        progressMessage.done = true
      }

      const promise = (async () => {
        try {
          const created = (await createReport(taskId)).data || {}
          if (!isCurrent()) return null
          progressMessage.reportTaskId = created.reportTaskId || null
          progressMessage.steps = created.steps || []
          for (const step of progressMessage.steps) applyStep(step)

          if (created.status === 'completed') {
            const report = { ...created, taskId, status: 'completed' }
            this._applyReport(report)
            finish(report)
            this.syncReportsFromConversation().catch(() => {})
            return report
          }

          this.reportTasks[created.reportTaskId] = created
          this._applyReport({ taskId, reportTaskId: created.reportTaskId, status: 'generating', steps: created.steps || [] })
          await streamReportEvents(created.reportTaskId, {
            signal: controller.signal,
            onEvent: ({ type, data }) => {
              if (!isCurrent()) return
              if (type === 'complete' || type === 'failed') {
                this._applyReport(data)
                progressMessage.steps = data.steps || progressMessage.steps
                finish(data, type === 'failed')
                if (type === 'complete' && data.reportId) this.syncReportsFromConversation().catch(() => {})
                return
              }
              const steps = [...(this.reportTasks[created.reportTaskId]?.steps || []), data]
              this.reportTasks[created.reportTaskId] = { ...this.reportTasks[created.reportTaskId], steps }
              progressMessage.steps = steps
              applyStep(data)
            },
          })
          return this.reportTasks[created.reportTaskId]
        } catch (error) {
          if (!isCurrent() || error?.name === 'AbortError') return null
          try {
            const recovered = (await getReportTask(progressMessage.reportTaskId)).data || {}
            if (!isCurrent()) return null
            this._applyReport(recovered)
            progressMessage.steps = recovered.steps || progressMessage.steps
            if (recovered.status === 'completed') {
              finish(recovered)
              this.syncReportsFromConversation().catch(() => {})
            } else {
              finish({ ...recovered, error: recovered.error || { message: error?.message } }, true)
            }
            return recovered
          } catch (recoveryError) {
            if (isCurrent()) finish({ error: { message: recoveryError?.message || error?.message } }, true)
            return null
          }
        } finally {
          const current = reportStreams.get(taskId)
          if (current?.messageId === progressMessage.id) {
            reportStreams.delete(taskId)
            this.activeReportCount = reportStreams.size
          }
        }
      })()

      reportStreams.set(taskId, { controller, messageId: progressMessage.id, promise })
      this.activeReportCount = reportStreams.size
      return promise
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

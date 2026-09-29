import { defineStore } from 'pinia'
import {
  createCalculationTask,
  deleteConversation,
  getCalculationResult,
  getCalculationInputs,
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
import { useTrialQuotaStore } from '@/store/modules/trialQuota'
import {
  downloadSpotContextTemplate,
  prepareSpotContext,
  removeSpotContext,
} from '@/api/spotContext'
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
const STATION_PAGE_SIZE = 30
const STATION_CACHE_TTL = 30 * 1000

function isCancelledRequest(error) {
  return error?.code === 'ERR_CANCELED' || error?.name === 'AbortError'
}

function uniqueStations(items, selectedNode) {
  const values = selectedNode ? [selectedNode, ...items] : items
  return [...new Set(values.filter(Boolean))]
}

function pruneStationCache(cache) {
  const now = Date.now()
  for (const [key, entry] of cache) {
    if (now - entry.savedAt >= STATION_CACHE_TTL) cache.delete(key)
  }
}

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

function failureText(message) {
  const text = String(message || '').trim()
  if (/飞书|feishu|server\s*error|95201/i.test(text)) {
    return '测算失败：测算服务暂时不可用，请稍后重试'
  }
  return `测算失败：${text || '未知错误'}`
}

function chatErrorMessage(data, inner) {
  return inner.response?.msg
    || inner.response?.message
    || data.msg
    || inner.message
    || '对话出错'
}

export const useCalculationStore = defineStore('calculation', {
  state: () => ({
    messages: [],
    versions: [],
    history: [],
    historyCursor: null,
    historyHasMore: false,
    historyLoading: false,
    historyRequestSequence: 0,
    conversationId: null,
    selectedVersion: null,
    comparisonVersionByVersion: {},
    responding: false,
    paramDict: [],
    switches: {},
    stationOptions: [],
    stationProvince: '',
    stationKeyword: '',
    stationCursor: null,
    stationHasMore: false,
    stationLoading: false,
    stationError: '',
    stationRequestSequence: 0,
    stationController: null,
    stationCache: new Map(),
    stationInflight: new Map(),
    reports: [],
    reportTasks: {},
    activeReportCount: 0,
    activeStream: null,
    activeTurnId: null,
    conversationEpoch: 0,
    historyOpenEpoch: 0,
    conversationDetailCache: new Map(),
    conversationDetailInflight: new Map(),
    conversationDetailGenerations: new Map(),
    conversationDetailCacheEpoch: 0,
    taskInputCache: new Map(),
    taskInputInflight: new Map(),
    taskInputLoading: {},
    taskInputErrors: {},
    taskInputEpoch: 0,
    conversationLoading: false,
    conversationLoadingId: null,
    conversationLoadError: '',
    spotContext: null,
    spotContextToken: null,
    spotContextUploading: false,
    spotContextProgress: null,
    spotContextError: '',
    spotContextRequestSequence: 0,
    spotContextController: null,
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
      this.taskInputEpoch += 1
      this.taskInputLoading = {}
      this.taskInputErrors = {}
      this.messages = []
      this.versions = []
      this.conversationId = null
      this.selectedVersion = null
      this.comparisonVersionByVersion = {}
      this.responding = false
      this.resetStationQuery()
      this.reports = []
      this.reportTasks = {}
      this.activeReportCount = 0
      this.conversationLoading = false
      this.conversationLoadingId = null
      this.conversationLoadError = ''
      const stagedToken = this.spotContextToken
      this.spotContextController?.abort()
      this.spotContextRequestSequence += 1
      this.spotContextController = null
      this.spotContext = null
      this.spotContextToken = null
      this.spotContextUploading = false
      this.spotContextProgress = null
      this.spotContextError = ''
      if (stagedToken) removeSpotContext({ contextToken: stagedToken }).catch(() => {})
    },
    invalidateConversationDetail(conversationId) {
      if (conversationId == null) return
      const key = String(conversationId)
      this.conversationDetailCache.delete(key)
      this.conversationDetailGenerations.set(
        key,
        (this.conversationDetailGenerations.get(key) || 0) + 1,
      )
      this.conversationDetailInflight.delete(key)
    },
    clearConversationDetailCache() {
      this.conversationDetailCacheEpoch += 1
      this.conversationDetailCache.clear()
      this.conversationDetailInflight.clear()
      this.conversationDetailGenerations.clear()
    },
    async loadConversationDetail(conversationId, { force = false } = {}) {
      const key = String(conversationId)
      if (!force && this.conversationDetailCache.has(key)) {
        return this.conversationDetailCache.get(key)
      }
      const generation = this.conversationDetailGenerations.get(key) || 0
      const cacheEpoch = this.conversationDetailCacheEpoch
      const active = this.conversationDetailInflight.get(key)
      if (active && active.generation === generation && active.cacheEpoch === cacheEpoch) {
        return active.promise
      }
      const promise = getConversation(key).then((response) => {
        const detail = response.data || {}
        if (
          this.conversationDetailCacheEpoch === cacheEpoch
          && (this.conversationDetailGenerations.get(key) || 0) === generation
        ) this.conversationDetailCache.set(key, detail)
        return detail
      })
      this.conversationDetailInflight.set(key, { generation, cacheEpoch, promise })
      // 失败不缓存：按 promise 身份清理在途记录，避免下次打开复用已 reject 的 promise。
      // 不能按 entry 对象比较——Pinia state 中读回的是响应式代理，与原对象永不全等。
      promise.finally(() => {
        if (this.conversationDetailInflight.get(key)?.promise === promise) {
          this.conversationDetailInflight.delete(key)
        }
      }).catch(() => {})
      return promise
    },
    _hydrateTaskInput(taskId, inputData) {
      const key = String(taskId)
      const entry = this.versions.find((item) => String(item.taskId) === key)
      if (entry) {
        entry.input = inputData.input || {}
        entry.changeMeta = inputData.changeMeta || entry.changeMeta || {}
      }
      for (const message of this.messages) {
        if (String(message.taskId) !== key) continue
        message.input = inputData.input || {}
        message.changeMeta = inputData.changeMeta || message.changeMeta || {}
      }
    },
    async ensureTaskInput(taskId, { force = false } = {}) {
      const results = await this.ensureTaskInputs([taskId], { force })
      return results[String(taskId)] || null
    },
    async ensureTaskInputs(taskIds, { force = false } = {}) {
      const keys = [...new Set((taskIds || [])
        .map((taskId) => String(taskId))
        .filter((key) => key && key !== 'undefined' && key !== 'null'))]
      if (!keys.length) return {}

      const results = {}
      const pending = []
      const requestKeys = []
      const epoch = this.taskInputEpoch
      for (const key of keys) {
        // force 只用于失败/缺失项重试；已有成功缓存始终复用，避免重试时连带刷新其它版本。
        if (this.taskInputCache.has(key) && (!force || !this.taskInputErrors[key])) {
          const cached = this.taskInputCache.get(key)
          this._hydrateTaskInput(key, cached)
          delete this.taskInputErrors[key]
          results[key] = cached
          continue
        }
        const active = this.taskInputInflight.get(key)
        if (active?.epoch === epoch) {
          pending.push(active.promise.then((input) => {
            if (input) results[key] = input
            return input
          }))
          continue
        }
        this.taskInputLoading[key] = true
        delete this.taskInputErrors[key]
        requestKeys.push(key)
      }

      if (requestKeys.length) {
        const batchPromise = getCalculationInputs(requestKeys.map((key) => Number(key)))
          .then((response) => {
            const items = response.data?.items || []
            const byKey = new Map(items.map((item) => [String(item.taskId), item]))
            const batchResults = {}
            for (const key of requestKeys) {
              const input = byKey.get(key)
              if (!input) {
                if (this.taskInputEpoch === epoch) this.taskInputErrors[key] = '参数加载失败'
                continue
              }
              batchResults[key] = input
              // 迟到响应不能把旧会话的输入写入缓存；当前会话成功后才允许缓存并回填。
              if (this.taskInputEpoch === epoch) {
                this.taskInputCache.set(key, input)
                this._hydrateTaskInput(key, input)
              }
            }
            return batchResults
          })
          .catch((error) => {
            if (this.taskInputEpoch === epoch) {
              for (const key of requestKeys) {
                this.taskInputErrors[key] = error?.response?.data?.msg
                  || error?.message || '参数加载失败'
              }
            }
            throw error
          })
        for (const key of requestKeys) {
          const taskPromise = batchPromise.then((batchResults) => {
            const input = batchResults[key] || null
            if (input) results[key] = input
            return input
          })
          this.taskInputInflight.set(key, { epoch, promise: taskPromise })
          pending.push(taskPromise)
          taskPromise.finally(() => {
            if (this.taskInputInflight.get(key)?.promise === taskPromise) {
              this.taskInputInflight.delete(key)
            }
            if (this.taskInputEpoch === epoch) this.taskInputLoading[key] = false
          }).catch(() => {})
        }
      }

      await Promise.all(pending)
      return results
    },
    selectVersion(version) {
      if (this.versions.some((item) => item.version === version)) this.selectedVersion = version
    },
    comparisonVersionFor(currentVersion) {
      const currentIndex = this.versions.findIndex((item) => item.version === currentVersion)
      if (currentIndex <= 0) return null
      const selected = this.comparisonVersionByVersion[currentVersion]
      const selectedIndex = this.versions.findIndex((item) => item.version === selected)
      return selectedIndex >= 0 && selectedIndex < currentIndex
        ? selected
        : this.versions[currentIndex - 1].version
    },
    selectComparisonVersion(currentVersion, compareVersion) {
      const currentIndex = this.versions.findIndex((item) => item.version === currentVersion)
      const compareIndex = this.versions.findIndex((item) => item.version === compareVersion)
      if (currentIndex <= 0 || compareIndex < 0 || compareIndex >= currentIndex) return
      this.comparisonVersionByVersion[currentVersion] = compareVersion
    },
    async loadHistory() {
      const sequence = ++this.historyRequestSequence
      this.historyLoading = true
      try {
        const response = await listConversations()
        if (sequence !== this.historyRequestSequence) return
        this.history = response.data?.items || []
        this.historyCursor = response.data?.nextCursor || null
        this.historyHasMore = !!this.historyCursor
      } finally {
        if (sequence === this.historyRequestSequence) this.historyLoading = false
      }
    },
    async loadMoreHistory() {
      if (!this.historyCursor || this.historyLoading) return
      const cursor = this.historyCursor
      const sequence = this.historyRequestSequence
      this.historyLoading = true
      try {
        const response = await listConversations(cursor)
        if (sequence !== this.historyRequestSequence || cursor !== this.historyCursor) return
        const items = response.data?.items || []
        this.history.push(...items)
        this.historyCursor = response.data?.nextCursor || null
        this.historyHasMore = !!this.historyCursor
      } finally {
        if (sequence === this.historyRequestSequence) this.historyLoading = false
      }
    },
    resetStationQuery() {
      this.stationController?.abort()
      this.stationRequestSequence += 1
      this.stationController = null
      this.stationProvince = ''
      this.stationKeyword = ''
      this.stationCursor = null
      this.stationHasMore = false
      this.stationLoading = false
      this.stationError = ''
      this.stationOptions = []
    },
    async loadParamMeta(province) {
      if (!province) return
      const paramResponse = await getParamDict(province)
      this.paramDict = paramResponse.data?.parameters || []
      this.switches = paramResponse.data?.switches || {}
    },
    async searchStations({ province, keyword = '', selectedNode = null } = {}) {
      if (!province) return
      const normalizedKeyword = String(keyword || '').trim()
      const queryKey = JSON.stringify([province, normalizedKeyword, null])
      pruneStationCache(this.stationCache)
      if (
        this.stationLoading
        && this.stationProvince === province
        && this.stationKeyword === normalizedKeyword
      ) return this.stationInflight.get(queryKey)

      this.stationController?.abort()
      const sequence = ++this.stationRequestSequence
      const controller = new AbortController()
      this.stationController = controller
      const isRepeatQuery = this.stationProvince === province && this.stationKeyword === normalizedKeyword
      this.stationProvince = province
      this.stationKeyword = normalizedKeyword
      this.stationCursor = null
      this.stationHasMore = false
      this.stationLoading = true
      this.stationError = ''
      this.stationOptions = isRepeatQuery
        ? uniqueStations(this.stationOptions, selectedNode)
        : uniqueStations([], selectedNode)

      try {
        const cached = this.stationCache.get(queryKey)
        let promise
        if (cached && Date.now() - cached.savedAt < STATION_CACHE_TTL) {
          promise = Promise.resolve(cached.page)
        } else {
          promise = this.stationInflight.get(queryKey)
          if (!promise) {
            promise = getStations({
              province,
              keyword: normalizedKeyword,
              limit: STATION_PAGE_SIZE,
              signal: controller.signal,
            }).then((response) => response.data || {})
            this.stationInflight.set(queryKey, promise)
            promise.finally(() => {
              if (this.stationInflight.get(queryKey) === promise) this.stationInflight.delete(queryKey)
            }).catch(() => {})
          }
        }
        const page = await promise
        if (sequence !== this.stationRequestSequence) return
        this.stationCache.set(queryKey, { savedAt: Date.now(), page })
        const pageStations = isRepeatQuery
          ? [...this.stationOptions, ...(page.items || [])]
          : (page.items || [])
        this.stationOptions = uniqueStations(pageStations, selectedNode)
        this.stationCursor = page.nextCursor || null
        this.stationHasMore = !!page.hasMore
      } catch (error) {
        if (sequence !== this.stationRequestSequence || isCancelledRequest(error)) return
        this.stationError = error?.response?.data?.msg || error?.message || '节点加载失败'
        this.stationOptions = uniqueStations([], selectedNode)
      } finally {
        if (sequence === this.stationRequestSequence) {
          this.stationLoading = false
          if (this.stationController === controller) this.stationController = null
        }
      }
    },
    async loadMoreStations({ selectedNode = null } = {}) {
      if (!this.stationProvince || !this.stationHasMore || !this.stationCursor || this.stationLoading) return
      const province = this.stationProvince
      const keyword = this.stationKeyword
      const cursor = this.stationCursor
      const queryKey = JSON.stringify([province, keyword, cursor])
      pruneStationCache(this.stationCache)
      const sequence = this.stationRequestSequence
      const controller = new AbortController()
      this.stationController = controller
      this.stationLoading = true
      this.stationError = ''
      try {
        const cached = this.stationCache.get(queryKey)
        let promise
        if (cached && Date.now() - cached.savedAt < STATION_CACHE_TTL) {
          promise = Promise.resolve(cached.page)
        } else {
          promise = this.stationInflight.get(queryKey)
          if (!promise) {
            promise = getStations({
              province,
              keyword,
              cursor,
              limit: STATION_PAGE_SIZE,
              signal: controller.signal,
            }).then((response) => response.data || {})
            this.stationInflight.set(queryKey, promise)
            promise.finally(() => {
              if (this.stationInflight.get(queryKey) === promise) this.stationInflight.delete(queryKey)
            }).catch(() => {})
          }
        }
        const page = await promise
        if (sequence !== this.stationRequestSequence) return
        this.stationCache.set(queryKey, { savedAt: Date.now(), page })
        this.stationOptions = uniqueStations([...this.stationOptions, ...(page.items || [])], selectedNode)
        this.stationCursor = page.nextCursor || null
        this.stationHasMore = !!page.hasMore
      } catch (error) {
        if (sequence !== this.stationRequestSequence || isCancelledRequest(error)) return
        this.stationError = error?.response?.data?.msg || error?.message || '节点加载失败'
      } finally {
        if (sequence === this.stationRequestSequence) {
          this.stationLoading = false
          if (this.stationController === controller) this.stationController = null
        }
      }
    },
    _applyConversationDetail(detail, conversationId, targetTaskId = null) {
      // 会话标识以服务端快照为准，缓存键才做字符串归一，避免历史回放改变后续请求体的 id 类型
      const resolvedId = detail.conversationId != null ? detail.conversationId : conversationId
      const completed = (detail.versions || [])
      const completedByTaskId = new Map(
        completed.map((version) => [String(version.taskId), version]),
      )
      this.messages = (detail.messages || []).map((message) => {
        if (message.messageType === 'calculation_completed') {
          const version = completedByTaskId.get(String(message.payload?.task_id))
          if (version) {
            if (message.payload?.answer_text) {
              return {
                id: nextId(), role: 'assistant', kind: 'assistant-stream',
                phase: 'completed', done: true,
                answerText: message.payload.answer_text, taskId: version.taskId,
                version: version.version, result: version.card || version.result, input: version.input,
                changeMeta: version.changeMeta || {}, report: version.report,
                calculatedAt: version.calculatedAt,
              }
            }
            return {
              id: nextId(), role: 'assistant', kind: 'result', taskId: version.taskId,
              version: version.version, result: version.card || version.result, input: version.input,
              changeMeta: version.changeMeta || {}, report: version.report,
              calculatedAt: version.calculatedAt,
            }
          }
        }
        if (message.messageType === 'report_generated') {
          return { id: nextId(), role: message.role, kind: 'report-generated', text: message.content, payload: message.payload }
        }
        if (message.messageType === 'calculation_error') {
          return { id: nextId(), role: 'assistant', kind: 'assistant-stream', phase: 'error', done: true, error: message.content, answerText: message.content, taskId: message.payload?.task_id || null }
        }
        return { id: nextId(), role: message.role, kind: 'text', text: message.content }
      })
      this.versions = completed.map((version) => ({
        conversationId: resolvedId, taskId: version.taskId, version: version.version,
        status: version.status, result: version.card || version.result, input: version.input,
        changeMeta: version.changeMeta || {}, report: version.report,
        calculatedAt: version.calculatedAt,
      }))
      this.reports = detail.reports || []
      this.reportTasks = Object.fromEntries(
        [...this.reports, ...completed.map((version) => version.report)].filter(Boolean)
          .filter((report) => report.reportTaskId)
          .map((report) => [report.reportTaskId, report]),
      )
      this.conversationId = resolvedId
      this.spotContext = detail.spotContext || null
      this.spotContextToken = null
      this.spotContextError = ''
      const target = targetTaskId == null
        ? null
        : this.versions.find((version) => String(version.taskId) === String(targetTaskId))
      this.selectedVersion = target?.version || (this.versions.length ? this.versions[this.versions.length - 1].version : null)
      this.responding = false
      const latestResult = completed.length
        ? completed[completed.length - 1].card || completed[completed.length - 1].result
        : null
      const province = latestResult?.basicInfo?.province
      if (province) this.loadParamMeta(province).catch(() => {})
    },
    async openConversation(conversationId, targetTaskId = null) {
      const key = String(conversationId)
      const stagedToken = this.spotContextToken
      if (stagedToken) removeSpotContext({ contextToken: stagedToken }).catch(() => {})
      this.spotContext = null
      this.spotContextToken = null
      this.spotContextError = ''
      this.disposeActiveTurn({ visible: false })
      this.disposeReportStreams()
      const openEpoch = ++this.historyOpenEpoch
      const conversationEpoch = ++this.conversationEpoch
      // 切换历史会话时隔离仍在途的参数请求，避免迟到响应回填新会话。
      this.taskInputEpoch += 1
      this.taskInputLoading = {}
      this.taskInputErrors = {}
      this.conversationLoading = true
      this.conversationLoadingId = key
      this.conversationLoadError = ''
      try {
        const detail = await this.loadConversationDetail(key)
        if (openEpoch !== this.historyOpenEpoch || conversationEpoch !== this.conversationEpoch) return
        this._applyConversationDetail(detail, key, targetTaskId)
      } catch (error) {
        if (openEpoch === this.historyOpenEpoch && conversationEpoch === this.conversationEpoch) {
          this.conversationLoadError = error?.response?.data?.msg || error?.message || '历史会话加载失败'
        }
        throw error
      } finally {
        if (openEpoch === this.historyOpenEpoch) {
          this.conversationLoading = false
          this.conversationLoadingId = null
        }
      }
    },
    async removeConversation(conversationId) {
      await deleteConversation(conversationId)
      const key = String(conversationId)
      this.history = this.history.filter((item) => String(item.conversationId) !== key)
      this.invalidateConversationDetail(conversationId)
      if (String(this.conversationId) === key) this.resetConversation()
      await this.loadHistory()
    },
    async uploadSpotContext(upload = {}) {
      const file = upload instanceof File ? upload : upload?.file
      const priceMode = upload instanceof File ? 'both' : (upload?.priceMode || 'both')
      if (!file || this.responding || this.spotContextUploading || (
        this.conversationId && this.spotContext?.status === 'ready'
      )) return
      const sequence = ++this.spotContextRequestSequence
      this.spotContextController?.abort()
      const controller = new AbortController()
      this.spotContextController = controller
      this.spotContextUploading = true
      this.spotContextProgress = {
        phase: 'uploading',
        fileName: file.name,
        uploadPercent: 0,
        completedDays: 0,
        totalDays: 0,
        message: '正在上传电价文件',
      }
      this.spotContextError = ''
      try {
        const response = await prepareSpotContext(file, this.conversationId, controller.signal, {
          priceMode,
          onUploadProgress: (event) => {
            if (sequence !== this.spotContextRequestSequence) return
            const total = event.total || file.size || 0
            this.spotContextProgress = {
              ...this.spotContextProgress,
              phase: 'uploading',
              uploadPercent: total ? Math.min(100, Math.round((event.loaded / total) * 100)) : 0,
              message: '正在上传电价文件',
            }
          },
          onProgress: (event) => {
            if (sequence !== this.spotContextRequestSequence) return
            this.spotContextProgress = {
              ...this.spotContextProgress,
              ...event,
              fileName: file.name,
            }
          },
        })
        if (sequence !== this.spotContextRequestSequence) return
        this.spotContext = response.data || null
        this.spotContextToken = this.conversationId
          ? null
          : response.data?.contextToken || null
        if (this.conversationId) this.invalidateConversationDetail(this.conversationId)
      } catch (error) {
        if (sequence !== this.spotContextRequestSequence || isCancelledRequest(error)) return
        this.spotContextError = error?.response?.data?.msg || error?.message || '电价文件校验失败'
        throw error
      } finally {
        if (sequence === this.spotContextRequestSequence) {
          this.spotContextUploading = false
          this.spotContextProgress = null
          if (this.spotContextController === controller) this.spotContextController = null
        }
      }
    },
    clearSpotContextError() {
      this.spotContextError = ''
    },
    async cancelStagedSpotContext() {
      if (this.conversationId || !this.spotContextToken || this.spotContextUploading) return
      const token = this.spotContextToken
      try {
        await removeSpotContext({ contextToken: token })
        if (this.spotContextToken !== token) return
        this.spotContext = null
        this.spotContextToken = null
        this.spotContextError = ''
      } catch (error) {
        if (this.spotContextToken === token) {
          this.spotContextError = error?.response?.data?.msg || error?.message || '取消电价文件失败，请稍后重试'
        }
        throw error
      }
    },
    async downloadSpotContextTemplate() {
      const blob = await downloadSpotContextTemplate()
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = 'spot-price-template.xlsx'
      anchor.click()
      URL.revokeObjectURL(url)
    },
    async renameConversation(conversationId, title) {
      const cleaned = String(title || '').trim()
      if (!cleaned) return
      await renameConversation(conversationId, cleaned)
      const item = this.history.find((entry) => String(entry.conversationId) === String(conversationId))
      if (item) item.title = cleaned
      const cached = this.conversationDetailCache.get(String(conversationId))
      if (cached) cached.title = cleaned
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
      this.invalidateConversationDetail(entry.conversationId || this.conversationId)
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
      let expectedConversationId = this.conversationId
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
          {
            message: content,
            conversation_id: this.conversationId || undefined,
            ...(this.spotContextToken ? { spot_context_token: this.spotContextToken } : {}),
          },
          {
            onOpen: ({ conversationId }) => {
              if (!this._isCurrentTurn(currentTurnId, epoch)) return
              if (conversationId) {
                expectedConversationId = conversationId
                if (!this.conversationId) {
                  this.conversationId = conversationId
                  this.spotContextToken = null
                  this.loadHistory().catch(() => {})
                }
              }
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
                  this._applyAnswerEvent(streamMsg, inner, epoch, expectedConversationId).catch((error) => {
                    if (this._isCurrentTurn(currentTurnId, epoch)) {
                      fail(error?.message || '测算结果读取失败')
                    }
                  })
                  break
                case 'recommended_questions':
                  streamMsg.pendingRecommendedQuestions = inner.recommended_questions || []
                  break
                case 'question': {
                  const questionText = inner.question_text || inner.text || ''
                  if (questionText) streamMsg.answerBuffer += questionText
                  completeSuccess()
                  break
                }
                case 'error':
                  fail(chatErrorMessage(data, inner))
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
    async _applyAnswerEvent(streamMsg, inner, epoch, expectedConversationId) {
      const answerText = inner.answer || ''
      if (answerText) streamMsg.answerBuffer += answerText

      const biz = Array.isArray(inner.biz) ? inner.biz : []
      const calcTool = biz.find((item) => item.tool === 'create_calculation_task')
      if (!calcTool) return

      const created = calcTool.payload?.data || {}
      if (
        expectedConversationId
        && created.conversationId
        && expectedConversationId !== created.conversationId
      ) {
        throw new Error('会话标识不一致，测算结果未展示，请重试')
      }
      if (created.conversationId && !this.conversationId && this.conversationEpoch === epoch) {
        this.conversationId = created.conversationId
      }
      if (created.status === 'failed') {
        const failure = new Error(created.error?.message || '测算失败')
        failure.requestId = created.error?.requestId || created.requestId
        throw failure
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
          changeMeta: created.changeMeta || {},
          calculatedAt: result.calculatedAt,
        },
      }
      this._showPendingResult(streamMsg, epoch)
      useTrialQuotaStore().refresh()
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
      const latest = this.latestVersion
      if (!latest || (!latest.taskId && !latest.input)) return
      if (latest.taskId && !latest.input) await this.ensureTaskInput(latest.taskId)
      // 省份在会话内永久锁定：以最新成功版本的冻结入参为准，不允许调整面板改动
      const province = latest.input?.province
      if (!province) return
      const isHenan = ['河南', '河南省'].includes(String(province).trim())
      await this._submitAndTrack({
        province,
        capacity_mwh: basics.capacity_mwh,
        power_mw: basics.power_mw,
        ...(isHenan ? { city: basics.city || null } : {}),
        node_name: isHenan ? null : (basics.node_name || null),
        param_overrides: overrides,
        trigger: 'recalculate',
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
        if (
          conversationId
          && created.conversationId
          && String(conversationId) !== String(created.conversationId)
        ) {
          throw new Error('会话标识不一致，测算结果未展示，请重试')
        }
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
          streamMsg.answerText = failureText(error.message)
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
          changeMeta: created.changeMeta || {},
          calculatedAt: result.calculatedAt,
        }
        this.versions.push(entry)
        this.selectedVersion = version
        this.invalidateConversationDetail(created.conversationId || conversationId)
        applyThinkingFrame(streamMsg.thinkingState, '2', {
          node_id: 'recalc', node_status: 'completed', node_subtitle: '测算完成',
        })
        finalizeThinking(streamMsg.thinkingState)
        streamMsg.result = result
        streamMsg.version = version
        streamMsg.input = created.input
        streamMsg.changeMeta = created.changeMeta || {}
        streamMsg.calculatedAt = result.calculatedAt
        streamMsg.taskId = created.taskId
        streamMsg.done = true
        streamMsg.phase = 'completed'
        streamMsg.finishedAt = Date.now()
        this.loadHistory().catch(() => {})
        if (result.basicInfo?.province) this.loadParamMeta(result.basicInfo.province).catch(() => {})
        useTrialQuotaStore().refresh()
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
                if (type === 'complete' && data.reportId) {
                  this.syncReportsFromConversation().catch(() => {})
                  useTrialQuotaStore().refresh()
                }
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
      const conversationId = String(this.conversationId)
      const epoch = this.conversationEpoch
      const detail = await this.loadConversationDetail(conversationId, { force: true })
      if (String(this.conversationId) !== conversationId || this.conversationEpoch !== epoch) return
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
      this.invalidateConversationDetail(this.conversationId)
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

<template>
  <div class="ir-home" :class="{ 'ir-home--welcome': !hasConversation }">
    <!-- 中间：对话区 -->
    <section class="ir-home__chat">
      <div v-if="hasConversation" class="ir-home__toolbar">
        <button
          class="ir-home__ledger-trigger"
          type="button"
          data-tip="项目档案"
          aria-label="打开项目档案"
          aria-controls="ir-home-ledger"
          :aria-expanded="projectRailOpen"
          @click="projectRailOpen = true"
        >
          <Archive aria-hidden="true" />
          <span>项目档案</span>
        </button>
      </div>

      <!-- 欢迎态：全局 layout 承载背景；本页为一组居中的“测算启动区” -->
      <div v-if="!hasConversation" class="ir-welcome">
        <div class="ir-welcome__inner">
          <div class="ir-welcome__heading">
            <img class="ir-welcome__orb" :src="orbSrc" alt="" aria-hidden="true" />
            <h1 class="ir-welcome__hi">
              储能项目投资测算
            </h1>
          </div>
          <p class="ir-welcome__lead">
            用自然语言描述项目所在地、额定功率、储能容量等基本信息，AI 将自动识别测算条件、完善关键参数并分析投资收益。
          </p>

          <ChatComposer
            ref="composerRef"
            class="ir-welcome__composer"
            :responding="calc.responding"
            placeholder="例如：测算甘肃酒泉 200MW/800MWh 独立储能项目，运营期20年"
            @send="onSend"
            @stop="calc.stopStream"
          />

          <div class="ir-welcome__chips">
            <button
              v-for="eg in examples"
              :key="eg"
              class="ir-chip"
              :disabled="calc.responding"
              @click="fillComposer(eg)"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">
                <path d="M13 2 4 14h7l-1 8 9-12h-7z" stroke-linejoin="round" />
              </svg>
              <span>{{ eg }}</span>
            </button>
          </div>

          <p class="ir-welcome__flow" aria-label="测算流程">
            <template v-for="(step, index) in flowSteps" :key="step">
              <span v-if="index > 0" class="ir-welcome__flow-sep" aria-hidden="true">→</span>
              <span class="ir-welcome__flow-step">{{ step }}</span>
            </template>
          </p>

          <div class="ir-welcome__divider" aria-hidden="true" />

          <div class="ir-welcome__metrics" aria-label="平台概览">
            <div v-for="metric in metrics" :key="metric.label" class="ir-welcome__metric">
              <span class="ir-welcome__metric-icon" v-html="metric.icon" aria-hidden="true" />
              <span class="ir-welcome__metric-copy">
                <span class="ir-welcome__metric-label">{{ metric.label }}</span>
                <strong class="ir-welcome__metric-value xc-num">
                  {{ metric.value }}<em>{{ metric.unit }}</em>
                </strong>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 对话态：消息流 + 底部输入框 -->
      <template v-else>
        <div ref="scrollEl" class="ir-home__stream">
          <div
            v-for="m in calc.messages"
            :key="m.id"
            :ref="(element) => setMessageElement(m.id, element)"
            class="ir-msg"
            :class="[
              `ir-msg--${m.role}`,
              { 'ir-msg--selected-result': m.kind === 'result' && m.version === calc.selectedVersion },
            ]"
            :data-version="m.kind === 'result' ? m.version : undefined"
            :data-task-id="m.taskId || undefined"
          >
            <img
              v-if="m.role === 'assistant'"
              class="ir-msg__avatar ir-msg__avatar--ai"
              :src="agentAvatar"
              alt=""
              aria-hidden="true"
            />
            <div v-if="m.role === 'user' && m.kind === 'text'" class="ir-msg__bubble">
              <span :class="{ 'ir-msg__pending': m.text === '测算中…' }">{{ m.text }}</span>
            </div>
            <AiAnswerContent
              v-else-if="m.role === 'assistant' && m.kind === 'text'"
              :text="m.text"
              :error="Boolean(m.error)"
            />
            <div v-else-if="m.kind === 'assistant-stream'" class="ir-msg__stream">
              <ThinkingChain
                :nodes="thinkingNodesOf(m)"
                :has-active="hasActiveThinkingOf(m)"
                :streaming="m.phase === 'streaming'"
                :bootstrapping="m.phase === 'streaming' && !m.hasThinkingStarted"
                :started-at="m.startedAt"
                :finished-at="m.finishedAt"
                :active-title="m.flow === 'report' ? '正在生成正式报告' : '正在深度推理'"
                :completed-title="m.flow === 'report' ? '报告生成完成' : '推理完成'"
                :bootstrapping-title="m.flow === 'report' ? '正在启动报告生成…' : '正在唤醒推理内核…'"
                :bootstrap-text="m.flow === 'report' ? '正在准备报告生成上下文…' : '正在准备分析上下文…'"
              />
              <ReportGenerationCard
                v-if="m.flow === 'report'"
                v-bind="reportCardProps(m)"
                @view="openReport"
                @view-history="jumpToReportRecord"
                @retry="generateReportAndReveal"
              />
              <AiAnswerContent v-else-if="m.answerText" :text="m.answerText" :error="Boolean(m.error)" />
              <div v-if="m.result" class="ir-msg__result">
                <ResultCard
                  :result="m.result"
                  :version="m.version"
                  :calculated-at="m.calculatedAt"
                  :seed-input="m.input || {}"
                  :comparison-input="comparisonInputFor(m.taskId)"
                  :display-comparison-input="displayComparisonFor(m.version)?.input"
                  :comparison-result="displayComparisonFor(m.version)?.result"
                  :comparison-version="calc.comparisonVersionFor(m.version) || ''"
                  :available-versions="availableComparisonVersions(m.version)"
                  :change-meta="comparisonChangeMetaFor(m.version)"
                  :param-dict="calc.paramDict"
                  :adjustable="m.version === calc.latestVersion?.version"
                  :switches="calc.switches"
                  :station-options="calc.stationOptions"
                  :station-loading="calc.stationLoading"
                  :station-has-more="calc.stationHasMore"
                  :station-error="calc.stationError"
                  :responding="calc.responding"
                  :report="calc.versions.find((item) => item.taskId === m.taskId)?.report"
                  :conversation-id="calc.conversationId || ''"
                  :task-id="m.taskId"
                  @recalculate="calc.recalculate($event)"
                  @station-open="calc.searchStations($event)"
                  @station-search="calc.searchStations($event)"
                  @station-load-more="calc.loadMoreStations($event)"
                  @generate-report="generateReportAndReveal(m.taskId)"
                  @compare-version-change="calc.selectComparisonVersion(m.version, $event)"
                />
              </div>
              <ul v-if="m.recommendedQuestions && m.recommendedQuestions.length" class="ir-msg__recommend">
                <li v-for="(q, qi) in m.recommendedQuestions" :key="qi">
                  <button type="button" :disabled="calc.responding" @click="onSend(q)">{{ q }}</button>
                </li>
              </ul>
            </div>
            <div v-else-if="m.kind === 'report-generated'" class="ir-msg__stream">
              <ReportGenerationCard
                v-bind="reportCardProps(m)"
                @view="openReport"
                @view-history="jumpToReportRecord"
                @retry="generateReportAndReveal"
              />
            </div>
            <div v-else-if="m.kind === 'result'" class="ir-msg__result">
              <!-- 调整参数并重新测算仅在最新版本卡片开放：
                   现货依赖比较/受控覆盖以“会话最新已完成版本”为基线，
                   在旧版本卡片上操作会与其自身展示值不一致，因此不提供入口 -->
              <ResultCard
                :result="m.result"
                :version="m.version"
                :calculated-at="m.calculatedAt"
                :seed-input="m.input || {}"
                :comparison-input="comparisonInputFor(m.taskId)"
                :display-comparison-input="displayComparisonFor(m.version)?.input"
                :comparison-result="displayComparisonFor(m.version)?.result"
                :comparison-version="calc.comparisonVersionFor(m.version) || ''"
                :available-versions="availableComparisonVersions(m.version)"
                :change-meta="comparisonChangeMetaFor(m.version)"
                :param-dict="calc.paramDict"
                :adjustable="m.version === calc.latestVersion?.version"
                :switches="calc.switches"
                :station-options="calc.stationOptions"
                :station-loading="calc.stationLoading"
                :station-has-more="calc.stationHasMore"
                :station-error="calc.stationError"
                :responding="calc.responding"
                :report="m.report || calc.versions.find((item) => item.taskId === m.taskId)?.report"
                :conversation-id="calc.conversationId || ''"
                :task-id="m.taskId"
                @recalculate="calc.recalculate($event)"
                @station-open="calc.searchStations($event)"
                @station-search="calc.searchStations($event)"
                @station-load-more="calc.loadMoreStations($event)"
                @generate-report="generateReportAndReveal(m.taskId)"
                @compare-version-change="calc.selectComparisonVersion(m.version, $event)"
              />
            </div>
            <img
              v-if="m.role === 'user'"
              class="ir-msg__avatar ir-msg__avatar--user"
              :src="userAvatar"
              alt=""
              aria-hidden="true"
            />
          </div>
        </div>

        <ChatComposer class="ir-home__composer" :responding="calc.responding" @send="onSend" @stop="calc.stopStream" />
      </template>
    </section>

    <!-- 右侧项目档案：桌面常驻，窄屏按需抽屉。 -->
    <div v-if="projectRailOpen" class="ir-home__ledger-backdrop" aria-hidden="true" @click="projectRailOpen = false" />
    <aside v-if="hasConversation" class="ir-home__side" :class="{ 'is-open': projectRailOpen }">
      <div id="ir-home-ledger" class="ir-home__ledger">
        <header class="ir-home__ledger-header">
          <h2>项目档案</h2>
          <button ref="ledgerCloseButton" class="ir-home__ledger-close" type="button" aria-label="关闭项目档案" @click="closeProjectRail">
            <X aria-hidden="true" />
          </button>
          <span class="ir-home__ledger-count xc-num">
            {{ reversedVersions.length }} 次测算 · {{ reversedReports.length }} 份报告
          </span>
        </header>

        <section class="ir-home__side-section ir-home__side-section--versions">
          <div class="ir-home__side-title">
            <span>测算记录</span>
            <span class="xc-num">{{ reversedVersions.length }}</span>
          </div>
          <div class="ir-home__side-scroll">
            <div v-if="!reversedVersions.length" class="ir-home__side-empty">暂无测算记录</div>
            <ul v-else class="ir-ver">
              <li
                v-for="v in reversedVersions"
                :key="v.version"
                class="ir-ver__item"
                :class="{ 'ir-ver__item--selected': v.version === calc.selectedVersion }"
                :data-sidebar-version="v.version"
              >
                <button
                  type="button"
                  class="ir-ver__select"
                  :aria-expanded="v.version === calc.selectedVersion"
                  @click="selectVersion(v.version)"
                >
                  <span class="ir-ver__node" aria-hidden="true" />
                  <span class="ir-ver__content">
                    <span class="ir-ver__row">
                      <span class="ir-ver__tag xc-num">{{ v.version }}</span>
                      <span v-if="v.version === calc.latestVersion?.version" class="ir-ver__latest">最新</span>
                      <span v-if="v.version !== calc.selectedVersion" class="ir-ver__cue">
                        查看结果
                        <svg viewBox="0 0 16 16" aria-hidden="true">
                          <path d="m6 3 5 5-5 5" />
                        </svg>
                      </span>
                    </span>
                    <span class="ir-ver__spec">{{ versionSpec(v) }}</span>
                    <span class="ir-ver__metric">
                      <span>项目全投资 IRR</span>
                      <strong class="xc-num">{{ formatNumber(v.result?.financial?.projectIrr) }}%</strong>
                    </span>
                    <span class="ir-ver__summary">
                      <strong>{{ archiveSummaryText(v) }}</strong>
                      <span>{{ archiveSummaryFields(v) }}</span>
                    </span>
                  </span>
                </button>
                <div v-if="v.version === calc.selectedVersion" class="ir-ver__actions">
                  <button
                    type="button"
                    class="ir-ver__report-action"
                    :disabled="v.report?.status === 'generating'"
                    @click="v.report?.status === 'completed' ? jumpToReportRecord(v.report.reportId) : generateReportAndReveal(v.taskId, true)"
                  >
                    {{ v.report?.status === 'completed' ? '跳转报告记录' : v.report?.status === 'generating' ? '报告生成中' : v.report?.status === 'failed' ? '重新生成报告' : '生成报告' }}
                    <svg v-if="v.report?.status !== 'generating'" viewBox="0 0 16 16" aria-hidden="true">
                      <path d="m6 3 5 5-5 5" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    class="ir-ver__share-action"
                    aria-label="分享此版本"
                    @click="openShareDialog(v)"
                  >
                    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
                      <path d="M4 11v2a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-2" stroke-linecap="round" stroke-linejoin="round" />
                      <path d="m10 5-2-2-2 2" stroke-linecap="round" stroke-linejoin="round" />
                      <path d="M8 3v7" stroke-linecap="round" />
                    </svg>
                    分享
                  </button>
                </div>
              </li>
            </ul>
          </div>
        </section>

        <section class="ir-home__side-section ir-home__side-section--reports">
          <div class="ir-home__side-title">
            <span>报告记录</span>
            <span class="xc-num">{{ reversedReports.length }}</span>
          </div>
          <div ref="reportListEl" class="ir-home__side-scroll">
            <div v-if="!reversedReports.length" class="ir-home__side-empty">暂无已生成报告</div>
            <ul v-else class="ir-report-list">
              <li
                v-for="report in reversedReports"
                :key="report.reportId"
                class="ir-report-list__item"
                :class="{ 'ir-report-list__item--highlighted': highlightedReportId === report.reportId }"
                :data-report-id="report.reportId"
              >
                <svg class="ir-report-list__icon" viewBox="0 0 20 20" aria-hidden="true">
                  <path d="M5 2.5h6l4 4v11H5z" />
                  <path d="M11 2.5v4h4M7.5 10h5M7.5 13h5" />
                </svg>
                <span class="ir-report-list__body">
                  <strong>{{ report.title || '正式报告' }}</strong>
                  <span>关联测算 {{ report.version }}</span>
                  <time class="xc-num">{{ formatRecordTime(report.createdAt) }}</time>
                </span>
                <button type="button" class="ir-report-list__view" @click="openReport(report.reportId)">
                  查看报告
                  <svg viewBox="0 0 16 16" aria-hidden="true"><path d="m6 3 5 5-5 5" /></svg>
                </button>
              </li>
            </ul>
          </div>
        </section>
      </div>
    </aside>
  </div>

  <ShareDialog
    v-model:visible="shareDialogVisible"
    :conversation-id="calc.conversationId || ''"
    :task-id="shareDialogTaskId"
    :version="shareDialogVersion"
  />
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { Archive, X } from '@lucide/vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { useSessionStore } from '@/store/modules/session'
import { useCalculationStore } from '@/store/modules/calculation'
import { getPlatformStats } from '@/api/calc'
import ResultCard from './components/ResultCard.vue'
import ChatComposer from './components/ChatComposer.vue'
import ThinkingChain from './components/ThinkingChain.vue'
import AiAnswerContent from './components/AiAnswerContent.vue'
import ReportGenerationCard from './components/ReportGenerationCard.vue'
import ShareDialog from './components/ShareDialog.vue'
import { thinkingNodes, hasActiveNode } from '@/utils/thinkingChain'
import orbSrc from '@/assets/ai-sphere.png'
import agentAvatar from '@/assets/agent.png'
import userAvatar from '@/assets/user.png'
import { formatNumber } from '@/utils/formatNumber'
import { buildArchiveSummary } from '@/utils/versionComparison'
import {
  buildReportProjectName,
  buildReportTitle,
  buildVersionTitle,
  formatProjectLocation,
} from '@/utils/projectTitle'

const session = useSessionStore()
const route = useRoute()
const router = useRouter()
const calc = useCalculationStore()
const scrollEl = ref(null)
const reportListEl = ref(null)
const ledgerCloseButton = ref(null)
const highlightedReportId = ref(null)
const projectRailOpen = ref(false)
const shareDialogVisible = ref(false)
const shareDialogTaskId = ref(null)
const shareDialogVersion = ref('')
const messageElements = new Map()
let reportHighlightTimer
let scrollFrame
let scrollRetryTimer
let streamObserver

function closeProjectRail(restoreFocus = true) {
  projectRailOpen.value = false
  if (restoreFocus) nextTick(() => document.querySelector('.ir-home__ledger-trigger')?.focus())
}

function onProjectRailKeydown(event) {
  if (!projectRailOpen.value) return
  if (event.key === 'Escape') {
    event.preventDefault()
    closeProjectRail()
    return
  }
  if (event.key !== 'Tab') return

  const rail = document.getElementById('ir-home-ledger')
  const focusable = rail
    ? [...rail.querySelectorAll('button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])')]
    : []
  if (!focusable.length) return
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

watch(projectRailOpen, async (open) => {
  if (typeof document !== 'undefined') document.body.classList.toggle('is-project-rail-open', open)
  if (open) await nextTick(() => ledgerCloseButton.value?.focus())
})

onMounted(() => {
  window.addEventListener('keydown', onProjectRailKeydown)
  openRouteConversation()
})

async function openRouteConversation() {
  const query = route?.query || {}
  const conversationId = query.conversationId
  const targetTaskId = query.taskId == null ? null : String(query.taskId)
  const alreadySelected = targetTaskId == null
    ? Boolean(calc.conversationId === String(conversationId))
    : Boolean(calc.conversationId === String(conversationId)
      && calc.versions.some((version) => String(version.taskId) === targetTaskId)
      && calc.selectedVersion === calc.versions.find((version) => String(version.taskId) === targetTaskId)?.version)
  if (!conversationId || alreadySelected) return
  try {
    await calc.openConversation(String(conversationId), targetTaskId)
    await nextTick()
    if (targetTaskId) {
      const target = [...document.querySelectorAll('[data-task-id]')]
        .find((element) => element.dataset.taskId === targetTaskId)
      target?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  } catch (error) {
    ElMessage.error('打开指定测算记录失败，请稍后重试')
  }
}

onBeforeUnmount(() => {
  document.body.classList.remove('is-project-rail-open')
  window.removeEventListener('keydown', onProjectRailKeydown)
})

function setMessageElement(messageId, element) {
  if (element) messageElements.set(messageId, element)
  else messageElements.delete(messageId)
}

function autoScrollTarget() {
  const stream = scrollEl.value
  if (!stream) return null
  return Math.max(0, stream.scrollHeight - stream.clientHeight)
}

function applyAutoScroll() {
  const target = autoScrollTarget()
  if (target === null) return
  scrollEl.value.scrollTop = target
}

function scheduleAutoScroll() {
  cancelAnimationFrame(scrollFrame)
  scrollFrame = requestAnimationFrame(() => {
    applyAutoScroll()
    clearTimeout(scrollRetryTimer)
    scrollRetryTimer = setTimeout(applyAutoScroll, 60)
  })
}

function stopScrollAnchor() {
  cancelAnimationFrame(scrollFrame)
  scrollFrame = null
  clearTimeout(scrollRetryTimer)
  scrollRetryTimer = null
}

const conversationActive = computed(() => calc.responding || calc.hasActiveReportGeneration)

function startScrollAnchor() {
  stopScrollAnchor()
  const tick = () => {
    applyAutoScroll()
    if (conversationActive.value) scrollFrame = requestAnimationFrame(tick)
  }
  scrollFrame = requestAnimationFrame(tick)
}

watch(conversationActive, async (active) => {
  await nextTick()
  if (active) startScrollAnchor()
  else stopScrollAnchor()
}, { flush: 'post' })

watch(scrollEl, (element) => {
  streamObserver?.disconnect()
  if (!element || typeof MutationObserver === 'undefined') return
  streamObserver = new MutationObserver(() => {
    if (conversationActive.value) scheduleAutoScroll()
  })
  streamObserver.observe(element, { childList: true, subtree: true, characterData: true })
}, { flush: 'post' })

onBeforeUnmount(() => {
  clearTimeout(reportHighlightTimer)
  stopScrollAnchor()
  streamObserver?.disconnect()
  messageElements.clear()
  calc.disposeActiveTurn({ visible: false })
  calc.disposeReportStreams()
})

const hasConversation = computed(() => calc.messages.length > 0)
const reversedVersions = computed(() => [...calc.versions].reverse())
const reversedReports = computed(() => calc.reports
  .filter((report) => report.status === 'completed' && report.reportId)
  .map((report, index) => ({ report, index, time: recordTimeValue(report.createdAt) }))
  .sort((a, b) => {
    if (a.time === null && b.time === null) return a.index - b.index
    if (a.time === null) return 1
    if (b.time === null) return -1
    return b.time - a.time || a.index - b.index
  })
  .map(({ report }) => report))

const examples = [
  '测算蒙西 100MW/200MWh 独立储能项目',
  '测算宁夏 100MW/400MWh 储能',
  '测算山西 2小时 独立储能',
]

const flowSteps = ['项目信息识别', '测算参数完善', '投资收益测算', '结果分析', '报告生成']

const platformStats = reactive({ calculationCount: 1286, projectCount: 128, reportCount: 256 })

// 欢迎态平台指标：固定值是历史基线，接口返回的真实使用量已在后端累加。
const metrics = computed(() => [
  {
    label: '累计测算次数', value: Number(platformStats.calculationCount).toLocaleString('zh-CN'), unit: '次',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M3 12h4l2 6 4-14 2 8h6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  },
  {
    label: '测算项目数', value: Number(platformStats.projectCount).toLocaleString('zh-CN'), unit: '个',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="m12 3 8 4.5-8 4.5-8-4.5L12 3Z"/><path d="M4 7.5V16l8 5 8-5V7.5"/><path d="M12 12v9"/></svg>',
  },
  {
    label: '生成报告', value: Number(platformStats.reportCount).toLocaleString('zh-CN'), unit: '份',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5M9 13h6M9 17h6" stroke-linecap="round"/></svg>',
  },
  {
    label: '可调测算参数', value: '20+', unit: '项',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h7M15 18h5" stroke-linecap="round"/><circle cx="15" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="13" cy="18" r="2"/></svg>',
  },
  {
    label: '覆盖省份', value: '28', unit: '个',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></svg>',
  },
])

async function refreshPlatformStats() {
  try {
    const response = await getPlatformStats()
    const data = response?.data?.data || response?.data || {}
    for (const key of ['calculationCount', 'projectCount', 'reportCount']) {
      if (Number.isFinite(Number(data[key]))) platformStats[key] = Number(data[key])
    }
  } catch {
    // 统计接口不可用时保留历史基线，不影响首页主流程。
  }
}

onMounted(refreshPlatformStats)

const composerRef = ref(null)

// 示例胶囊只把示例文案填入输入框并聚焦，不自动发送；用户检查补充后再发送。
function fillComposer(text) {
  const composer = composerRef.value
  if (composer && typeof composer.fill === 'function') composer.fill(text)
}

async function onSend(text) {
  const pending = calc.sendAndCalculate(text)
  await nextTick()
  scheduleAutoScroll()
  await pending
  await refreshPlatformStats()
}

async function generateReportAndReveal(taskId, fromProjectArchive = false) {
  if (fromProjectArchive) closeProjectRail(false)
  const pending = calc.generateReport(taskId)
  await nextTick()
  const reportMessage = [...calc.messages].reverse().find((message) => (
    message.flow === 'report' && message.taskId === taskId
  ))
  const messageTarget = messageElements.get(reportMessage?.id)
  if (typeof messageTarget?.scrollIntoView === 'function') {
    messageTarget.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } else {
    scheduleAutoScroll()
  }
  await pending
  await refreshPlatformStats()
}

function thinkingNodesOf(message) {
  return message.thinkingState ? thinkingNodes(message.thinkingState) : []
}

function hasActiveThinkingOf(message) {
  return message.thinkingState ? hasActiveNode(message.thinkingState) : false
}

async function selectVersion(version) {
  calc.selectVersion(version)
  closeProjectRail(false)
  await nextTick()
  const versionEntry = calc.versions.find((item) => item.version === version)
  const resultMessage = calc.messages.find((message) => (
    message.result
    && versionEntry?.taskId != null
    && message.taskId === versionEntry.taskId
  ))
  const stream = scrollEl.value
  const target = messageElements.get(resultMessage?.id)
  if (!stream || !target) return
  const top = stream.scrollTop + target.getBoundingClientRect().top - stream.getBoundingClientRect().top
  const bottom = Math.max(0, stream.scrollHeight - stream.clientHeight)
  stream.scrollTop = Math.max(0, Math.min(bottom, top))
}

function reportCardProps(message) {
  const reportId = message.reportId ?? message.payload?.report_id ?? null
  const taskId = message.taskId ?? message.payload?.task_id ?? null
  const report = calc.reports.find((item) => (
    (reportId && item.reportId === reportId) || (taskId && item.taskId === taskId)
  )) || null
  const linkedTaskId = taskId ?? report?.taskId ?? null
  const versionEntry = calc.versions.find((item) => item.taskId === linkedTaskId) || null
  const basic = versionEntry?.result?.basicInfo || {}
  const input = versionEntry?.input || {}
  const province = basic.province ?? input.province ?? ''
  const nodeName = basic.nodeName ?? input.nodeName ?? input.node_name ?? ''
  const power = basic.powerMw ?? input.powerMw ?? input.power_mw
  const capacity = basic.capacityMwh ?? input.capacityMwh ?? input.capacity_mwh
  const failed = message.phase === 'error' || Boolean(message.error) || report?.status === 'failed'
  const completed = message.kind === 'report-generated'
    || report?.status === 'completed'
    || Boolean(reportId)

  return {
    status: failed ? 'failed' : completed ? 'completed' : 'generating',
    reportId: reportId ?? report?.reportId ?? null,
    taskId: linkedTaskId,
    title: report?.title || buildReportTitle(province, nodeName, power, capacity),
    projectName: formatProjectLocation(province, nodeName)
      ? buildReportProjectName(province, nodeName, power, capacity)
      : '储能投资项目',
    version: report?.version || versionEntry?.version || '',
    powerText: power === null || power === undefined ? '—' : `${formatNumber(power)} MW`,
    capacityText: capacity === null || capacity === undefined ? '—' : `${formatNumber(capacity)} MWh`,
    errorMessage: message.error || report?.error?.message || '',
    archived: Boolean(report?.reportId),
  }
}

function openReport(reportId) {
  if (!reportId) return
  const { href } = router.resolve({ name: 'ReportDetail', params: { reportId } })
  if (!window.open(href, '_blank')) {
    ElMessage.warning('浏览器阻止了新标签页，请允许弹窗后重试')
  }
}

async function jumpToReportRecord(reportId) {
  closeProjectRail(false)
  await nextTick()
  const reportMessage = calc.messages.find((message) => (
    (message.flow === 'report' || message.kind === 'report-generated')
    && (message.reportId ?? message.payload?.report_id) === reportId
  ))
  const reportTaskId = calc.reports.find((report) => report.reportId === reportId)?.taskId
  const taskMessage = reportMessage || calc.messages.find((message) => (
    (message.flow === 'report' || message.kind === 'report-generated')
    && reportTaskId != null
    && (message.taskId ?? message.payload?.task_id) === reportTaskId
  ))
  const messageTarget = messageElements.get(taskMessage?.id)
  if (typeof messageTarget?.scrollIntoView === 'function') {
    messageTarget.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const target = reportListEl.value?.querySelector(`[data-report-id="${reportId}"]`)
  if (!target) return
  target.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  highlightedReportId.value = reportId
  clearTimeout(reportHighlightTimer)
  reportHighlightTimer = setTimeout(() => { highlightedReportId.value = null }, 1600)
}

function formatRecordTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  const pad = (number) => String(number).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function recordTimeValue(value) {
  if (!value) return null
  const time = new Date(value).getTime()
  return Number.isNaN(time) ? null : time
}

function comparisonInputFor(taskId) {
  const index = calc.versions.findIndex((entry) => entry.taskId === taskId)
  return index > 0 ? calc.versions[index - 1]?.input || null : null
}

function versionEntryFor(version) {
  return calc.versions.find((entry) => entry.version === version) || null
}

function displayComparisonFor(version) {
  const compareVersion = calc.comparisonVersionFor(version)
  return compareVersion ? versionEntryFor(compareVersion) : null
}

function availableComparisonVersions(version) {
  const currentIndex = calc.versions.findIndex((entry) => entry.version === version)
  return currentIndex > 0
    ? calc.versions.slice(0, currentIndex).map((entry, index) => ({
      version: entry.version,
      isPrevious: index === currentIndex - 1,
    })).reverse()
    : []
}

function comparisonChangeMetaFor(version) {
  const currentIndex = calc.versions.findIndex((entry) => entry.version === version)
  const compareVersion = calc.comparisonVersionFor(version)
  const compareIndex = calc.versions.findIndex((entry) => entry.version === compareVersion)
  if (compareIndex < 0 || currentIndex <= compareIndex) return {}
  const latestSource = new Map()
  for (const entry of calc.versions.slice(compareIndex + 1, currentIndex + 1)) {
    for (const key of entry.changeMeta?.derivedChangedKeys || []) latestSource.set(key, 'derived')
    for (const key of entry.changeMeta?.explicitOverrideKeys || []) latestSource.set(key, 'explicit')
  }
  return {
    previousTaskId: calc.versions[compareIndex]?.taskId ?? null,
    explicitOverrideKeys: [...latestSource].filter(([, source]) => source === 'explicit').map(([key]) => key),
    derivedChangedKeys: [...latestSource].filter(([, source]) => source === 'derived').map(([key]) => key),
  }
}

function openShareDialog(v) {
  shareDialogTaskId.value = v.taskId
  shareDialogVersion.value = v.version
  shareDialogVisible.value = true
}

// 右侧测算记录条目摘要使用各版本冻结的地区、节点与规模
function versionSpec(v) {
  const b = v.result?.basicInfo || {}
  const input = v.input || {}
  const province = b.province ?? input.province ?? ''
  const nodeName = b.nodeName ?? input.nodeName ?? input.node_name ?? ''
  const power = b.powerMw ?? input.powerMw ?? input.power_mw
  const capacity = b.capacityMwh ?? input.capacityMwh ?? input.capacity_mwh
  return buildVersionTitle(province, nodeName, power, capacity)
}

function previousVersionFor(v) {
  const index = calc.versions.findIndex((entry) => entry.taskId === v.taskId)
  return index > 0 ? calc.versions[index - 1] : null
}

function archiveSummaryFor(v) {
  return buildArchiveSummary(v, previousVersionFor(v), calc.paramDict)
}

function archiveSummaryText(v) {
  const summary = archiveSummaryFor(v)
  if (summary.initial) return '首个测算版本'
  const parts = []
  if (summary.explicit.count) parts.push(`主动调整 ${summary.explicit.count} 项`)
  if (summary.derived.count) parts.push(`联动更新 ${summary.derived.count} 项`)
  return `较 ${summary.previousVersion}：${parts.length ? parts.join(' · ') : '参数未变化'}`
}

function archiveSummaryFields(v) {
  const summary = archiveSummaryFor(v)
  if (summary.initial) return '作为后续版本的初始参照'
  const labels = [...summary.explicit.labels, ...summary.derived.labels]
  return labels.length ? labels.join('、') : '同一组冻结参数重新测算'
}
</script>

<style scoped>
.ir-home {
  display: grid;
  grid-template-columns: minmax(0, 1fr) clamp(280px, 22vw, 340px);
  gap: var(--xc-space-6);
  height: 100%;
  padding: 0 var(--xc-gutter-x);
}
.ir-home--welcome {
  /* 首页沿用测算态的主内容列，右侧留白保持两种状态的输入框基准一致。 */
  grid-template-columns: minmax(0, 1fr) clamp(280px, 22vw, 340px);
}
.ir-home__chat {
  --ir-message-inset: 84px;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ---------- 欢迎态：全局 layout 承载背景；本页为一组居中的“测算启动区” ---------- */
.ir-welcome {
  position: relative;
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: stretch;
  min-height: 0;
  padding: var(--xc-space-6) 0 clamp(24px, 7vh, 96px);
  overflow: hidden;
}
/* 内容列宽度与对话态 composer 同档，两态输入框尺寸/左右边界保持一致 */
.ir-welcome__inner {
  position: relative;
  z-index: 1;
  width: calc(100% - 2 * var(--ir-message-inset));
  max-width: var(--xc-content-fluid);
  margin-inline: auto;
  display: flex;
  flex-direction: column;
  align-items: stretch;
}
.ir-welcome__heading {
  display: flex;
  align-items: center;
  gap: var(--xc-space-5);
  margin-bottom: var(--xc-space-3);
}
.ir-welcome__orb {
  flex: 0 0 auto;
  width: 48px;
  height: 48px;
  object-fit: contain;
  filter: drop-shadow(0 8px 32px rgba(110, 42, 255, 0.45));
  animation: ir-orb-float 7.5s ease-in-out infinite;
}
@keyframes ir-orb-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-3px); }
}
.ir-welcome__hi {
  margin: 0;
  max-width: 640px;
  color: var(--xc-text-strong);
  font-size: clamp(32px, 3.2vw, 46px);
  font-weight: var(--xc-fw-bold);
  line-height: var(--xc-lh-tight);
  letter-spacing: 0.5px;
}
.ir-welcome__lead {
  margin: 0 0 var(--xc-space-6);
  max-width: 640px;
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-lg);
  line-height: var(--xc-lh-normal);
}
.ir-welcome__composer {
  margin-bottom: var(--xc-space-4);
  padding: 0;
}
.ir-welcome__chips {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-start;
  gap: var(--xc-space-3);
  margin-bottom: var(--xc-space-6);
}
/* 测算流程：低对比单行步骤，不制卡；流程下用细线与平台指标分区 */
.ir-welcome__flow {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--xc-space-3);
  margin: 0 0 var(--xc-space-5);
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-xs);
  line-height: var(--xc-lh-normal);
}
.ir-welcome__flow-step { color: var(--xc-text-soft); }
.ir-welcome__flow-sep { color: var(--xc-text-faint); }
.ir-welcome__divider {
  width: 100%;
  height: 1px;
  margin-bottom: var(--xc-space-5);
  background: var(--xc-border-card);
}
/* 平台指标：紧凑信息带，图标/标签弱化，数字清晰，不作为页面主视觉 */
.ir-welcome__metrics {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 22px;
}
.ir-welcome__metric {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--xc-space-3);
}
.ir-welcome__metric-icon {
  flex: 0 0 auto;
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  color: var(--xc-accent-blue);
  opacity: 0.75;
}
.ir-welcome__metric-icon :deep(svg) { width: 18px; height: 18px; }
.ir-welcome__metric-copy {
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: var(--xc-space-2);
}
.ir-welcome__metric-label {
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-2xs);
  white-space: nowrap;
}
.ir-welcome__metric-value {
  color: var(--xc-text-strong);
  font-size: var(--xc-fs-md);
  font-weight: var(--xc-fw-bold);
  font-variant-numeric: tabular-nums;
}
.ir-welcome__metric-value em {
  margin-left: 2px;
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-2xs);
  font-style: normal;
  font-weight: var(--xc-fw-regular);
}

/* 对话态 */
.ir-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--xc-space-2);
  height: 32px;
  padding: 0 var(--xc-space-5);
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-full);
  background: var(--xc-surface-card);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-sm);
  cursor: pointer;
  transition: border-color var(--xc-dur-fast), color var(--xc-dur-fast);
}
.ir-chip:hover:not(:disabled) { border-color: var(--xc-border-accent); color: var(--xc-text-strong); }
.ir-chip:disabled { opacity: 0.5; cursor: default; }
.ir-chip svg { width: 15px; height: 15px; color: var(--xc-accent-blue); }

/* ---------- 对话态 ---------- */
.ir-home__stream {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  /* 为位于消息外侧 52px 的 32px 头像保留安全区。 */
  padding: var(--xc-space-8) var(--ir-message-inset) var(--xc-space-7);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--xc-space-7);
}
/* 消息宽度继续服从投研结果布局；右侧记录栏会自然压缩主列。 */
.ir-msg { position: relative; display: flex; width: 100%; max-width: var(--xc-content-fluid); }
.ir-msg--user { justify-content: flex-end; }
.ir-msg--assistant { justify-content: flex-start; }
.ir-msg__avatar {
  position: absolute;
  top: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
}
.ir-msg__avatar--ai { left: -52px; }
.ir-msg__avatar--user { right: -52px; }
/* 用户文本始终通过 Vue 插值安全展示，不参与 Markdown 渲染。 */
.ir-msg--user .ir-msg__bubble {
  max-width: 78%;
  padding: var(--xc-space-3) var(--xc-space-5);
  border-radius: var(--xc-radius-sm);
  font-size: var(--xc-fs-sm);
  line-height: 1.6;
  color: var(--xc-text-strong);
  background: var(--xc-surface-frosted);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.ir-msg__pending { color: var(--xc-text-mute); }
.ir-msg__result { width: 100%; }
.ir-msg__stream { width: 100%; min-width: 0; display: flex; flex-direction: column; gap: var(--xc-space-4); }
.ir-msg__error { color: var(--xc-status-danger); }
.ir-msg__recommend { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: var(--xc-space-2); }
.ir-msg__recommend button {
  padding: 4px var(--xc-space-4);
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-full);
  background: var(--xc-surface-card);
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-xs);
  cursor: pointer;
}
.ir-msg__recommend button:hover:not(:disabled) { border-color: var(--xc-border-accent); color: var(--xc-text-strong); }
.ir-msg__recommend button:disabled { opacity: 0.5; cursor: default; }
/* 版本选择只用于定位记录，不再给结果卡叠加一圈高亮框。 */
.ir-msg--selected-result .ir-msg__result {
  border-radius: var(--xc-radius-sm);
}
/* 对话态底部输入框：复用消息流的水平安全区，与 AI 回复和思考框同宽。 */
.ir-home__composer {
  width: calc(100% - 2 * var(--ir-message-inset));
  max-width: var(--xc-content-fluid);
  margin: 0 auto;
  padding: var(--xc-space-4) 0 var(--xc-space-6);
}
.ir-home__toolbar {
  display: none;
  flex: 0 0 auto;
  align-items: center;
  justify-content: flex-end;
  width: calc(100% - 2 * var(--ir-message-inset));
  max-width: var(--xc-content-fluid);
  min-height: 44px;
  margin: 0 auto;
  padding-top: var(--xc-space-2);
  border-bottom: 1px solid var(--xc-border-soft);
}

/* ---------- 右侧项目档案 ---------- */
.ir-home__side {
  min-height: 0;
  padding: var(--xc-space-6) 0;
}
.ir-home__ledger {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) minmax(136px, 0.48fr);
  overflow: hidden;
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-sm);
  background: var(--xc-surface-sider);
  box-shadow: var(--xc-shadow-glass);
  backdrop-filter: blur(var(--xc-blur-md));
  -webkit-backdrop-filter: blur(var(--xc-blur-md));
}
.ir-home__ledger-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--xc-space-3);
  padding: var(--xc-space-5);
  border-bottom: 1px solid var(--xc-border-soft);
}
.ir-home__ledger-header h2 {
  margin: 0;
  color: var(--xc-text-strong);
  font-size: var(--xc-fs-md);
  font-weight: var(--xc-fw-semi);
  letter-spacing: 0.02em;
}
.ir-home__ledger-count {
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-2xs);
  line-height: var(--xc-lh-normal);
  white-space: nowrap;
}
.ir-home__side-section {
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.ir-home__side-section--reports { border-top: 1px solid var(--xc-border-soft); }
.ir-home__side-scroll {
  min-height: 0;
  overflow-y: auto;
  padding: 0 var(--xc-space-4) var(--xc-space-4);
  scrollbar-gutter: stable;
}
.ir-home__side-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--xc-space-3);
  padding: var(--xc-space-4) var(--xc-space-5) var(--xc-space-3);
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-xs);
  font-weight: var(--xc-fw-medium);
}
.ir-home__side-title .xc-num { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.ir-home__side-empty {
  padding: var(--xc-space-4) var(--xc-space-2);
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-xs);
  line-height: var(--xc-lh-loose);
}

/* 版本顺序由左侧轨道表达，选中项才展开完整档案。 */
.ir-ver {
  position: relative;
  list-style: none;
  margin: 0;
  padding: 0 0 0 var(--xc-space-4);
  display: flex;
  flex-direction: column;
  gap: var(--xc-space-2);
}
.ir-ver::before {
  content: '';
  position: absolute;
  top: var(--xc-space-4);
  bottom: var(--xc-space-4);
  left: 5px;
  width: 1px;
  background: var(--xc-border-soft);
}
.ir-ver__item { position: relative; min-width: 0; }
.ir-ver__select {
  position: relative;
  width: 100%;
  min-height: 44px;
  display: block;
  padding: var(--xc-space-3) var(--xc-space-4);
  border: 1px solid transparent;
  border-radius: var(--xc-radius-sm);
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color var(--xc-dur-fast), background var(--xc-dur-fast), transform var(--xc-dur-fast);
}
.ir-ver__select:hover { border-color: var(--xc-border-soft); background: var(--xc-surface-card); }
.ir-ver__select:active { transform: translateY(1px); }
.ir-ver__select:focus-visible,
.ir-ver__report-action:focus-visible,
.ir-ver__share-action:focus-visible,
.ir-report-list__view:focus-visible {
  outline: 2px solid var(--xc-accent-blue);
  outline-offset: 2px;
}
.ir-ver__item--selected .ir-ver__select {
  border-color: var(--xc-border-accent);
  background: var(--xc-surface-control);
}
.ir-ver__node {
  position: absolute;
  top: var(--xc-space-5);
  left: calc(-1 * var(--xc-space-4) - 4px);
  z-index: 1;
  width: 9px;
  height: 9px;
  border: 2px solid var(--xc-border-strong);
  border-radius: var(--xc-radius-full);
  background: var(--xc-surface-base);
  transition: border-color var(--xc-dur-fast), background var(--xc-dur-fast), box-shadow var(--xc-dur-fast);
}
.ir-ver__item--selected .ir-ver__node {
  border-color: var(--xc-accent-blue);
  background: var(--xc-accent-blue);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--xc-accent-blue) 16%, transparent);
}
.ir-ver__content { min-width: 0; display: flex; flex-direction: column; gap: var(--xc-space-2); }
.ir-ver__row { display: flex; align-items: center; gap: var(--xc-space-2); min-width: 0; }
.ir-ver__tag {
  flex: 0 0 auto;
  color: var(--xc-accent-blue);
  font-size: var(--xc-fs-xs);
  font-weight: var(--xc-fw-semi);
}
.ir-ver__latest {
  flex: 0 0 auto;
  padding: 1px var(--xc-space-2);
  border-radius: var(--xc-radius-full);
  background: color-mix(in srgb, var(--xc-status-ok) 12%, transparent);
  color: var(--xc-status-ok);
  font-size: var(--xc-fs-2xs);
}
.ir-ver__cue {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-2xs);
  line-height: var(--xc-lh-normal);
  white-space: nowrap;
}
.ir-ver__cue svg,
.ir-ver__report-action svg,
.ir-report-list__view svg {
  width: 14px;
  height: 14px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.ir-ver__spec {
  min-width: 0;
  overflow: hidden;
  color: var(--xc-text-default);
  font-size: var(--xc-fs-xs);
  line-height: var(--xc-lh-normal);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ir-ver__metric {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--xc-space-3);
  margin-top: var(--xc-space-2);
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-2xs);
}
.ir-ver__metric strong {
  color: var(--xc-text-strong);
  font-family: var(--xc-font-num);
  font-size: var(--xc-fs-lg);
  font-weight: var(--xc-fw-semi);
  font-variant-numeric: tabular-nums;
}
.ir-ver__summary { min-width: 0; display: flex; flex-direction: column; gap: 2px; padding-top: var(--xc-space-2); border-top: 1px solid var(--xc-border-soft); font-size: var(--xc-fs-3xs); line-height: var(--xc-lh-normal); }
.ir-ver__summary strong { overflow: hidden; color: var(--xc-text-soft); font-weight: var(--xc-fw-medium); text-overflow: ellipsis; white-space: nowrap; }
.ir-ver__summary span { overflow: hidden; color: var(--xc-text-mute); text-overflow: ellipsis; white-space: nowrap; }
.ir-ver__time { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); line-height: var(--xc-lh-normal); }
.ir-ver__actions {
  width: calc(100% - var(--xc-space-4));
  margin: var(--xc-space-2) 0 var(--xc-space-2) var(--xc-space-4);
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(84px, 0.72fr);
  gap: var(--xc-space-2);
}
.ir-ver__report-action {
  width: 100%;
  min-height: 36px;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--xc-space-2);
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-sm);
  background: transparent;
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-xs);
  cursor: pointer;
  transition: border-color var(--xc-dur-fast), background var(--xc-dur-fast), color var(--xc-dur-fast);
}
.ir-ver__report-action:hover:not(:disabled) {
  border-color: var(--xc-border-accent);
  background: var(--xc-surface-control);
  color: var(--xc-text-strong);
}
.ir-ver__report-action:disabled { opacity: 0.5; cursor: not-allowed; }

.ir-ver__share-action {
  width: 100%;
  min-height: 36px;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--xc-space-2);
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-sm);
  background: transparent;
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-xs);
  cursor: pointer;
  transition: border-color var(--xc-dur-fast), background var(--xc-dur-fast), color var(--xc-dur-fast);
}
.ir-ver__share-action:hover:not(:disabled) {
  border-color: var(--xc-border-accent);
  background: var(--xc-surface-control);
  color: var(--xc-text-strong);
}
.ir-ver__share-action svg { width: 14px; height: 14px; flex-shrink: 0; }

/* 报告是版本产物，以文档行而非第二层卡片表达。 */
.ir-report-list { list-style: none; margin: 0; padding: 0; }
.ir-report-list__item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--xc-space-3);
  min-width: 0;
  padding: var(--xc-space-3) var(--xc-space-2);
  border-bottom: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-sm);
  transition: background var(--xc-dur-base), border-color var(--xc-dur-base);
}
.ir-report-list__item:last-child { border-bottom-color: transparent; }
.ir-report-list__item--highlighted {
  border-bottom-color: var(--xc-border-accent);
  background: color-mix(in srgb, var(--xc-accent-blue) 14%, transparent);
}
.ir-report-list__icon {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: var(--xc-accent-blue);
  stroke-width: 1.4;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.ir-report-list__body { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.ir-report-list__body strong {
  overflow: hidden;
  color: var(--xc-text-strong);
  font-size: var(--xc-fs-xs);
  font-weight: var(--xc-fw-medium);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ir-report-list__body span,
.ir-report-list__body time {
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-2xs);
  line-height: var(--xc-lh-normal);
}
.ir-report-list__view {
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 0 var(--xc-space-2);
  border: 0;
  border-radius: var(--xc-radius-sm);
  background: transparent;
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-2xs);
  white-space: nowrap;
  cursor: pointer;
  transition: background var(--xc-dur-fast), color var(--xc-dur-fast);
}
.ir-report-list__view:hover { background: var(--xc-surface-control); color: var(--xc-text-strong); }

.ir-home__ledger-trigger { display: none; }
.ir-home__ledger-close { display: none; }
.ir-home__ledger-backdrop { display: none; }

@media (max-width: 1439px) {
  .ir-home {
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
  }
  .ir-home__chat { flex: 1 1 auto; min-height: 0; }
  .ir-home__side {
    position: fixed;
    z-index: var(--xc-z-modal);
    inset: 16px 16px 16px auto;
    width: min(360px, calc(100vw - 32px));
    padding: 0;
    transform: translateX(calc(100% + 24px));
    transition: transform var(--xc-dur-base) var(--xc-ease-out);
  }
  .ir-home__side.is-open { transform: translateX(0); }
  .ir-home__side:not(.is-open) { visibility: hidden; pointer-events: none; }
  .ir-home__ledger { height: 100%; }
  .ir-home__ledger-trigger {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--xc-space-2);
    min-height: 36px;
    padding: 0 var(--xc-space-4);
    border: 1px solid var(--xc-border-accent);
    border-radius: var(--xc-radius-sm);
    background: var(--xc-surface-control);
    color: var(--xc-text-soft);
    font: inherit;
    font-size: var(--xc-fs-xs);
    cursor: pointer;
  }
  .ir-home__ledger-trigger:hover { border-color: var(--xc-accent-blue); color: var(--xc-text-strong); }
  .ir-home__ledger-trigger:focus-visible { outline: 2px solid var(--xc-accent-blue); outline-offset: 2px; }
  .ir-home__ledger-trigger svg { width: 16px; height: 16px; color: var(--xc-accent-blue); }
  .ir-home__toolbar { display: flex; }
  .ir-home__ledger-backdrop {
    display: block;
    position: fixed;
    z-index: calc(var(--xc-z-modal) - 1);
    inset: 0;
    background: rgba(10, 18, 28, 0.42);
  }
  .ir-home__ledger-close {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    margin-left: auto;
    border: 0;
    background: transparent;
    color: var(--xc-text-soft);
    cursor: pointer;
  }
  .ir-home__ledger-close :deep(svg) { width: 17px; height: 17px; }
  .ir-home__ledger-header { align-items: center; }
  .ir-home__ledger-header .ir-home__ledger-count { order: 3; margin-left: auto; }
  .ir-home__chat { --ir-message-inset: 60px; }
}
@media (min-width: 1101px) and (max-width: 1439px) {
  .ir-home__chat { --ir-message-inset: 32px; }
  .ir-home__toolbar {
    position: fixed;
    z-index: var(--xc-z-nav);
    top: 50%;
    right: 28px;
    width: 44px;
    min-height: 44px;
    margin: 0;
    padding: 0;
    border: 0;
    transform: translateY(-50%);
  }
  .ir-home__ledger-trigger {
    position: relative;
    width: 44px;
    height: 44px;
    min-height: 44px;
    padding: 0;
    border-radius: var(--xc-radius-full);
    background: var(--xc-surface-raised);
    box-shadow: var(--xc-shadow-md);
  }
  .ir-home__ledger-trigger span { display: none; }
  .ir-home__ledger-trigger svg { width: 18px; height: 18px; }
  .ir-home__ledger-trigger::after {
    content: attr(data-tip);
    position: absolute;
    top: 50%;
    right: calc(100% + 10px);
    padding: 5px 8px;
    border: 1px solid var(--xc-border-soft);
    border-radius: var(--xc-radius-xs);
    background: var(--xc-surface-raised);
    box-shadow: var(--xc-shadow-sm);
    color: var(--xc-text-strong);
    font-size: var(--xc-fs-2xs);
    white-space: nowrap;
    pointer-events: none;
    opacity: 0;
    transform: translateY(-50%);
    transition: opacity var(--xc-dur-fast);
  }
  .ir-home__ledger-trigger:hover::after,
  .ir-home__ledger-trigger:focus-visible::after { opacity: 1; }
  .ir-home--welcome {
    display: grid;
    grid-template-columns: minmax(0, 1fr) clamp(260px, 24vw, 300px);
    gap: var(--xc-space-4);
  }
}
@media (min-width: 1240px) and (max-width: 1299px) {
  .ir-home__chat { --ir-message-inset: 52px; }
  .ir-home__stream { padding-right: 104px; }
  .ir-home__toolbar { right: 8px; }
}
@media (min-width: 768px) and (max-width: 1100px) {
  .ir-home__stream { padding-right: 108px; }
  .ir-home__toolbar {
    position: fixed;
    z-index: var(--xc-z-nav);
    top: 50%;
    right: 8px;
    width: 44px;
    min-height: 44px;
    margin: 0;
    padding: 0;
    border: 0;
    transform: translateY(-50%);
  }
  .ir-home__ledger-trigger {
    position: relative;
    width: 44px;
    height: 44px;
    min-height: 44px;
    padding: 0;
    border-radius: var(--xc-radius-full);
    background: var(--xc-surface-raised);
    box-shadow: var(--xc-shadow-md);
  }
  .ir-home__ledger-trigger span { display: none; }
  .ir-home__ledger-trigger svg { width: 18px; height: 18px; }
  .ir-home__ledger-trigger::after {
    content: attr(data-tip);
    position: absolute;
    top: 50%;
    right: calc(100% + 10px);
    padding: 5px 8px;
    border: 1px solid var(--xc-border-soft);
    border-radius: var(--xc-radius-xs);
    background: var(--xc-surface-raised);
    box-shadow: var(--xc-shadow-sm);
    color: var(--xc-text-strong);
    font-size: var(--xc-fs-2xs);
    white-space: nowrap;
    pointer-events: none;
    opacity: 0;
    transform: translateY(-50%);
    transition: opacity var(--xc-dur-fast);
  }
  .ir-home__ledger-trigger:hover::after,
  .ir-home__ledger-trigger:focus-visible::after { opacity: 1; }
}
@media (max-width: 760px) {
  .ir-home { padding-inline: var(--xc-space-4); }
  .ir-home__chat { --ir-message-inset: 0px; }
  .ir-home__stream {
    padding: var(--xc-space-5) 0 var(--xc-space-6);
    gap: var(--xc-space-6);
  }
  .ir-msg { padding-top: 40px; }
  .ir-msg__avatar { top: 0; width: 30px; height: 30px; }
  .ir-msg__avatar--ai { left: 0; }
  .ir-msg__avatar--user { right: 0; }
  .ir-home__composer { width: 100%; padding: var(--xc-space-3) 0 var(--xc-space-4); }
  .ir-home__toolbar {
    width: 100%;
    min-height: 48px;
    padding-top: var(--xc-space-2);
  }
  .ir-home__ledger-trigger {
    width: 40px;
    height: 40px;
    min-height: 40px;
    padding: 0;
    border-radius: var(--xc-radius-full);
  }
  .ir-home__ledger-trigger span { display: none; }
  .ir-home__ledger-trigger svg { width: 17px; height: 17px; }
  .ir-home__ledger-header { align-items: flex-start; flex-wrap: wrap; padding: var(--xc-space-4); }
  .ir-home__ledger-header .ir-home__ledger-count { width: 100%; margin-left: 0; }
  .ir-home__side-title { padding-inline: var(--xc-space-4); }
  .ir-home__side-scroll { padding-inline: var(--xc-space-3); }
}
@media (prefers-reduced-motion: reduce) {
  .ir-welcome__orb { animation: none; }
  .ir-home__side,
  .ir-ver__select,
  .ir-ver__node,
  .ir-ver__report-action,
  .ir-ver__share-action,
  .ir-report-list__item,
  .ir-report-list__view { transition: none; }
}
</style>

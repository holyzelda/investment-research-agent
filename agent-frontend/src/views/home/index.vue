<template>
  <div class="ir-home" :class="{ 'ir-home--welcome': !hasConversation }">
    <!-- 中间：对话区 -->
    <section class="ir-home__chat">
      <!-- 欢迎态：背景由全局 layout 全屏承载；上区文字簇贴顶、下区提问框+胶囊沉底左对齐 -->
      <div v-if="!hasConversation" class="ir-welcome">
        <div class="ir-welcome__top">
          <div class="ir-welcome__heading">
            <img class="ir-welcome__orb" :src="orbSrc" alt="" aria-hidden="true" />
            <h1 class="ir-welcome__hi">
              你好，<br />我是朱雀投研智能体
            </h1>
          </div>
          <p class="ir-welcome__lead">
            用一句话完成储能项目投资测算
          </p>

          <div class="ir-welcome__abilities" aria-label="能力范围">
            <span>储能投资测算</span>
            <span>收益分析</span>
            <span>测算调整</span>
            <span>投资报告</span>
          </div>
        </div>

        <div class="ir-welcome__bottom">
          <ChatComposer
            class="ir-welcome__composer"
            :responding="calc.responding"
            placeholder="描述你的储能项目，例如：测算甘肃 200MW/800MWh 独立储能项目"
            @send="onSend"
            @stop="calc.stopStream"
          />

          <div class="ir-welcome__chips">
            <button
              v-for="eg in examples"
              :key="eg"
              class="ir-chip"
              :disabled="calc.responding"
              @click="onSend(eg)"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">
                <path d="M13 2 4 14h7l-1 8 9-12h-7z" stroke-linejoin="round" />
              </svg>
              <span>{{ eg }}</span>
            </button>
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
                @retry="calc.generateReport"
              />
              <AiAnswerContent v-else-if="m.answerText" :text="m.answerText" :error="Boolean(m.error)" />
              <div v-if="m.result" class="ir-msg__result">
                <ResultCard
                  :result="m.result"
                  :version="m.version"
                  :calculated-at="m.calculatedAt"
                  :seed-input="m.input || {}"
                  :param-dict="m.version === calc.latestVersion?.version ? calc.paramDict : []"
                  :switches="calc.switches"
                  :station-options="calc.stationOptions"
                  :responding="calc.responding"
                  :report="calc.versions.find((item) => item.taskId === m.taskId)?.report"
                  @recalculate="calc.recalculate($event)"
                  @generate-report="calc.generateReport(m.taskId)"
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
                @retry="calc.generateReport"
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
                :param-dict="m.version === calc.latestVersion?.version ? calc.paramDict : []"
                :switches="calc.switches"
                :station-options="calc.stationOptions"
                :responding="calc.responding"
                :report="m.report || calc.versions.find((item) => item.taskId === m.taskId)?.report"
                @recalculate="calc.recalculate($event)"
                @generate-report="calc.generateReport(m.taskId)"
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

    <!-- 右侧项目档案：版本轨道与正式报告。 -->
    <aside v-if="hasConversation" class="ir-home__side">
      <div class="ir-home__ledger">
        <header class="ir-home__ledger-header">
          <h2>项目档案</h2>
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
                    <template v-if="v.version === calc.selectedVersion">
                      <span class="ir-ver__metric">
                        <span>项目全投资 IRR</span>
                        <strong class="xc-num">{{ formatNumber(v.result?.financial?.projectIrr) }}%</strong>
                      </span>
                      <span class="ir-ver__time xc-num">测算时间 {{ formatRecordTime(v.calculatedAt) }}</span>
                    </template>
                  </span>
                </button>
                <button
                  v-if="v.version === calc.selectedVersion"
                  type="button"
                  class="ir-ver__report-action"
                  :disabled="v.report?.status === 'generating'"
                  @click="v.report?.status === 'completed' ? jumpToReportRecord(v.report.reportId) : calc.generateReport(v.taskId)"
                >
                  {{ v.report?.status === 'completed' ? '跳转报告记录' : v.report?.status === 'generating' ? '报告生成中' : v.report?.status === 'failed' ? '重新生成报告' : '生成报告' }}
                  <svg v-if="v.report?.status !== 'generating'" viewBox="0 0 16 16" aria-hidden="true">
                    <path d="m6 3 5 5-5 5" />
                  </svg>
                </button>
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
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/store/modules/session'
import { useCalculationStore } from '@/store/modules/calculation'
import ResultCard from './components/ResultCard.vue'
import ChatComposer from './components/ChatComposer.vue'
import ThinkingChain from './components/ThinkingChain.vue'
import AiAnswerContent from './components/AiAnswerContent.vue'
import ReportGenerationCard from './components/ReportGenerationCard.vue'
import { thinkingNodes, hasActiveNode } from '@/utils/thinkingChain'
import orbSrc from '@/assets/ai-sphere.png'
import agentAvatar from '@/assets/agent.png'
import userAvatar from '@/assets/user.png'
import { formatNumber } from '@/utils/formatNumber'
import {
  buildReportProjectName,
  buildReportTitle,
  buildVersionTitle,
  formatProjectLocation,
} from '@/utils/projectTitle'

const session = useSessionStore()
const router = useRouter()
const calc = useCalculationStore()
const scrollEl = ref(null)
const reportListEl = ref(null)
const highlightedReportId = ref(null)
const messageElements = new Map()
let reportHighlightTimer
let scrollFrame
let scrollRetryTimer
let streamObserver

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

async function onSend(text) {
  const pending = calc.sendAndCalculate(text)
  await nextTick()
  scheduleAutoScroll()
  await pending
}

function thinkingNodesOf(message) {
  return message.thinkingState ? thinkingNodes(message.thinkingState) : []
}

function hasActiveThinkingOf(message) {
  return message.thinkingState ? hasActiveNode(message.thinkingState) : false
}

async function selectVersion(version) {
  calc.selectVersion(version)
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

/* ---------- 欢迎态：背景由全局 layout 承载；上区文字贴顶、下区提问框沉底 ---------- */
.ir-welcome {
  position: relative;
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-start;
  min-height: 0;
  padding: var(--xc-space-9) 0;
  overflow: hidden;
}
/* 上区：欢迎语 + 描述 + 能力标签，贴顶（略下移，避免顶到边） */
.ir-welcome__top {
  position: relative;
  z-index: 1;
  width: 100%;
  padding-inline: var(--xc-space-10);
  margin-top: clamp(40px, 9vh, 110px);
  text-align: left;
}
/* 下区：提问框 + 示例胶囊，锚在主区底部、收窄左对齐（与对话态 composer 同宽档位，右侧留白给 hero） */
.ir-welcome__bottom {
  position: relative;
  z-index: 1;
  width: calc(100% - 2 * var(--ir-message-inset));
  max-width: var(--xc-content-fluid);
  margin-inline: auto;
  display: flex;
  flex-direction: column;
  gap: var(--xc-space-5);
}
.ir-welcome__heading {
  display: flex;
  align-items: center;
  gap: var(--xc-space-5);
  margin-bottom: var(--xc-space-4);
}
.ir-welcome__orb {
  flex: 0 0 auto;
  width: 96px;
  height: 96px;
  object-fit: contain;
  filter: drop-shadow(0 10px 48px rgba(110, 42, 255, 0.55));
  animation: ir-orb-float 6s ease-in-out infinite;
}
@keyframes ir-orb-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}
.ir-welcome__hi {
  margin: 0;
  font-size: clamp(36px, 3.4vw, 52px);
  font-weight: var(--xc-fw-bold);
  line-height: var(--xc-lh-snug);
  letter-spacing: 0.5px;
  background: var(--xc-grad-brand-h);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.ir-welcome__lead {
  font-size: var(--xc-fs-lg);
  color: var(--xc-text-soft);
  line-height: var(--xc-lh-normal);
  margin: 0 0 var(--xc-space-5);
}
.ir-welcome__lead strong { color: var(--xc-accent-blue); }
.ir-welcome__abilities {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-start;
  align-items: center;
  gap: var(--xc-space-5);
  margin-bottom: var(--xc-space-8);
}
.ir-welcome__abilities span {
  position: relative;
  font-size: var(--xc-fs-md);
  color: var(--xc-text-soft);
}
.ir-welcome__abilities span::before {
  content: '·';
  position: absolute;
  left: calc(-1 * var(--xc-space-3));
  color: var(--xc-text-faint);
}
.ir-welcome__abilities span:first-child::before { content: none; }
.ir-welcome__abilities span.is-accent { color: var(--xc-accent-blue); }
.ir-welcome__composer { padding: 0; }
.ir-welcome__chips {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-start;
  gap: var(--xc-space-3);
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
.ir-ver__time { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); line-height: var(--xc-lh-normal); }
.ir-ver__report-action {
  width: calc(100% - var(--xc-space-4));
  min-height: 36px;
  margin: var(--xc-space-2) 0 var(--xc-space-2) var(--xc-space-4);
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

@media (max-width: 1100px) {
  .ir-home {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: minmax(620px, 1fr) minmax(360px, 54vh);
    height: auto;
    min-height: 100%;
    overflow-y: auto;
  }
  .ir-home__chat { min-height: 620px; }
  .ir-home__side { min-height: 360px; padding-top: 0; }
}
@media (max-width: 1200px) {
  .ir-home__chat { --ir-message-inset: 60px; }
  .ir-msg__avatar--ai { left: -44px; }
  .ir-msg__avatar--user { right: -44px; }
}
@media (max-width: 760px) {
  .ir-home { grid-template-rows: minmax(560px, 1fr) minmax(340px, 58vh); }
  .ir-home__chat { --ir-message-inset: 44px; min-height: 560px; }
  .ir-msg__avatar--ai { left: -38px; }
  .ir-msg__avatar--user { right: -38px; }
  .ir-home__ledger-header { align-items: flex-start; flex-direction: column; padding: var(--xc-space-4); }
  .ir-home__side-title { padding-inline: var(--xc-space-4); }
  .ir-home__side-scroll { padding-inline: var(--xc-space-3); }
}
@media (prefers-reduced-motion: reduce) {
  .ir-ver__select,
  .ir-ver__node,
  .ir-ver__report-action,
  .ir-report-list__item,
  .ir-report-list__view { transition: none; }
}
</style>

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
            <div v-if="m.kind === 'text'" class="ir-msg__bubble">
              <span :class="{ 'ir-msg__pending': m.text === '测算中…' }">{{ m.text }}</span>
            </div>
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
              <AiAnswerContent v-if="m.answerText" :text="m.answerText" :error="Boolean(m.error)">
                <template v-if="m.flow === 'report' && m.reportId" #actions>
                  <button type="button" @click="openReport(m.reportId)">查看报告</button>
                </template>
              </AiAnswerContent>
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
                  :report="calc.versions.find((item) => item.version === m.version)?.report"
                  @recalculate="calc.recalculate($event)"
                  @generate-report="calc.generateReport(m.taskId)"
                  @view-report="openReport"
                />
              </div>
              <ul v-if="m.recommendedQuestions && m.recommendedQuestions.length" class="ir-msg__recommend">
                <li v-for="(q, qi) in m.recommendedQuestions" :key="qi">
                  <button type="button" :disabled="calc.responding" @click="onSend(q)">{{ q }}</button>
                </li>
              </ul>
            </div>
            <AiAnswerContent v-else-if="m.kind === 'report-generated'" :text="m.text || '正式报告已生成，可查看完整报告。'">
              <template #actions>
                <button type="button" @click="openReport(m.payload?.report_id)">查看报告</button>
              </template>
            </AiAnswerContent>
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
                :report="m.report || calc.versions.find((item) => item.version === m.version)?.report"
                @recalculate="calc.recalculate($event)"
                @generate-report="calc.generateReport(calc.versions.find((item) => item.version === m.version)?.taskId)"
                @view-report="openReport"
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

    <!-- 右侧：测算记录与报告记录。 -->
    <aside v-if="hasConversation" class="ir-home__side">
      <section class="ir-home__side-section">
        <div class="ir-home__side-title">测算记录</div>
        <div class="ir-home__side-scroll">
          <div v-if="!calc.versions.length" class="ir-home__side-empty">
            暂无版本，发起测算后在此追踪 V1 / V2 / V3…
          </div>
          <ul v-else class="ir-ver">
            <li
              v-for="v in reversedVersions"
              :key="v.version"
              class="ir-ver__item"
              :class="{
                'ir-ver__item--selected': v.version === calc.selectedVersion,
              }"
              tabindex="0"
              @click="selectVersion(v.version)"
              @keydown.enter="selectVersion(v.version)"
            >
              <div class="ir-ver__row">
                <span class="ir-ver__tag">{{ v.version }}</span>
                <span v-if="v.version === calc.latestVersion?.version" class="ir-ver__dot">● 最新</span>
              </div>
              <div class="ir-ver__spec">{{ versionSpec(v) }}</div>
              <div class="ir-ver__metric xc-num">
                项目全投资IRR {{ formatNumber(v.result?.financial?.projectIrr) }}%
              </div>
              <div class="ir-ver__time">测算时间：{{ formatRecordTime(v.calculatedAt) }}</div>
              <button
                class="ir-report-list__view ir-report-list__view--full"
                :disabled="v.report?.status === 'generating'"
                @click.stop="v.report?.status === 'completed' ? jumpToReportRecord(v.report.reportId) : calc.generateReport(v.taskId)"
              >{{ v.report?.status === 'completed' ? '跳转报告记录' : v.report?.status === 'generating' ? '报告生成中' : v.report?.status === 'failed' ? '重新生成报告' : '生成报告' }}</button>
            </li>
          </ul>
        </div>
      </section>
      <section class="ir-home__side-section">
        <div class="ir-home__side-title">报告记录</div>
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
              <strong>{{ report.title || '正式报告' }}</strong>
              <span>关联测算：{{ report.version }}</span>
              <span>{{ formatRecordTime(report.createdAt) }}</span>
              <button class="ir-report-list__view ir-report-list__view--full" @click="openReport(report.reportId)">查看报告</button>
            </li>
          </ul>
        </div>
      </section>
    </aside>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/store/modules/session'
import { useCalculationStore } from '@/store/modules/calculation'
import ResultCard from './components/ResultCard.vue'
import ChatComposer from './components/ChatComposer.vue'
import ThinkingChain from './components/ThinkingChain.vue'
import AiAnswerContent from './components/AiAnswerContent.vue'
import { thinkingNodes, hasActiveNode } from '@/utils/thinkingChain'
import orbSrc from '@/assets/ai-sphere.png'
import agentAvatar from '@/assets/agent.png'
import userAvatar from '@/assets/user.png'
import { formatNumber } from '@/utils/formatNumber'

const session = useSessionStore()
const router = useRouter()
const calc = useCalculationStore()
const scrollEl = ref(null)
const reportListEl = ref(null)
const highlightedReportId = ref(null)
let reportHighlightTimer
let scrollFrame
let scrollRetryTimer
let streamObserver

function forceScrollToBottom() {
  if (!scrollEl.value) return
  scrollEl.value.scrollTop = scrollEl.value.scrollHeight
}

function scheduleScrollToBottom() {
  cancelAnimationFrame(scrollFrame)
  scrollFrame = requestAnimationFrame(() => {
    forceScrollToBottom()
    clearTimeout(scrollRetryTimer)
    scrollRetryTimer = setTimeout(forceScrollToBottom, 60)
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
    forceScrollToBottom()
    if (conversationActive.value) scrollFrame = requestAnimationFrame(tick)
  }
  scrollFrame = requestAnimationFrame(tick)
}

watch(conversationActive, async (active) => {
  await nextTick()
  if (active) startScrollAnchor()
  else {
    stopScrollAnchor()
    scheduleScrollToBottom()
  }
}, { flush: 'post' })

watch(scrollEl, (element) => {
  streamObserver?.disconnect()
  if (!element || typeof MutationObserver === 'undefined') return
  streamObserver = new MutationObserver(() => {
    if (conversationActive.value) scheduleScrollToBottom()
  })
  streamObserver.observe(element, { childList: true, subtree: true, characterData: true })
}, { flush: 'post' })

onBeforeUnmount(() => {
  clearTimeout(reportHighlightTimer)
  stopScrollAnchor()
  streamObserver?.disconnect()
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
  '测算甘肃 200MW/800MWh 独立储能项目',
  '测算宁夏 100MW/400MWh 储能',
  '测算山东 300MW/600MWh 独立储能',
]

async function onSend(text) {
  scheduleScrollToBottom()
  await calc.sendAndCalculate(text)
  await nextTick()
  scheduleScrollToBottom()
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
  const target = scrollEl.value?.querySelector(`[data-version="${version}"]`)
  if (typeof target?.scrollIntoView === 'function') {
    target.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

function openReport(reportId) {
  if (reportId) router.push(`/reports/${reportId}`)
}

async function jumpToReportRecord(reportId) {
  await nextTick()
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

// 右侧测算记录条目摘要：测算{省份} {功率}MW/{容量}MWh，缺省时优雅降级
function versionSpec(v) {
  const b = v.result?.basicInfo || {}
  const province = b.province ?? v.input?.province ?? ''
  const power = b.powerMw ?? v.input?.power_mw
  const capacity = b.capacityMwh ?? v.input?.capacity_mwh
  const scale = [power, capacity].every((x) => x !== null && x !== undefined)
    ? `${formatNumber(power)}MW/${formatNumber(capacity)}MWh`
    : ''
  return `测算${province} ${scale}`.trim()
}
</script>

<style scoped>
.ir-home {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(240px, 20%);
  gap: var(--xc-space-6);
  height: 100%;
  padding: 0 var(--xc-gutter-x);
}
.ir-home--welcome {
  grid-template-columns: 1fr; /* 欢迎态不显示右栏，主区占满 */
}
.ir-home__chat {
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
  padding: var(--xc-space-9) var(--xc-space-10);
  overflow: hidden;
}
/* 上区：欢迎语 + 描述 + 能力标签，贴顶（略下移，避免顶到边） */
.ir-welcome__top {
  position: relative;
  z-index: 1;
  width: 100%;
  margin-top: clamp(40px, 9vh, 110px);
  text-align: left;
}
/* 下区：提问框 + 示例胶囊，锚在主区底部、收窄左对齐（与对话态 composer 同宽档位，右侧留白给 hero） */
.ir-welcome__bottom {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: var(--xc-content-fluid);
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
  /* 左右留出足够空间容纳对话框外侧的头像，不被裁切 */
  padding: var(--xc-space-8) 72px var(--xc-space-7);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--xc-space-6);
}
/* 对话框本身的宽度 = 输入框宽度，头像绝对定位在框外，不占用/挤压对话框宽度 */
.ir-msg { position: relative; display: flex; width: 100%; max-width: var(--xc-content-fluid); }
.ir-msg--user { justify-content: flex-end; }
.ir-msg--assistant { justify-content: flex-start; }
.ir-msg__avatar {
  position: absolute;
  top: 2px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
}
.ir-msg__avatar--ai { left: -44px; }
.ir-msg__avatar--user { right: -44px; }
/* 用户气泡：右对齐、灰底、克制 */
.ir-msg--user .ir-msg__bubble {
  max-width: 78%;
  padding: var(--xc-space-3) var(--xc-space-5);
  border-radius: var(--xc-radius-lg);
  font-size: var(--xc-fs-md);
  line-height: var(--xc-lh-normal);
  color: var(--xc-text-default);
  background: var(--xc-surface-control);
  word-break: break-word;
}
/* AI 消息：满宽、极淡底、无边框，头像在框外左侧（对齐 trader ai-bubble） */
.ir-msg--assistant .ir-msg__bubble {
  width: 100%;
  padding: var(--xc-space-6);
  border-radius: var(--xc-radius-lg);
  font-size: var(--xc-fs-md);
  line-height: var(--xc-lh-loose);
  color: var(--xc-text-default);
  background: var(--xc-surface-card);
}
.ir-msg__pending { color: var(--xc-text-mute); }
.ir-msg__result { width: 100%; }
.ir-msg__stream { width: 100%; display: flex; flex-direction: column; gap: var(--xc-space-3); }
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
.ir-msg--selected-result .ir-msg__result {
  border-radius: var(--xc-radius-lg);
  box-shadow: 0 0 0 1px var(--xc-border-accent);
}
/* 对话态底部输入框：居中收窄，与消息流同宽 */
.ir-home__composer {
  width: 100%;
  max-width: var(--xc-content-fluid);
  margin: 0 auto;
  padding: var(--xc-space-4) var(--xc-space-6) var(--xc-space-6);
}

/* ---------- 右侧版本记录 ---------- */
.ir-home__side {
  border-left: 1px solid var(--xc-border-soft);
  padding: var(--xc-space-6) 0 var(--xc-space-6) var(--xc-space-6);
  min-height: 0;
  display: grid;
  grid-template-rows: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--xc-space-6);
}
.ir-home__side-section { min-height: 0; display: flex; flex-direction: column; }
.ir-home__side-scroll { min-height: 0; overflow-y: auto; padding-right: var(--xc-space-2); }
.ir-home__side-title {
  font-size: var(--xc-fs-sm);
  font-weight: var(--xc-fw-medium);
  color: var(--xc-text-strong);
  margin-bottom: var(--xc-space-4);
}
.ir-home__side-empty {
  font-size: var(--xc-fs-2xs);
  color: var(--xc-text-mute);
  line-height: var(--xc-lh-loose);
}
.ir-ver { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--xc-space-3); }
.ir-report-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--xc-space-3); }
.ir-report-list__item { display: flex; flex-direction: column; gap: var(--xc-space-2); border: 1px solid var(--xc-border-card); border-radius: var(--xc-radius-md); background: var(--xc-surface-card); padding: var(--xc-space-4); font-size: var(--xc-fs-2xs); color: var(--xc-text-soft); }
.ir-report-list__item--highlighted {
  background: color-mix(in srgb, var(--xc-accent-blue) 14%, transparent);
}
.ir-report-list__item strong { color: var(--xc-text-strong); font-size: var(--xc-fs-xs); }
.ir-ver__item {
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-md);
  background: var(--xc-surface-card);
  padding: var(--xc-space-4);
  cursor: pointer;
  transition: border-color var(--xc-dur-fast), background var(--xc-dur-fast);
}
.ir-ver__item--selected {
  border-color: var(--xc-border-accent);
  background: var(--xc-surface-control);
}
.ir-ver__row { display: flex; align-items: center; justify-content: space-between; }
.ir-ver__tag {
  font-size: var(--xc-fs-2xs);
  color: var(--xc-text-inverse);
  background: var(--xc-accent-blue);
  border-radius: var(--xc-radius-full);
  padding: 1px var(--xc-space-3);
}
.ir-ver__dot { font-size: var(--xc-fs-3xs); color: var(--xc-status-ok); }
.ir-ver__spec { font-size: var(--xc-fs-xs); color: var(--xc-text-default); margin-top: var(--xc-space-2); }
.ir-ver__time { margin: var(--xc-space-2) 0; font-size: var(--xc-fs-3xs); color: var(--xc-text-mute); }
.ir-ver__metric { font-size: var(--xc-fs-xs); color: var(--xc-text-soft); margin: var(--xc-space-2) 0 var(--xc-space-3); }
.ir-report-list__view {
  min-height: 28px;
  padding: 4px var(--xc-space-3);
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-sm);
  background: var(--xc-surface-control);
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-3xs);
  cursor: pointer;
}
.ir-report-list__view--full { width: 100%; }
.ir-ver__report {
  font-size: var(--xc-fs-3xs);
  color: var(--xc-text-mute);
  background: transparent;
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-sm);
  padding: 2px var(--xc-space-3);
  cursor: pointer;
}
</style>

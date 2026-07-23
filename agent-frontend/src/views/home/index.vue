<template>
  <div class="ir-home" :class="{ 'ir-home--welcome': !hasConversation }">
    <!-- 中间：对话区 -->
    <section class="ir-home__chat">
      <!-- 欢迎态：居中问候 + 输入框 + 示例胶囊 -->
      <div v-if="!hasConversation" class="ir-welcome">
        <div class="ir-welcome__inner">
          <img class="ir-welcome__orb" :src="orbSrc" alt="" aria-hidden="true" />
          <h1 class="ir-welcome__hi">
            你好，我是朱雀投研智能体
          </h1>
          <p class="ir-welcome__lead">
            用一句话给出<strong>省份 · 容量 · 功率</strong>，我来完成储能项目的权威测算，
            并给出财务指标、收入结构与 15 年现金流。
          </p>

          <ChatComposer
            class="ir-welcome__composer"
            :responding="calc.responding"
            placeholder="描述你的储能项目，例如：测算甘肃 200MW/800MWh 独立储能项目"
            @send="onSend"
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
            <div v-else-if="m.kind === 'result'" class="ir-msg__result">
              <!-- 调整参数并重新测算仅在最新版本卡片开放：
                   现货依赖比较/受控覆盖以“会话最新已完成版本”为基线，
                   在旧版本卡片上操作会与其自身展示值不一致，因此不提供入口 -->
              <ResultCard
                :result="m.result"
                :version="m.version"
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

        <ChatComposer class="ir-home__composer" :responding="calc.responding" @send="onSend" />
      </template>
    </section>

    <!-- 右侧：测算记录与报告记录。 -->
    <aside v-if="hasConversation" class="ir-home__side">
      <section class="ir-home__side-section">
        <div class="ir-home__side-title">测算记录</div>
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
          <div class="ir-ver__metric xc-num">
            项目全投资IRR {{ formatNumber(v.result?.financial?.projectIrr) }}%
          </div>
          <button
            class="ir-ver__report"
            :disabled="v.report?.status === 'generating'"
            @click.stop="v.report?.status === 'completed' ? openReport(v.report.reportId) : calc.generateReport(v.taskId)"
          >{{ v.report?.status === 'completed' ? '查看报告' : v.report?.status === 'generating' ? '报告生成中' : v.report?.status === 'failed' ? '重新生成报告' : '生成报告' }}</button>
        </li>
      </ul>
      </section>
      <section class="ir-home__side-section">
        <div class="ir-home__side-title">报告记录</div>
        <div v-if="!reversedReports.length" class="ir-home__side-empty">暂无已生成报告</div>
        <ul v-else class="ir-report-list">
          <li v-for="report in reversedReports" :key="report.reportId" class="ir-report-list__item">
            <strong>{{ report.title || '正式报告' }}</strong>
            <span>关联测算：{{ report.version }}</span>
            <span>{{ report.createdAt }}</span>
            <button class="ir-ver__report" @click="openReport(report.reportId)">查看报告</button>
          </li>
        </ul>
      </section>
    </aside>
  </div>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/store/modules/session'
import { useCalculationStore } from '@/store/modules/calculation'
import ResultCard from './components/ResultCard.vue'
import ChatComposer from './components/ChatComposer.vue'
import orbSrc from '@/assets/ai-sphere.png'
import agentAvatar from '@/assets/agent.png'
import userAvatar from '@/assets/user.png'
import { formatNumber } from '@/utils/formatNumber'

const session = useSessionStore()
const router = useRouter()
const calc = useCalculationStore()
const scrollEl = ref(null)

const hasConversation = computed(() => calc.messages.length > 0)
const reversedVersions = computed(() => [...calc.versions].reverse())
const reversedReports = computed(() => calc.reports
  .filter((report) => report.status === 'completed' && report.reportId)
  .slice()
  .reverse())

const examples = [
  '测算甘肃 200MW/800MWh 独立储能项目',
  '测算宁夏 100MW/400MWh 储能',
  '测算山东 300MW/600MWh 独立储能',
]

async function onSend(text) {
  await calc.sendAndCalculate(text)
  await nextTick()
  if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
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
</script>

<style scoped>
.ir-home {
  display: grid;
  grid-template-columns: 1fr 300px;
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

/* ---------- 欢迎态：居中 ---------- */
.ir-welcome {
  flex: 1 1 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--xc-space-11) var(--xc-space-9);
}
.ir-welcome__inner {
  width: min(860px, 100%);
  text-align: center;
}
.ir-welcome__orb {
  width: 108px;
  height: 108px;
  object-fit: contain;
  filter: drop-shadow(0 10px 48px rgba(110, 42, 255, 0.55));
  margin-bottom: var(--xc-space-5);
  animation: ir-orb-float 6s ease-in-out infinite;
}
@keyframes ir-orb-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}
.ir-welcome__hi {
  font-size: clamp(36px, 3.4vw, 52px);
  font-weight: var(--xc-fw-bold);
  line-height: var(--xc-lh-snug);
  letter-spacing: 0.5px;
  background: var(--xc-grad-brand-h);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  margin: 0 0 var(--xc-space-5);
}
.ir-welcome__lead {
  font-size: var(--xc-fs-md);
  color: var(--xc-text-soft);
  line-height: var(--xc-lh-loose);
  margin: 0 auto var(--xc-space-8);
  max-width: 640px;
}
.ir-welcome__lead strong { color: var(--xc-accent-blue); }
.ir-welcome__composer { padding: 0; }
.ir-welcome__chips {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--xc-space-3);
  margin-top: var(--xc-space-6);
}
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
.ir-msg--selected-result .ir-msg__result {
  border-radius: var(--xc-radius-lg);
  box-shadow: 0 0 0 1px var(--xc-border-accent);
}
/* 对话态底部输入框：居中收窄，与消息流同宽 */
.ir-home__composer {
  width: 100%;
  max-width: var(--xc-content-fluid);
  margin: 0 auto;
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
.ir-home__side-section { min-height: 0; overflow-y: auto; }
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
.ir-ver__metric { font-size: var(--xc-fs-xs); color: var(--xc-text-soft); margin: var(--xc-space-3) 0; }
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

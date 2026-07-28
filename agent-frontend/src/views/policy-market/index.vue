<template>
  <section class="policy-market-page">
    <div class="policy-market-page__grid">
      <ConsultationHistory :consultations="store.consultations" :selected-id="store.selectedConsultationId" @new-question="handleNewQuestion" @select="handleSelectConsultation" />
      <main ref="consultRef" class="policy-market-page__consult" :class="{ 'is-reading': isReading }">
        <header v-if="!isReading" class="policy-market-page__hero">
          <div class="policy-market-page__hero-meta">
            <span>政策研判工作台</span>
            <span>POLICY RESEARCH DESK</span>
          </div>
          <h1>从政策原文，<br><em>得到可执行判断</em></h1>
          <p>连接政策文件、市场动态与行业经验，快速厘清影响范围、关键变化和行动方向。</p>
        </header>
        <ConsultationComposer v-if="!isReading" ref="composerRef" @submit-question="handleSubmit" />
        <header v-else class="policy-market-page__reader-bar">
          <div>
            <span>研究结论</span>
            <h1>{{ selectedTitle }}</h1>
            <time>{{ selectedDate }}</time>
          </div>
          <button type="button" @click="handleNewQuestion()"><Plus :size="16" />新建提问</button>
        </header>
        <p v-if="store.consultationsLoading" class="policy-market-page__notice" aria-live="polite">正在加载咨询记录</p>
        <p v-else-if="store.consultationsError" class="policy-market-page__notice policy-market-page__notice--error" aria-live="polite">{{ store.consultationsError }}</p>
        <p v-if="store.consultationDetailLoading" class="policy-market-page__notice" aria-live="polite">正在调取完整研究结论</p>
        <p v-else-if="store.consultationDetailError" class="policy-market-page__notice policy-market-page__notice--error" role="alert">{{ store.consultationDetailError }}</p>
        <div ref="resultAnchorRef" class="policy-market-page__result-anchor" aria-hidden="true"></div>
        <ConsultationResult :consultation="store.selectedConsultation" :reader-mode="isReading" @reuse-question="handleNewQuestion" />
        <p v-if="isReading" class="policy-market-page__source-note">回答基于公开政策文件与市场数据，具体结论请结合实际场景判断。</p>
      </main>
      <MarketPulse :filters="store.statsFilters" :stats="store.stats" :topic-options="store.topicOptions" :news="store.news" :loading="store.newsLoading" :error="store.newsError" :stats-loading="store.statsLoading" :stats-error="store.statsError" @filters-change="handleFiltersChange" />
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@lucide/vue'
import { usePolicyMarketStore } from '@/store/modules/policyMarket'
import ConsultationHistory from './components/ConsultationHistory.vue'
import ConsultationComposer from './components/ConsultationComposer.vue'
import ConsultationResult from './components/ConsultationResult.vue'
import MarketPulse from './components/MarketPulse.vue'

const store = usePolicyMarketStore()
const composerRef = ref(null)
const consultRef = ref(null)
const resultAnchorRef = ref(null)
const isReading = computed(() => store.selectedConsultationId !== null)
const selectedTitle = computed(() => store.selectedConsultation?.title || store.selectedConsultation?.question || '研究结论')
const selectedDate = computed(() => formatReaderDate(store.selectedConsultation?.createdAt))
onMounted(() => { store.loadInitialData() })
async function handleNewQuestion(prefill = '') {
  store.startNewConsultation()
  await nextTick()
  composerRef.value?.setQuestion(typeof prefill === 'string' ? prefill : '')
  composerRef.value?.focus()
}
async function handleSubmit(question) { try { await store.submitQuestion(question) } catch (error) { ElMessage.error(error?.message || '咨询提交失败，请稍后重试') } }
async function handleSelectConsultation(id) {
  try {
    await store.selectConsultation(id)
  } catch (error) {
    ElMessage.error(error?.message || '研究结论加载失败，请稍后重试')
  }
  await nextTick()
  scrollResultToTop()
}
function handleFiltersChange(filters) { store.setStatsFilters(filters) }
function scrollResultToTop() {
  const isCompact = window.matchMedia('(max-width: 1100px)').matches
  resultAnchorRef.value?.scrollIntoView({ behavior: isCompact ? 'smooth' : 'auto', block: 'start' })
  if (!isCompact) consultRef.value?.scrollTo?.({ top: 0, behavior: 'auto' })
}
function formatReaderDate(value) {
  if (!value) return '日期未记录'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '日期未记录'
  return new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(date)
}
</script>

<style scoped>
.policy-market-page {
  --pm-accent: #54c6d6;
  --pm-surface: #283034;
  --pm-elevated: #323b3f;
  --pm-border: #485458;
  min-height: 100%;
  box-sizing: border-box;
  padding: 24px clamp(14px, 1.5vw, 28px) 48px;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.policy-market-page::-webkit-scrollbar {
  display: none;
  width: 0;
  height: 0;
}

.policy-market-page__grid {
  display: grid;
  grid-template-columns: minmax(196px, 228px) minmax(0, 1fr) minmax(296px, 340px);
  column-gap: clamp(20px, 1.8vw, 32px);
  align-items: start;
  width: min(100%, 1760px);
  min-height: calc(100vh - 64px - 80px);
  margin: 0 auto;
}

.policy-market-page__consult {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 0;
}

.policy-market-page__consult.is-reading { gap: 16px; }
.policy-market-page__result-anchor { height: 0; scroll-margin-top: 82px; }

.policy-market-page__hero {
  display: grid;
  gap: 12px;
  padding: 4px 2px 12px;
}

.policy-market-page__hero-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--xc-border-soft);
  color: var(--xc-text-mute);
  font-family: var(--xc-font-mono);
  font-size: var(--xc-fs-2xs);
}

.policy-market-page__hero-meta span:first-child {
  color: var(--pm-accent);
  font-family: var(--xc-font-zh);
  font-weight: var(--xc-fw-semi);
}

.policy-market-page__hero h1 {
  max-width: 680px;
  margin: 0;
  color: var(--xc-text-strong);
  font-size: clamp(32px, 3vw, 44px);
  font-weight: var(--xc-fw-semi);
  line-height: 1.2;
  letter-spacing: 0;
  text-wrap: balance;
}

.policy-market-page__hero h1 em { color: var(--pm-accent); font-style: normal; }
.policy-market-page__hero p,
.policy-market-page__notice {
  max-width: 620px;
  margin: 0;
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-sm);
  line-height: var(--xc-lh-loose);
}

.policy-market-page__notice { margin: 0; font-size: var(--xc-fs-xs); }
.policy-market-page__notice--error { color: var(--xc-status-danger); }
.policy-market-page__source-note { margin: 0; padding: 12px 0 0 26px; border-top: 1px solid var(--xc-border-soft); color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); line-height: var(--xc-lh-normal); }

.policy-market-page__reader-bar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 6px 0 16px 26px;
  border-bottom: 1px solid var(--xc-border-soft);
}

.policy-market-page__reader-bar > div { min-width: 0; display: grid; gap: 6px; }
.policy-market-page__reader-bar span { color: var(--pm-accent); font-size: var(--xc-fs-2xs); font-weight: var(--xc-fw-semi); }
.policy-market-page__reader-bar h1 { display: -webkit-box; max-width: 780px; margin: 0; overflow: hidden; color: var(--xc-text-strong); font-size: clamp(22px, 2vw, 30px); font-weight: var(--xc-fw-semi); line-height: 1.3; overflow-wrap: anywhere; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.policy-market-page__reader-bar time { color: var(--xc-text-mute); font-family: var(--xc-font-mono); font-size: var(--xc-fs-2xs); }
.policy-market-page__reader-bar button { min-height: 40px; display: inline-flex; align-items: center; justify-content: center; flex: 0 0 auto; gap: 8px; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); padding: 8px 13px; background: transparent; color: var(--xc-text-strong); font: inherit; font-size: var(--xc-fs-xs); cursor: pointer; }
.policy-market-page__reader-bar button:hover, .policy-market-page__reader-bar button:focus-visible { border-color: var(--pm-accent); outline: none; background: var(--xc-surface-frosted); }
.policy-market-page__reader-bar button:focus-visible { box-shadow: 0 0 0 2px var(--pm-accent); }

@media (max-width: 1280px) {
  .policy-market-page { overflow-y: auto; }
  .policy-market-page__grid { grid-template-columns: 192px minmax(0, 1fr); column-gap: 24px; }
  .policy-market-page__grid > :last-child { grid-column: 1 / -1; }
}

@media (max-width: 1100px) {
  .policy-market-page__grid { grid-template-columns: minmax(0, 1fr); column-gap: 0; }
  .policy-market-page__consult { padding: 24px 0 0; }
  .policy-market-page__grid > :last-child { grid-column: auto; }
}

@media (max-width: 640px) {
  .policy-market-page { padding: 14px 12px 28px; }
  .policy-market-page__grid { min-height: auto; grid-template-columns: 1fr; }
  .policy-market-page__grid > :last-child { grid-column: auto; }
  .policy-market-page__consult { padding-top: 20px; }
  .policy-market-page__hero { padding: 0 2px 6px; }
  .policy-market-page__hero-meta span:last-child { display: none; }
  .policy-market-page__hero h1 { font-size: 30px; }
  .policy-market-page__reader-bar { align-items: stretch; flex-direction: column; gap: 14px; padding: 2px 0 14px 18px; }
  .policy-market-page__reader-bar button { width: 100%; min-height: 44px; }
}
</style>

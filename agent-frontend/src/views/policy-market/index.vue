<template>
  <section class="policy-market-page">
    <div class="policy-market-page__grid">
      <ConsultationHistory :consultations="store.consultations" :selected-id="store.selectedConsultationId" @new-question="handleNewQuestion" @select="store.selectConsultation" />
      <main class="policy-market-page__consult">
        <header class="policy-market-page__hero"><p>POLICY INTELLIGENCE DESK · 01</p><h1>把政策读懂，<em>让决策先行。</em></h1><span>连接政策原文、市场信号与行业经验，帮你快速厘清影响、判断趋势。</span></header>
        <ConsultationComposer ref="composerRef" @submit-question="handleSubmit" />
        <p v-if="store.consultationsLoading" class="policy-market-page__notice" aria-live="polite">正在加载咨询记录</p>
        <p v-else-if="store.consultationsError" class="policy-market-page__notice policy-market-page__notice--error" aria-live="polite">{{ store.consultationsError }}</p>
        <ConsultationResult :consultation="store.selectedConsultation" />
        <p class="policy-market-page__source-note">回答基于公开政策文件与市场数据，具体结论请结合实际场景判断。</p>
      </main>
      <MarketPulse :filters="store.statsFilters" :stats="store.stats" :topic-options="store.topicOptions" :news="store.news" :loading="store.newsLoading" :error="store.newsError" :stats-loading="store.statsLoading" :stats-error="store.statsError" @filters-change="handleFiltersChange" />
    </div>
  </section>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { usePolicyMarketStore } from '@/store/modules/policyMarket'
import ConsultationHistory from './components/ConsultationHistory.vue'
import ConsultationComposer from './components/ConsultationComposer.vue'
import ConsultationResult from './components/ConsultationResult.vue'
import MarketPulse from './components/MarketPulse.vue'

const store = usePolicyMarketStore()
const composerRef = ref(null)
onMounted(() => { store.loadInitialData() })
async function handleNewQuestion() { store.startNewConsultation(); await nextTick(); composerRef.value?.focus() }
async function handleSubmit(question) { try { await store.submitQuestion(question) } catch (error) { ElMessage.error(error?.message || '咨询提交失败，请稍后重试') } }
function handleFiltersChange(filters) { store.setStatsFilters(filters) }
</script>

<style scoped>
.policy-market-page { min-height: 100%; padding: clamp(18px, 2.6vw, 36px) clamp(16px, 3vw, 48px); box-sizing: border-box; }
.policy-market-page__grid { min-height: calc(100vh - 64px - 72px); display: grid; grid-template-columns: 196px minmax(600px, 820px) 286px; justify-content: center; gap: clamp(22px, 3vw, 48px); align-items: start; }
.policy-market-page__consult { min-width: 0; display: flex; flex-direction: column; gap: var(--xc-space-4); }
.policy-market-page__hero { display: grid; gap: var(--xc-space-2); padding: clamp(10px, 1.5vh, 18px) 2px 18px; }
.policy-market-page__hero p { margin: 0; color: var(--xc-accent-blue); font-size: var(--xc-fs-2xs); letter-spacing: .08em; }
.policy-market-page__hero h1 { max-width: 720px; margin: 0; color: var(--xc-text-strong); font-size: clamp(34px, 3.4vw, var(--xc-fs-h1)); font-weight: var(--xc-fw-semi); line-height: 1.16; text-wrap: balance; }
.policy-market-page__hero h1 em { color: var(--xc-accent-blue); font-style: normal; }
.policy-market-page__hero span, .policy-market-page__notice { max-width: 620px; color: var(--xc-text-mute); font-size: var(--xc-fs-sm); line-height: var(--xc-lh-normal); }
.policy-market-page__notice { margin: 0; font-size: var(--xc-fs-xs); }
.policy-market-page__notice--error { color: var(--xc-status-danger); }
.policy-market-page__source-note { margin: 0; padding-inline: 2px; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); line-height: var(--xc-lh-normal); }
@media (max-width: 1180px) { .policy-market-page { overflow-y: auto; }.policy-market-page__grid { grid-template-columns: 188px minmax(0, 1fr) 270px; gap: 22px; } }
@media (max-width: 980px) { .policy-market-page__grid { min-height: auto; grid-template-columns: minmax(180px, 220px) minmax(0, 1fr); gap: 24px; }.policy-market-page__grid > :last-child { grid-column: 1 / -1; } }
@media (max-width: 720px) { .policy-market-page { padding: 12px 16px 24px; }.policy-market-page__grid { grid-template-columns: 1fr; gap: 18px; }.policy-market-page__grid > :last-child { grid-column: auto; }.policy-market-page__hero { padding-block: 12px 4px; }.policy-market-page__hero h1 { font-size: 30px; } }
</style>

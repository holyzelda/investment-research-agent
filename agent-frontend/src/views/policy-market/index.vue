<template>
  <section class="policy-market-page">
    <div class="policy-market-page__grid">
      <ConsultationHistory
        :consultations="store.consultations"
        :selected-id="store.selectedConsultationId"
        @new-question="handleNewQuestion"
        @select="store.selectConsultation"
      />

      <main class="policy-market-page__consult">
        <header class="policy-market-page__hero">
          <p>POLICY INTELLIGENCE DESK · 01</p>
          <h1>把政策读懂，<em>让决策先行。</em></h1>
          <span>连接政策原文、市场信号与行业经验，帮你快速厘清影响、判断趋势。</span>
        </header>
        <ConsultationComposer ref="composerRef" @submit-question="handleSubmit" />
        <p v-if="store.consultationsLoading" class="policy-market-page__notice" aria-live="polite">正在加载咨询记录</p>
        <p v-else-if="store.consultationsError" class="policy-market-page__notice policy-market-page__notice--error" aria-live="polite">{{ store.consultationsError }}</p>
        <ConsultationResult :consultation="store.selectedConsultation" />
        <p class="policy-market-page__source-note">回答基于公开政策文件与市场数据，具体结论请结合实际场景判断。</p>
      </main>

      <MarketPulse
        :filters="store.statsFilters"
        :stats="store.stats"
        :news="store.news"
        :loading="store.newsLoading"
        :error="store.newsError"
        :stats-loading="store.statsLoading"
        :stats-error="store.statsError"
        @filters-change="handleFiltersChange"
        @open-news="handleOpenNews"
      />
    </div>
    <NewsDetailDialog v-model="dialogVisible" :news="selectedNews" />
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { usePolicyMarketStore } from '@/store/modules/policyMarket'
import ConsultationHistory from './components/ConsultationHistory.vue'
import ConsultationComposer from './components/ConsultationComposer.vue'
import ConsultationResult from './components/ConsultationResult.vue'
import MarketPulse from './components/MarketPulse.vue'
import NewsDetailDialog from './components/NewsDetailDialog.vue'

const store = usePolicyMarketStore()
const composerRef = ref(null)
const dialogVisible = ref(false)
const selectedNewsId = ref(null)
const selectedNews = computed(() => store.news.find((item) => item.id === selectedNewsId.value) || null)

onMounted(() => {
  store.loadInitialData()
})

async function handleNewQuestion() {
  store.startNewConsultation()
  await nextTick()
  composerRef.value?.focus()
}

async function handleSubmit(question) {
  try {
    await store.submitQuestion(question)
  } catch (error) {
    ElMessage.error(error?.message || '咨询提交失败，请稍后重试')
  }
}

function handleFiltersChange(filters) {
  store.setStatsFilters(filters)
}

function handleOpenNews(id) {
  selectedNewsId.value = id
  dialogVisible.value = true
}
</script>

<style scoped>
.policy-market-page { min-height: 100%; padding: var(--xc-gutter-y) var(--xc-gutter-x); box-sizing: border-box; }
.policy-market-page__grid { min-height: calc(100vh - 64px - (var(--xc-gutter-y) * 2)); display: grid; grid-template-columns: 248px minmax(0, 1fr) 336px; gap: var(--xc-space-4); }
.policy-market-page__consult { min-width: 0; display: flex; flex-direction: column; gap: var(--xc-space-4); }
.policy-market-page__hero { display: grid; gap: var(--xc-space-2); padding: var(--xc-space-4) 0; }
.policy-market-page__hero p { margin: 0; color: var(--xc-accent-blue); font-size: var(--xc-fs-2xs); letter-spacing: 0.05em; }
.policy-market-page__hero h1 { margin: 0; color: var(--xc-text-strong); font-size: clamp(var(--xc-fs-h2), 3vw, var(--xc-fs-h1)); font-weight: var(--xc-fw-semi); line-height: var(--xc-lh-snug); }
.policy-market-page__hero h1 em { color: var(--xc-accent-blue); font-style: normal; }
.policy-market-page__hero span { color: var(--xc-text-mute); font-size: var(--xc-fs-sm); line-height: var(--xc-lh-normal); }
.policy-market-page__notice { margin: 0; color: var(--xc-text-mute); font-size: var(--xc-fs-xs); }
.policy-market-page__notice--error { color: var(--xc-status-danger); }
.policy-market-page__source-note { margin: 0; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); line-height: var(--xc-lh-normal); }
@media (max-width: 1180px) {
  .policy-market-page { overflow-y: auto; }
  .policy-market-page__grid { min-height: auto; grid-template-columns: 1fr; }
}
</style>

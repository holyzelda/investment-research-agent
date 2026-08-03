<template>
  <section class="index-map-page">
    <header class="index-map-page__header">
      <div class="index-map-page__title">
        <h1>全国储能投资指数</h1>
        <span>政策成熟度、收益稳定性与区域投资热度综合研判</span>
      </div>
    </header>

    <div v-if="store.periodsError" class="index-map-page__empty" role="alert">{{ store.periodsError }}</div>
    <div v-else class="index-map-page__body">
      <main class="index-map-page__main">
        <div class="index-map-page__map">
          <div v-if="store.overviewLoading" class="index-map-page__state" aria-live="polite">正在加载全国指数</div>
          <div v-else-if="store.overviewError" class="index-map-page__state" role="alert">
            <span>{{ store.overviewError }}</span>
            <button class="xc-btn xc-btn--ghost" type="button" @click="store.retryOverview">重试</button>
          </div>
          <ChinaIndexMap
            v-else
            :provinces="store.overview?.provinces || []"
            :selected-province-code="store.selectedProvinceCode"
            @select="store.selectProvince"
          />
        </div>
        <IndexSummaryCards :summary="store.overview?.summary" />
        <section class="index-map-page__rankings" aria-label="全国指数排行榜">
          <IndexRankingList title="投资热力榜" :items="store.overview?.rankings?.investmentHeat || []" value-key="indexScore" suffix="分" :selected-province-code="store.selectedProvinceCode" @select="store.selectProvince" />
          <IndexRankingList title="收益稳定榜" :items="store.overview?.rankings?.returnStability || []" value-key="annualizedReturn" suffix="分" :selected-province-code="store.selectedProvinceCode" @select="store.selectProvince" />
        </section>
      </main>
      <ProvinceIndexDetail :detail="store.provinceDetail" :loading="store.detailLoading" :error="store.detailError" @retry="store.retryDetail" />
    </div>
  </section>
</template>

<script setup>
import { onMounted } from 'vue'
import { useIndexMapStore } from '@/store/modules/indexMap'
import ChinaIndexMap from './components/ChinaIndexMap.vue'
import IndexSummaryCards from './components/IndexSummaryCards.vue'
import IndexRankingList from './components/IndexRankingList.vue'
import ProvinceIndexDetail from './components/ProvinceIndexDetail.vue'

const store = useIndexMapStore()
onMounted(() => store.initialize())
</script>

<style scoped>
.index-map-page { display: grid; grid-template-rows: auto minmax(0, 1fr); gap: 12px; height: 100%; min-height: 0; padding: 10px var(--xc-gutter-x) 16px; box-sizing: border-box; overflow: hidden; font-family: var(--xc-font-zh); }
.index-map-page__header { display: flex; align-items: center; min-height: 42px; padding-bottom: 10px; }
.index-map-page__title { display: flex; align-items: baseline; flex-wrap: wrap; gap: 6px 12px; min-width: 0; }
.index-map-page__header h1 { margin: 0; color: var(--xc-text-strong); font-size: 20px; font-weight: 600; line-height: 1.2; letter-spacing: 0; }
.index-map-page__title span { color: var(--xc-text-mute); font-size: 12px; line-height: 1.35; }
.index-map-page__body { display: grid; grid-template-columns: minmax(0, 1fr) clamp(340px, 25vw, 380px); gap: 12px; min-height: 0; overflow: hidden; }
.index-map-page__main { display: grid; grid-template-rows: minmax(300px, 1fr) auto auto; gap: 8px; min-width: 0; min-height: 0; }
.index-map-page__map { position: relative; min-height: 0; overflow: hidden; border: 1px solid var(--xc-border-soft); border-radius: 8px; background: rgba(20, 27, 31, 0.96); }
.index-map-page__state, .index-map-page__empty { display: grid; place-content: center; justify-items: center; gap: 12px; min-height: 320px; border: 1px solid var(--xc-border-soft); border-radius: 8px; background: var(--xc-surface-workspace); color: var(--xc-text-mute); font-size: 13px; }
.index-map-page__state { height: 100%; min-height: 0; border: 0; }
.index-map-page__rankings { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); border: 1px solid var(--xc-border-soft); border-radius: 8px; background: rgba(40, 48, 52, 0.72); overflow: hidden; }
.index-map-page__rankings :deep(.index-ranking + .index-ranking) { border-left: 1px solid var(--xc-border-soft); }
.index-map-page__map :deep(.china-index-map) { min-height: 0; }
@media (max-width: 1279px) { .index-map-page__body { grid-template-columns: minmax(0, 1fr) 330px; } }
@media (max-width: 1023px) {
  .index-map-page { height: auto; min-height: 100%; overflow: visible; }
  .index-map-page__body { grid-template-columns: 1fr; overflow: visible; }
  .index-map-page__main { grid-template-rows: clamp(420px, 56vh, 620px) auto auto; }
  .index-map-page :deep(.province-detail) { height: auto; max-height: none; overflow: visible; }
}
@media (max-width: 639px) {
  .index-map-page { gap: 10px; padding: 8px 10px 20px; }
  .index-map-page__main { grid-template-rows: 420px auto auto; }
  .index-map-page__rankings { grid-template-columns: 1fr; }
  .index-map-page__rankings :deep(.index-ranking + .index-ranking) { border-top: 1px solid var(--xc-border-soft); border-left: 0; }
}
</style>

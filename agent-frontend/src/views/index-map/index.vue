<template>
  <section class="index-map-page">
    <header class="index-map-page__header"><div><h1>全国储能投资指数</h1><p>按 S/A/B/C 类分级 · 政策市场解读 · 节点价差与潮流阻塞透视</p></div></header>
    <div v-if="store.periodsError" class="index-map-page__empty">{{ store.periodsError }}</div>
    <template v-else>
      <div class="index-map-page__body">
        <div class="index-map-page__main"><div class="index-map-page__map"><div v-if="store.overviewLoading" class="index-map-page__state">正在加载全国指数</div><div v-else-if="store.overviewError" class="index-map-page__state"><span>{{ store.overviewError }}</span><button class="xc-btn xc-btn--ghost" type="button" @click="store.retryOverview">重试</button></div><ChinaIndexMap v-else :provinces="store.overview?.provinces || []" :selected-province-code="store.selectedProvinceCode" @select="store.selectProvince" /></div><IndexSummaryCards :summary="store.overview?.summary" /><div class="index-map-page__rankings"><IndexRankingList title="投资热力榜" :items="store.overview?.rankings?.investmentHeat || []" value-key="indexScore" suffix="分" :selected-province-code="store.selectedProvinceCode" @select="store.selectProvince" /><IndexRankingList title="收益稳定榜" :items="store.overview?.rankings?.returnStability || []" :selected-province-code="store.selectedProvinceCode" @select="store.selectProvince" /></div></div>
        <ProvinceIndexDetail :detail="store.provinceDetail" :loading="store.detailLoading" :error="store.detailError" @retry="store.retryDetail" />
      </div>
    </template>
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
.index-map-page { position: relative; display: grid; grid-template-rows: auto minmax(0, 1fr); gap: var(--xc-space-2); height: 100%; min-height: 0; padding: var(--xc-space-2) var(--xc-gutter-x); box-sizing: border-box; overflow: hidden; background: transparent; font-family: var(--xc-font-zh); }
.index-map-page__header, .index-map-page__tabs, .index-map-page__body { position: relative; z-index: 1; }
.index-map-page__header, .index-map-page__tabs { display: flex; justify-content: space-between; align-items: center; gap: var(--xc-space-4); }
.index-map-page__header { min-height: 40px; padding: var(--xc-space-1) 0; }
.index-map-page__header h1 { margin: 0; color: var(--xc-text-strong); font-size: var(--xc-fs-lg); font-weight: var(--xc-fw-semi); line-height: var(--xc-lh-tight); }
.index-map-page__header p { margin: 2px 0 0; color: rgba(232, 206, 139, 0.66); font-size: var(--xc-fs-2xs); line-height: var(--xc-lh-tight); }
.index-map-page__tabs { padding-bottom: var(--xc-space-2); border-bottom: 1px solid var(--xc-border-card); }
.index-map-page__tabs button:not(.xc-btn) { border: 0; background: transparent; color: var(--xc-text-mute); cursor: pointer; }
.index-map-page__tabs .is-active { color: var(--xc-text-strong); border-bottom: 2px solid var(--xc-accent-blue); }
.index-map-page__tabs .xc-btn { margin-left: auto; }
.index-map-page__body { display: grid; grid-template-columns: minmax(0, 1fr) minmax(320px, 380px); gap: var(--xc-space-3); min-height: 0; overflow: hidden; }
.index-map-page__main { display: grid; grid-template-rows: minmax(0, 1fr) auto auto; gap: var(--xc-space-2); min-width: 0; min-height: 0; }
.index-map-page__map { position: relative; min-height: 0; }
.index-map-page__state, .index-map-page__empty { display: grid; place-content: center; justify-items: center; gap: var(--xc-space-3); min-height: 460px; border: 1px solid rgba(120, 198, 255, 0.2); border-radius: var(--xc-radius-lg); background: rgba(10, 18, 32, 0.72); box-shadow: var(--xc-shadow-md); color: var(--xc-text-mute); backdrop-filter: blur(14px); }
.index-map-page__rankings { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--xc-space-2); }
.index-map-page__map :deep(.china-index-map) { min-height: 0; }
@media (max-width: 900px) {
  .index-map-page { height: 100%; min-height: 0; padding: 6px 8px; overflow: hidden; }
  .index-map-page__header { min-height: 34px; padding: 4px 0; }
  .index-map-page__header h1 { font-size: var(--xc-fs-md); }
  .index-map-page__header p { margin-top: 1px; font-size: 10px; }
  .index-map-page__body { grid-template-columns: 1fr; grid-template-rows: minmax(0, 1.65fr) minmax(0, 1fr); gap: 6px; overflow: hidden; }
  .index-map-page__main { grid-template-rows: minmax(220px, 1fr) auto auto; gap: 5px; }
  .index-map-page__map, .index-map-page__map :deep(.china-index-map) { min-height: 0; }
  .index-map-page__rankings { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 5px; }
}
@media (max-width: 720px) {
  .index-map-page__rankings { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .index-summary-cards { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
</style>

<template>
  <section class="index-map-page">
    <header class="index-map-page__header"><div><h1>全国储能投资指数</h1><p>按 S/A/B/C 类分级 · 政策市场解读 · 节点价差与潮流阻塞透视</p></div><IndexPeriodSelect :periods="store.periods" :model-value="store.activePeriod" :loading="store.periodsLoading" @update:model-value="store.selectPeriod" /></header>
    <nav class="index-map-page__tabs"><button class="is-active" type="button">全国指数地图</button><button type="button" disabled>政策与市场</button><button type="button" disabled>区域节点分析</button><button class="xc-btn xc-btn--primary" type="button" @click="ElMessage.info('洞察简报功能将在后续开放')">导出洞察简报</button></nav>
    <div v-if="store.periodsError" class="index-map-page__empty">{{ store.periodsError }}</div>
    <template v-else>
      <div class="index-map-page__body">
        <div class="index-map-page__main"><div class="index-map-page__map"><div v-if="store.overviewLoading" class="index-map-page__state">正在加载全国指数</div><div v-else-if="store.overviewError" class="index-map-page__state"><span>{{ store.overviewError }}</span><button class="xc-btn xc-btn--ghost" type="button" @click="store.retryOverview">重试</button></div><ChinaIndexMap v-else :provinces="store.overview?.provinces || []" :selected-province-code="store.selectedProvinceCode" @select="store.selectProvince" /></div><IndexSummaryCards :summary="store.overview?.summary" /><div class="index-map-page__rankings"><IndexRankingList title="投资热力榜" :items="store.overview?.rankings?.investmentHeat || []" value-key="indexScore" suffix="分" :selected-province-code="store.selectedProvinceCode" @select="store.selectProvince" /><IndexRankingList title="收益稳定榜" :items="store.overview?.rankings?.returnStability || []" value-key="annualizedReturn" suffix="%" :selected-province-code="store.selectedProvinceCode" @select="store.selectProvince" /></div></div>
        <ProvinceIndexDetail :detail="store.provinceDetail" :loading="store.detailLoading" :error="store.detailError" @retry="store.retryDetail" />
      </div>
    </template>
  </section>
</template>
<script setup>
import { onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useIndexMapStore } from '@/store/modules/indexMap'
import ChinaIndexMap from './components/ChinaIndexMap.vue'
import IndexPeriodSelect from './components/IndexPeriodSelect.vue'
import IndexSummaryCards from './components/IndexSummaryCards.vue'
import IndexRankingList from './components/IndexRankingList.vue'
import ProvinceIndexDetail from './components/ProvinceIndexDetail.vue'
const store = useIndexMapStore()
onMounted(() => store.initialize())
</script>
<style scoped>
.index-map-page { display: grid; gap: var(--xc-space-3); min-height: 100%; padding: var(--xc-gutter-y) var(--xc-gutter-x); box-sizing: border-box; }.index-map-page__header, .index-map-page__tabs { display: flex; justify-content: space-between; align-items: center; gap: var(--xc-space-4); }.index-map-page__header h1 { margin: 0; color: var(--xc-text-strong); font-size: var(--xc-fs-h2); }.index-map-page__header p { margin: var(--xc-space-1) 0 0; color: var(--xc-text-mute); font-size: var(--xc-fs-xs); }.index-map-page__tabs { padding-bottom: var(--xc-space-2); border-bottom: 1px solid var(--xc-border-card); }.index-map-page__tabs button:not(.xc-btn) { border: 0; background: transparent; color: var(--xc-text-mute); cursor: pointer; }.index-map-page__tabs .is-active { color: var(--xc-text-strong); border-bottom: 2px solid var(--xc-accent-blue); }.index-map-page__tabs .xc-btn { margin-left: auto; }.index-map-page__body { display: grid; grid-template-columns: minmax(0, 1fr) minmax(320px, 400px); gap: var(--xc-space-3); min-height: 0; }.index-map-page__main { display: grid; gap: var(--xc-space-3); min-width: 0; }.index-map-page__map { position: relative; min-height: 460px; }.index-map-page__state, .index-map-page__empty { display: grid; place-content: center; justify-items: center; gap: var(--xc-space-3); min-height: 460px; border: 1px solid var(--xc-border-card); border-radius: var(--xc-radius-lg); color: var(--xc-text-mute); }.index-map-page__rankings { display: grid; grid-template-columns: 1fr 1fr; gap: var(--xc-space-3); }@media (max-width: 1100px) { .index-map-page__body { grid-template-columns: 1fr; }.index-map-page__header { align-items: start; flex-direction: column; }.province-detail { max-height: none; } }@media (max-width: 720px) { .index-map-page__rankings { grid-template-columns: 1fr; }.index-summary-cards { grid-template-columns: 1fr 1fr; } }
</style>

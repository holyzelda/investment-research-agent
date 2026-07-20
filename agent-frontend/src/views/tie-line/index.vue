<template>
  <section class="tie-line-page">
    <header class="tie-line-page__top">
      <div class="tie-line-page__heading">
        <h2 class="tie-line-page__title">跨省跨区</h2>
        <p class="tie-line-page__subtitle">全国跨省跨区联络线分布</p>
      </div>
      <TieLineStatsBar :stats="store.stats" />
    </header>

    <TieLineFilterBar
      :start-region="store.activeStartRegion"
      :end-region="store.activeEndRegion"
      :region-options="store.filters.regionOptions"
      @update:start-region="store.setStartRegion"
      @update:end-region="store.setEndRegion"
    />

    <div class="tie-line-page__body">
      <div class="tie-line-page__map-wrap">
        <div v-if="store.loading" class="tie-line-page__state">联络线加载中…</div>
        <div v-else-if="store.error" class="tie-line-page__state">{{ store.error }}</div>
        <ChinaTieLineMap
          v-else
          :lines="store.visibleLines"
          :selected-id="store.selectedId"
          :voltage-options="store.filters.voltageOptions"
          @select="store.selectLine"
        />
        <div class="tie-line-page__map-note">箭头表示线路资料起点至终点，不代表实时潮流或功率方向</div>
      </div>
      <TieLineDetailPanel
        class="tie-line-page__detail"
        :line="store.detail"
        :recommended-line="store.recommendedLine"
        :accent-token="detailAccentToken"
      />
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useTieLineStore } from '@/store/modules/tieLine'
import { buildVoltagePresentation } from './voltagePresentation'
import ChinaTieLineMap from './components/ChinaTieLineMap.vue'
import TieLineStatsBar from './components/TieLineStatsBar.vue'
import TieLineFilterBar from './components/TieLineFilterBar.vue'
import TieLineDetailPanel from './components/TieLineDetailPanel.vue'

const store = useTieLineStore()

const detailAccentToken = computed(() => {
  const { tokenByText } = buildVoltagePresentation(store.filters.voltageOptions)
  const displayLine = store.detail || store.recommendedLine
  return tokenByText[displayLine?.voltageText] || '--xc-map-voltage-unknown'
})

onMounted(() => {
  store.loadLines()
})
</script>

<style scoped>
.tie-line-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--xc-space-4, 16px);
  padding: var(--xc-space-4, 16px) var(--xc-gutter-x, 24px);
  box-sizing: border-box;
}
.tie-line-page__top {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--xc-space-6, 24px);
  flex-wrap: wrap;
}
.tie-line-page__title {
  font-size: var(--xc-fs-h2, 24px);
  font-weight: var(--xc-fw-semi, 600);
  color: var(--xc-text-strong);
  margin: 0;
}
.tie-line-page__subtitle {
  font-size: var(--xc-fs-2xs, 12px);
  color: var(--xc-text-mute);
  margin: 2px 0 0;
}
.tie-line-page__body {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  gap: var(--xc-space-4, 16px);
}
.tie-line-page__map-wrap {
  position: relative;
  flex: 1 1 auto;
  min-width: 0;
  background: var(--xc-map-ocean);
  border-radius: var(--xc-radius-md, 10px);
  overflow: hidden;
}
.tie-line-page__map-note {
  position: absolute;
  left: 16px;
  bottom: 16px;
  max-width: 260px;
  padding: 6px 10px;
  border: 1px solid var(--xc-map-legend-border);
  border-radius: var(--xc-radius-sm, 8px);
  background: var(--xc-map-legend-bg);
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-3xs, 10px);
  line-height: var(--xc-lh-snug, 1.3);
}
.tie-line-page__detail {
  flex: 0 0 300px;
}
.tie-line-page__state {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--xc-text-mute);
}
</style>

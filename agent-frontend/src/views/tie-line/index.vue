<template>
  <section class="tie-line-page">
    <header class="tie-line-page__header">
      <div class="tie-line-page__heading">
        <h2 class="tie-line-page__title">跨省跨区联络线</h2>
      </div>
      <TieLineStatsBar :stats="store.stats" />
    </header>

    <TieLineFilterBar
      :start-region="store.activeStartRegion"
      :end-region="store.activeEndRegion"
      :min-capacity-mw="store.activeMinCapacityMw"
      :max-capacity-mw="store.activeMaxCapacityMw"
      :region-options="store.filters.regionOptions"
      @update:start-region="store.setStartRegion"
      @update:end-region="store.setEndRegion"
      @update:min-capacity-mw="store.setMinCapacityMw"
      @update:max-capacity-mw="store.setMaxCapacityMw"
      @swap-regions="store.swapRegions"
      @reset-filters="store.resetFilters"
    />

    <div class="tie-line-page__body">
      <div class="tie-line-page__map-wrap">
        <div v-if="store.loading" class="tie-line-page__state tie-line-page__state--loading" aria-live="polite">
          <span class="xc-skeleton xc-skeleton-rect tie-line-page__skeleton" aria-hidden="true" />
          <span>正在加载联络线资料</span>
        </div>
        <div v-else-if="store.error" class="tie-line-page__state tie-line-page__state--error" role="alert">
          <strong>数据加载失败</strong>
          <span>{{ store.error }}</span>
          <button class="xc-btn xc-btn--ghost" type="button" @click="store.loadLines">重试</button>
        </div>
        <template v-else>
          <ChinaTieLineMap
            :lines="store.visibleLines"
            :selected-id="store.selectedId"
            :voltage-options="store.filters.voltageOptions"
            @select="store.selectLine"
          />
          <div v-if="hasNoVisibleLines" class="tie-line-page__empty" aria-live="polite">
            <strong>未找到匹配的数据</strong>
            <span>尝试调整筛选条件</span>
            <button class="xc-btn xc-btn--ghost" type="button" @click="store.resetFilters">清空筛选</button>
          </div>
        </template>
      </div>
      <TieLineDetailPanel
        class="tie-line-page__detail"
        :line="store.detail"
        :recommended-line="store.recommendedLine"
        :no-visible-lines="hasNoVisibleLines"
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

const hasNoVisibleLines = computed(() =>
  !store.loading && !store.error && store.lines.length > 0 && store.visibleLines.length === 0,
)

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
.tie-line-page { height: 100%; display: flex; flex-direction: column; gap: var(--xc-gutter-y); padding: var(--xc-gutter-y) var(--xc-gutter-x); box-sizing: border-box; }
.tie-line-page__header { display: flex; align-items: flex-end; justify-content: space-between; gap: var(--xc-space-7); }
.tie-line-page__heading { min-width: 0; }
.tie-line-page__eyebrow { margin: 0; color: var(--xc-accent-blue); font-size: var(--xc-fs-2xs); letter-spacing: 0.04em; }
.tie-line-page__title { margin: var(--xc-space-1) 0 0; color: var(--xc-text-strong); font-size: var(--xc-fs-h2); font-weight: var(--xc-fw-semi); line-height: var(--xc-lh-snug); }
.tie-line-page__subtitle { margin: var(--xc-space-1) 0 0; color: var(--xc-text-mute); font-size: var(--xc-fs-xs); }
.tie-line-page__body { flex: 1 1 auto; min-height: 0; display: grid; grid-template-columns: minmax(0, 1fr) 360px; gap: var(--xc-space-4); }
.tie-line-page__map-wrap { position: relative; min-width: 0; min-height: 0; overflow: hidden; background: var(--xc-map-ocean); border-radius: var(--xc-radius-md); }
.tie-line-page__detail { min-width: 0; }
.tie-line-page__state,
.tie-line-page__empty { position: absolute; inset: 0; z-index: var(--xc-z-raised); display: grid; place-content: center; justify-items: center; gap: var(--xc-space-3); padding: var(--xc-space-7); color: var(--xc-text-mute); text-align: center; }
.tie-line-page__state--loading { background: var(--xc-surface-base); }
.tie-line-page__state--error,
.tie-line-page__empty { background: var(--xc-surface-overlay); }
.tie-line-page__state strong,
.tie-line-page__empty strong { color: var(--xc-text-strong); font-size: var(--xc-fs-md); }
.tie-line-page__skeleton { width: min(70%, 520px); height: min(48%, 360px); border-radius: var(--xc-radius-md); }
@media (max-width: 1440px) {
  .tie-line-page__header { align-items: flex-start; }
  .tie-line-page__body { grid-template-columns: minmax(0, 1fr) 320px; }
  .tie-line-page__heading { max-width: 420px; }
}
</style>

<template>
  <section class="tie-line-page">
    <header class="tie-line-page__header">
      <div class="tie-line-page__heading">
        <h2 class="tie-line-page__title">跨省跨区联络线</h2>
        <p class="tie-line-page__subtitle">全国跨区输电网络 · 容量 · 路径 · 功率趋势</p>
      </div>
      <TieLineFilterBar
        class="tie-line-page__filters"
        :start-region="store.activeStartRegion"
        :end-region="store.activeEndRegion"
        :min-capacity-mw="store.activeMinCapacityMw"
        :max-capacity-mw="store.activeMaxCapacityMw"
        :region-options="store.filters.regionOptions"
        :visible-count="store.visibleLines.length"
        :total-count="store.lines.length"
        @update:start-region="store.setStartRegion"
        @update:end-region="store.setEndRegion"
        @update:min-capacity-mw="store.setMinCapacityMw"
        @update:max-capacity-mw="store.setMaxCapacityMw"
        @swap-regions="store.swapRegions"
        @reset-filters="store.resetFilters"
      />
      <TieLineStatsBar :stats="store.stats" />
    </header>

    <div class="tie-line-page__notice-row">
      <div v-if="showNoResultNotice" class="tie-line-page__notice" role="status" aria-live="polite">
        <strong>未找到符合条件的联络线</strong>
        <span>请调整起点、终点或额定容量条件</span>
      </div>
    </div>

    <div class="tie-line-page__body">
      <div class="tie-line-page__map-wrap">
        <div v-if="isBlockingLoading" class="tie-line-page__state tie-line-page__state--loading" aria-live="polite">
          <span class="xc-skeleton xc-skeleton-rect tie-line-page__skeleton" aria-hidden="true" />
          <span>正在加载联络线资料</span>
        </div>
        <div v-else-if="isBlockingError" class="tie-line-page__state tie-line-page__state--error" role="alert">
          <strong>数据加载失败</strong>
          <span>{{ store.error }}</span>
          <button class="xc-btn xc-btn--ghost" type="button" @click="store.loadLines({ force: true })">重试</button>
        </div>
        <template v-else>
          <ChinaTieLineMap
            :lines="store.visibleLines"
            :selected-id="store.selectedId"
            :voltage-options="store.filters.voltageOptions"
            @select="store.selectLine"
          />
        </template>
      </div>
      <TieLineDetailPanel
        class="tie-line-page__detail"
        :line="store.detail"
        :recommended-line="store.recommendedLine"
        :no-visible-lines="hasNoVisibleLines"
        :accent-token="detailAccentToken"
        :power-trend="store.powerTrend"
        :power-range="store.powerRange"
        :power-trend-loading="store.powerTrendLoading"
        :power-trend-error="store.powerTrendError"
        @power-range-change="({ key, ...range }) => store.setPowerRange(key, range)"
        @retry-power-trend="store.loadPowerTrend()"
      />
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useTieLineStore } from '@/store/modules/tieLine'
import { buildVoltagePresentation } from './voltagePresentation'
import ChinaTieLineMap from './components/ChinaTieLineMap.vue'
import TieLineStatsBar from './components/TieLineStatsBar.vue'
import TieLineFilterBar from './components/TieLineFilterBar.vue'
import TieLineDetailPanel from './components/TieLineDetailPanel.vue'

const store = useTieLineStore()
const showNoResultNotice = ref(false)
let noResultTimer = null

const hasNoVisibleLines = computed(() =>
  !store.loading && !store.error && store.lines.length > 0 && store.visibleLines.length === 0,
)
const isBlockingLoading = computed(() => store.loading && !store.loaded)
const isBlockingError = computed(() => store.error && !store.loaded)

watch(hasNoVisibleLines, (visible) => {
  window.clearTimeout(noResultTimer)
  if (!visible) {
    showNoResultNotice.value = false
    return
  }
  showNoResultNotice.value = true
  noResultTimer = window.setTimeout(() => {
    showNoResultNotice.value = false
  }, 2000)
})

watch(
  () => [store.recommendedLine?.id, store.selectedId],
  ([recommendedId, selectedId]) => {
    if (selectedId == null && recommendedId != null) store.loadRecommendedPowerTrend()
  },
)

const detailAccentToken = computed(() => {
  const { tokenByText } = buildVoltagePresentation(store.filters.voltageOptions)
  const displayLine = store.detail || store.recommendedLine
  return tokenByText[displayLine?.voltageText] || '--xc-map-voltage-unknown'
})

onMounted(() => {
  if (store.loaded) {
    store.loadLines({ force: true, silent: true })
    return
  }
  store.loadLines()
})

onBeforeUnmount(() => {
  window.clearTimeout(noResultTimer)
})
</script>

<style scoped>
.tie-line-page { --tl-detail-width: clamp(360px, 29vw, 420px); position: relative; isolation: isolate; height: 100%; min-height: 640px; box-sizing: border-box; overflow: hidden; background: var(--xc-surface-raised); }
.tie-line-page__header { position: absolute; top: var(--xc-gutter-y); left: var(--xc-gutter-x); right: var(--xc-gutter-x); z-index: 30; display: grid; grid-template-columns: minmax(210px, 0.48fr) minmax(520px, 1.62fr) auto; align-items: center; gap: clamp(12px, 1.2vw, 22px); pointer-events: none; }
.tie-line-page__header > * { pointer-events: auto; }
.tie-line-page__heading { min-width: 0; }
.tie-line-page__eyebrow { margin: 0; color: var(--xc-accent-blue); font-size: var(--xc-fs-2xs); letter-spacing: 0.04em; }
.tie-line-page__title { margin: var(--xc-space-1) 0 0; color: var(--xc-text-strong); font-size: clamp(24px, 1.45rem, 28px); font-weight: var(--xc-fw-semi); line-height: var(--xc-lh-snug); text-shadow: 0 10px 34px rgba(88, 214, 207, 0.16); }
.tie-line-page__subtitle { margin: var(--xc-space-1) 0 0; color: rgba(232, 206, 139, 0.66); font-size: var(--xc-fs-xs); }
.tie-line-page__filters { min-width: 0; justify-self: stretch; }
.tie-line-page__notice-row { position: absolute; top: 78px; left: var(--xc-gutter-x); z-index: 31; display: flex; align-items: center; pointer-events: none; }
.tie-line-page__body { position: absolute; inset: 0; min-width: 0; min-height: 0; }
.tie-line-page__body::after { content: ''; position: absolute; top: 0; right: 0; bottom: 0; z-index: 8; width: min(520px, 38vw); pointer-events: none; background: linear-gradient(90deg, transparent 0%, color-mix(in srgb, var(--xc-surface-raised) 72%, transparent) 22%, var(--xc-surface-raised) 100%); }
.tie-line-page__map-wrap { position: absolute; inset: 0; z-index: 1; min-width: 0; min-height: 0; overflow: visible; background: transparent; }
.tie-line-page__detail { position: absolute; top: 138px; right: var(--xc-gutter-x); bottom: var(--xc-space-5); z-index: 20; width: var(--tl-detail-width); min-width: 0; }
.tie-line-page :deep(.china-tie-line-map__signature) { top: 138px; left: var(--xc-gutter-x); }
.tie-line-page :deep(.china-tie-line-map__tools) { top: 96px; right: calc(var(--tl-detail-width) + 52px); }
.tie-line-page :deep(.china-tie-line-map__list) { top: 140px; right: calc(var(--tl-detail-width) + 52px); }
.tie-line-page :deep(.china-tie-line-map__legend),
.tie-line-page :deep(.china-tie-line-map__note) { left: var(--xc-gutter-x); }
.tie-line-page__state { position: absolute; inset: 0; z-index: var(--xc-z-raised); display: grid; place-content: center; justify-items: center; gap: var(--xc-space-3); padding: var(--xc-space-7); color: var(--xc-text-mute); text-align: center; }
.tie-line-page__state--loading { background: transparent; }
.tie-line-page__state--error { background: var(--xc-surface-overlay); }
.tie-line-page__state strong { color: var(--xc-text-strong); font-size: var(--xc-fs-md); }
.tie-line-page__notice { display: grid; gap: var(--xc-space-1); width: 360px; max-width: 31vw; padding: var(--xc-space-3) var(--xc-space-4); border: 1px solid var(--xc-border-accent); border-radius: var(--xc-radius-md); background: linear-gradient(135deg, var(--xc-surface-raised), color-mix(in srgb, var(--xc-accent-blue) 16%, var(--xc-surface-raised))); box-shadow: var(--xc-glow-blue), var(--xc-shadow-md); color: var(--xc-text-soft); text-align: left; animation: tl-notice-slide 180ms var(--xc-ease-out); pointer-events: none; }
.tie-line-page__notice strong { color: var(--xc-text-strong); font-size: var(--xc-fs-sm); font-weight: var(--xc-fw-semi); }
.tie-line-page__notice span { color: var(--xc-text-soft); font-size: var(--xc-fs-2xs); }
.tie-line-page__skeleton { display: none; }
@keyframes tl-notice-slide {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}
@media (max-width: 1440px) {
  .tie-line-page__header { grid-template-columns: minmax(190px, 0.44fr) minmax(470px, 1.5fr) auto; align-items: center; gap: var(--xc-space-3); }
  .tie-line-page__heading { max-width: 360px; }
}
@media (max-width: 1180px) {
  .tie-line-page { --tl-detail-width: auto; min-height: 1040px; overflow-y: auto; }
  .tie-line-page__header { right: var(--xc-gutter-x); grid-template-columns: 1fr; align-items: start; gap: var(--xc-space-3); }
  .tie-line-page__filters { justify-self: stretch; }
  .tie-line-page__notice-row { top: 220px; right: var(--xc-gutter-x); }
  .tie-line-page__notice { width: auto; max-width: none; }
  .tie-line-page__body { min-height: 1040px; }
  .tie-line-page__body::after { display: none; }
  .tie-line-page__map-wrap { inset: 0 0 auto; height: 620px; min-height: 620px; }
  .tie-line-page__detail { top: 620px; left: var(--xc-gutter-x); right: var(--xc-gutter-x); bottom: auto; width: auto; min-height: 380px; }
  .tie-line-page :deep(.china-tie-line-map__tools) { top: 244px; right: var(--xc-gutter-x); }
  .tie-line-page :deep(.china-tie-line-map__list) { top: 288px; right: var(--xc-gutter-x); }
}
</style>

<template>
  <aside class="tl-detail">
    <template v-if="displayLine">
      <header class="tl-profile__head">
        <div class="tl-profile__identity">
          <span class="tl-profile__eyebrow">线路档案</span>
          <h3 class="tl-profile__name" :style="{ color: `var(${accentToken})` }">{{ displayLine.name }}</h3>
          <p class="tl-profile__type">{{ lineTypeText }}</p>
        </div>
      </header>

      <section class="tl-mini-route" :style="{ '--tl-accent': `var(${accentToken})` }" aria-label="线路起讫路径">
        <div class="tl-mini-route__station tl-mini-route__station--start">
          <span class="tl-mini-route__dot" aria-hidden="true" />
          <strong>{{ displayLine.startPoint || '—' }}</strong>
          <small>{{ displayLine.startRegion || '—' }}</small>
        </div>
        <div class="tl-mini-route__link" aria-hidden="true"><span /></div>
        <div class="tl-mini-route__station tl-mini-route__station--end">
          <span class="tl-mini-route__dot" aria-hidden="true" />
          <strong>{{ displayLine.endPoint || '—' }}</strong>
          <small>{{ displayLine.endRegion || '—' }}</small>
        </div>
      </section>

      <dl class="tl-metric-strip" aria-label="线路关键指标">
        <div class="tl-metric-strip__item"><dt>额定容量</dt><dd class="xc-num">{{ capText }}</dd></div>
        <div class="tl-metric-strip__item"><dt>电压等级</dt><dd class="xc-num">{{ displayLine.voltageText || '—' }}</dd></div>
        <div class="tl-metric-strip__item"><dt>线路长度</dt><dd class="xc-num">{{ displayLine.lengthText || '—' }}</dd></div>
        <div class="tl-metric-strip__item"><dt>投运年份</dt><dd class="xc-num">{{ displayLine.operationYear || '—' }}</dd></div>
      </dl>

      <section v-if="basisSummary" class="tl-data-basis">
        <button class="tl-data-basis__toggle" type="button" @click="basisOpen = !basisOpen">
          <span>数据口径</span>
          <strong class="tl-data-basis__summary">{{ basisSummary }}</strong>
          <em>{{ basisOpen ? '收起' : '展开' }}</em>
        </button>
        <div v-if="basisOpen" class="tl-data-basis__body">
          <p v-if="displayLine.coordinateBasis">坐标基准：{{ displayLine.coordinateBasis }}</p>
          <p v-if="displayLine.dataBasisNote">数据说明：{{ displayLine.dataBasisNote }}</p>
          <p v-if="displayLine.sourceNote">来源备注：{{ displayLine.sourceNote }}</p>
        </div>
      </section>

      <TieLinePowerTrend
        v-if="displayLine"
        :trend="powerTrend"
        :range="powerRange"
        :loading="powerTrendLoading"
        :error="powerTrendError"
        :accent-token="accentToken"
        :rated-capacity-mw="displayLine.ratedCapacityMw"
        @range-change="$emit('power-range-change', $event)"
        @retry="$emit('retry-power-trend')"
      />
    </template>

    <div v-else class="tl-detail__placeholder">
      {{ noVisibleLines ? '当前筛选条件下暂无线路' : '点击地图上的联络线查看线路详情' }}
    </div>
  </aside>
</template>

<script setup>
import { computed, ref } from 'vue'
import TieLinePowerTrend from './TieLinePowerTrend.vue'

const props = defineProps({
  line: { type: Object, default: null },
  recommendedLine: { type: Object, default: null },
  noVisibleLines: { type: Boolean, default: false },
  accentToken: { type: String, default: '--xc-map-voltage-unknown' },
  powerTrend: { type: Object, default: null },
  powerRange: { type: Object, default: () => ({}) },
  powerTrendLoading: { type: Boolean, default: false },
  powerTrendError: { type: String, default: '' },
})

defineEmits(['power-range-change', 'retry-power-trend'])

const displayLine = computed(() => props.line || props.recommendedLine)
const capText = computed(() =>
  displayLine.value && displayLine.value.ratedCapacityMw != null
    ? `${Number(displayLine.value.ratedCapacityMw).toLocaleString('zh-CN')} MW`
    : '—',
)
const lineTypeText = computed(() => {
  const voltage = displayLine.value?.voltageText || ''
  const name = displayLine.value?.name || ''
  return voltage.includes('±') || name.includes('直流') ? '跨区直流输电线路' : '跨区交流输电线路'
})
const basisOpen = ref(false)
const basisSummary = computed(() => {
  if (!displayLine.value) return ''
  return [displayLine.value.coordinateBasis, displayLine.value.dataBasisNote].filter(Boolean).join(' · ')
})
</script>

<style scoped>
.tl-detail {
  height: 100%;
  box-sizing: border-box;
  padding: var(--xc-space-4);
  overflow-y: auto;
  background: var(--xc-surface-1);
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-md);
}
.tl-profile__head { display:flex; align-items:flex-start; justify-content:space-between; gap:var(--xc-space-3); }
.tl-profile__identity { min-width:0; }
.tl-profile__eyebrow { display:block; color:var(--xc-text-mute); font-size:12px; }
.tl-profile__name { margin:var(--xc-space-1) 0 0; font-size:var(--xc-fs-h3); font-weight:var(--xc-fw-semi); line-height:var(--xc-lh-snug); overflow-wrap:anywhere; }
.tl-profile__type { margin:var(--xc-space-1) 0 0; color:var(--xc-text-soft); font-size:var(--xc-fs-xs); line-height:var(--xc-lh-normal); }
.tl-mini-route { display:grid; grid-template-columns:minmax(0, 1fr) 52px minmax(0, 1fr); align-items:start; gap:var(--xc-space-2); margin-top:var(--xc-space-5); }
.tl-mini-route__station { min-width:0; display:grid; grid-template-columns:auto minmax(0, 1fr); column-gap:var(--xc-space-2); row-gap:var(--xc-space-1); color:var(--xc-text-strong); }
.tl-mini-route__station strong { overflow-wrap:anywhere; line-height:var(--xc-lh-snug); }
.tl-mini-route__station small { grid-column:2; color:var(--xc-text-mute); font-size:12px; line-height:var(--xc-lh-normal); overflow-wrap:anywhere; }
.tl-mini-route__dot { width:9px; height:9px; margin-top:0.35em; border-radius:999px; background:var(--tl-accent); box-shadow:0 0 0 3px var(--xc-surface-1); }
.tl-mini-route__link { position:relative; height:24px; margin-top:0.15em; }
.tl-mini-route__link::before { content:''; position:absolute; left:0; right:8px; top:8px; border-top:1px solid var(--tl-accent); }
.tl-mini-route__link::after { content:'▶'; position:absolute; right:0; top:1px; color:var(--tl-accent); font-size:10px; }
.tl-metric-strip { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:var(--xc-space-3); margin:var(--xc-space-4) 0 0; }
.tl-metric-strip__item { min-width:0; padding:var(--xc-space-3); background:var(--xc-surface-tinted); border:1px solid var(--xc-border-soft); border-radius:var(--xc-radius-sm); }
.tl-metric-strip__item + .tl-metric-strip__item::before { display:none; }
.tl-metric-strip dt { color:var(--xc-text-mute); font-size:12px; }
.tl-metric-strip dd { margin:var(--xc-space-1) 0 0; color:var(--xc-text-strong); font-size:18px; font-weight:600; line-height:var(--xc-lh-snug); overflow-wrap:anywhere; }
.tl-data-basis { margin-top:var(--xc-space-4); }
.tl-data-basis__toggle { width:100%; display:grid; grid-template-columns:auto minmax(0, 1fr) auto; gap:var(--xc-space-2); align-items:start; padding:0; color:var(--xc-text-mute); background:transparent; border:0; text-align:left; cursor:pointer; font-size:12px; }
.tl-data-basis__summary { color:var(--xc-text-soft); font-weight:var(--xc-fw-regular); overflow-wrap:anywhere; }
.tl-data-basis__toggle em { color:var(--xc-accent-blue); font-style:normal; }
.tl-data-basis__body { display:grid; gap:var(--xc-space-1); margin-top:var(--xc-space-2); color:var(--xc-text-mute); font-size:12px; line-height:var(--xc-lh-normal); }
.tl-data-basis__body p { margin:0; overflow-wrap:anywhere; }
.tl-detail__placeholder { height: 100%; display: grid; place-items: center; color: var(--xc-text-mute); font-size: var(--xc-fs-sm); text-align: center; }
@media (max-width: 1180px) {
  .tl-detail { height:auto; }
  .tl-mini-route { grid-template-columns:1fr; }
  .tl-mini-route__link { width:24px; height:38px; margin-left:4px; }
  .tl-mini-route__link::before { left:4px; right:auto; top:0; bottom:8px; border-top:0; border-left:1px solid var(--tl-accent); }
  .tl-mini-route__link::after { left:0; right:auto; top:auto; bottom:0; content:'▼'; }
  .tl-metric-strip { grid-template-columns:1fr; gap:var(--xc-space-3); }
  .tl-metric-strip__item { padding:0; }
  .tl-metric-strip__item + .tl-metric-strip__item::before { display:none; }
}
</style>

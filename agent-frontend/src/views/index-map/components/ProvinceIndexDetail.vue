<template>
  <aside class="province-detail">
    <div v-if="loading" class="province-detail__state">正在加载省份详情</div>
    <div v-else-if="error" class="province-detail__state"><span>{{ error }}</span><button class="xc-btn xc-btn--ghost" type="button" @click="$emit('retry')">重试</button></div>
    <div v-else-if="!detail" class="province-detail__state">该期次暂无省份详情</div>
    <template v-else>
      <header><div><h2>{{ detail.provinceName }}</h2><p>{{ detail.regionDescription || '—' }}</p></div><strong class="province-detail__grade">{{ detail.grade || '—' }}</strong></header>
      <section class="province-detail__score"><strong class="xc-num">{{ formatNumber(detail.indexScore) }}</strong><span>/ 100</span><div><b>{{ detail.investmentAdvice || '—' }}</b></div></section>
      <section><h3>归因分析 · 市场化成熟度</h3><p>{{ detail.maturity?.summary || '—' }}</p><div class="province-detail__grid"><article v-for="item in detail.maturity?.scores || []" :key="item.key"><span>{{ item.label }}</span><strong class="xc-num">{{ formatNumber(item.score) }}</strong></article></div></section>
      <section><h3>归因分析 · 因子贡献度</h3><div v-for="item in detail.factorContributions || []" :key="item.key" class="province-detail__bar"><span>{{ item.label }}</span><i><b :style="{ width: `${item.value || 0}%` }" /></i><strong class="xc-num">+{{ formatNumber(item.delta) }}</strong></div></section>
      <section class="province-detail__installed">
        <h3>装机结构 · 在运 <b class="xc-num">合计 {{ formatNumber(detail.installedStructure?.totalGw) }} GW</b></h3>
        <article
          v-for="item in detail.installedStructure?.items || []"
          :key="item.key"
          :class="['province-detail__capacity', `province-detail__capacity--${item.key}`]"
        >
          <i class="province-detail__capacity-mark" aria-hidden="true" />
          <div class="province-detail__capacity-info">
            <div><strong>{{ item.label }}</strong><span>{{ formatNumber(item.share) }}%</span></div>
            <small v-if="item.key === 'renewable' && item.windShare != null && item.solarShare != null">
              风电 {{ formatNumber(item.windShare) }}% · 光伏 {{ formatNumber(item.solarShare) }}%
            </small>
            <small v-else>{{ item.description || '—' }}</small>
          </div>
          <div class="province-detail__capacity-value">
            <strong class="xc-num">{{ formatCapacity(item.capacityGw) }} <small>GW</small></strong>
            <span v-if="item.deltaText" :class="{ 'is-down': item.deltaText.startsWith('↓') }">{{ item.deltaText }}</span>
          </div>
        </article>
      </section>
      <p class="province-detail__analysis">{{ detail.analysisText || '—' }}</p>
    </template>
  </aside>
</template>
<script setup>
import { formatNumber } from '@/utils/formatNumber'

function formatCapacity(value) {
  if (value === null || value === undefined || value === '') return '—'
  const number = Number(value)
  if (!Number.isFinite(number)) return String(value)
  return String(Number(number.toFixed(3)))
}

defineProps({ detail: { type: Object, default: null }, loading: Boolean, error: { type: String, default: '' } })
defineEmits(['retry'])
</script>
<style scoped>
.province-detail { display: grid; align-content: start; gap: var(--xc-space-3); min-height: 0; height: 100%; padding: var(--xc-space-4); box-sizing: border-box; border: 1px solid rgba(120, 198, 255, 0.2); border-radius: var(--xc-radius-lg); background: linear-gradient(155deg, rgba(255, 255, 255, 0.09), rgba(255, 255, 255, 0.035) 48%, rgba(34, 177, 253, 0.055)); box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08), 0 20px 56px rgba(0, 0, 0, 0.3); overflow-y: auto; backdrop-filter: blur(16px); }
.province-detail__state { display: grid; place-items: center; gap: var(--xc-space-3); min-height: 240px; color: var(--xc-text-mute); }
header, .province-detail__score { display: flex; justify-content: space-between; gap: var(--xc-space-3); }
h2, h3, p { margin: 0; } h2 { color: var(--xc-text-strong); font-size: var(--xc-fs-h2); line-height: var(--xc-lh-tight); } h3 { color: var(--xc-text-soft); font-size: var(--xc-fs-xs); } p, small { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.province-detail__grade { display: grid; place-items: center; flex: 0 0 auto; width: 40px; height: 40px; border: 2px solid rgba(255, 170, 0, 0.8); border-radius: 50%; background: rgba(255, 170, 0, 0.1); box-shadow: 0 0 26px rgba(255, 170, 0, 0.24); color: var(--xc-text-strong); }
.province-detail__score { align-items: center; padding: var(--xc-space-3) var(--xc-space-4); border: 1px solid rgba(34, 177, 253, 0.24); border-radius: var(--xc-radius-md); background: linear-gradient(120deg, rgba(34, 177, 253, 0.13), rgba(255, 170, 0, 0.07)); } .province-detail__score > strong { color: var(--xc-text-strong); font-size: var(--xc-fs-xl); line-height: var(--xc-lh-tight); text-shadow: 0 0 22px rgba(34, 177, 253, 0.32); } .province-detail__score div { display: grid; justify-items: end; } .province-detail__score b { color: #8fdcff; } .province-detail__score em { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); font-style: normal; }
section { display: grid; gap: var(--xc-space-2); } h3 b { float: right; color: var(--xc-text-strong); }
.province-detail__grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--xc-space-2); } .province-detail__grid article { display: grid; gap: 1px; padding: var(--xc-space-2) var(--xc-space-3); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: var(--xc-radius-sm); background: rgba(255, 255, 255, 0.035); } .province-detail__grid span { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); } .province-detail__grid strong { color: var(--xc-text-strong); }
.province-detail__capacity { --capacity-color: #29d5bb; display: grid; grid-template-columns: 4px minmax(0, 1fr) auto; align-items: stretch; gap: var(--xc-space-2); min-height: 48px; padding: 7px 10px 7px 7px; box-sizing: border-box; border: 1px solid rgba(255, 255, 255, 0.11); border-radius: var(--xc-radius-sm); background: rgba(7, 18, 37, 0.52); }
.province-detail__capacity--thermal { --capacity-color: #ff9e4a; }
.province-detail__capacity--storage { --capacity-color: #a98bff; }
.province-detail__capacity-mark { width: 4px; height: 100%; min-height: 34px; border-radius: 2px; background: var(--capacity-color); box-shadow: 0 0 12px color-mix(in srgb, var(--capacity-color) 55%, transparent); }
.province-detail__capacity-info, .province-detail__capacity-value { display: grid; align-content: space-between; min-width: 0; }
.province-detail__capacity-info > div { display: flex; align-items: baseline; gap: 6px; }
.province-detail__capacity-info strong { color: var(--xc-text-strong); font-size: var(--xc-fs-xs); }
.province-detail__capacity-info span, .province-detail__capacity-info small { overflow: hidden; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); text-overflow: ellipsis; white-space: nowrap; }
.province-detail__capacity-value { justify-items: end; padding-left: 6px; }
.province-detail__capacity-value > strong { color: var(--xc-text-strong); font-size: var(--xc-fs-md); line-height: 1; }
.province-detail__capacity-value > strong small { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); font-weight: 500; }
.province-detail__capacity-value > span { color: #49dfa6; font-size: var(--xc-fs-2xs); font-weight: 700; }
.province-detail__capacity-value > span.is-down { color: #ff7373; }
.province-detail__bar { display: grid; grid-template-columns: 58px 1fr 42px; align-items: center; gap: var(--xc-space-2); color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); } .province-detail__bar i { height: 7px; border-radius: var(--xc-radius-full); background: rgba(255, 255, 255, 0.08); overflow: hidden; } .province-detail__bar i b { display: block; height: 100%; background: linear-gradient(90deg, var(--xc-accent-blue), var(--xc-status-warn)); box-shadow: var(--xc-glow-blue); } .province-detail__bar strong { color: var(--xc-text-soft); text-align: right; }
.province-detail__analysis { padding: var(--xc-space-2) var(--xc-space-3); border-left: 3px solid rgba(34, 177, 253, 0.72); border-radius: var(--xc-radius-sm); background: rgba(34, 177, 253, 0.08); line-height: var(--xc-lh-normal); }.province-detail .xc-btn { justify-self: stretch; }
@media (max-width: 900px) {
  .province-detail { grid-template-columns: 0.8fr 1fr 1.25fr; grid-template-rows: auto minmax(0, 1fr) auto; align-content: stretch; gap: 5px 7px; height: 100%; min-height: 0; padding: 6px 8px; overflow: hidden; }
  .province-detail > header { grid-column: 1; grid-row: 1; }
  .province-detail__score { grid-column: 2; grid-row: 1; padding: 3px 6px; }
  .province-detail > section:nth-of-type(2) { grid-column: 1; grid-row: 2; }
  .province-detail > section:nth-of-type(3) { grid-column: 2; grid-row: 2; }
  .province-detail > section:nth-of-type(4) { grid-column: 3; grid-row: 1 / span 2; }
  .province-detail__analysis { grid-column: 1 / -1; grid-row: 3; padding: 3px 6px; }
  .province-detail__grade { width: 28px; height: 28px; }
  .province-detail__score > strong { font-size: var(--xc-fs-lg); }
  .province-detail__grid { gap: 3px; }
  .province-detail__grid article { padding: 3px 5px; }
  .province-detail__capacity { grid-template-columns: 3px minmax(0, 1fr) auto; min-height: 39px; padding: 4px 6px 4px 4px; }
  .province-detail__capacity-mark { width: 3px; min-height: 29px; }
  .province-detail__capacity-info strong { font-size: 11px; }
  .province-detail__capacity-value > strong { font-size: 14px; }
  .province-detail__bar { grid-template-columns: 42px 1fr 34px; gap: 3px; }
  section { gap: 3px; }
  h2 { font-size: var(--xc-fs-md); }
  h3, p, small, .province-detail__grid span, .province-detail__capacity-info span, .province-detail__capacity-info small, .province-detail__capacity-value > span, .province-detail__bar { font-size: 10px; }
}
</style>

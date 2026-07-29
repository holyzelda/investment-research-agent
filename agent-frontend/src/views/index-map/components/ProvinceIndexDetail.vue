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
.province-detail { display: grid; align-content: start; gap: 14px; min-height: 0; height: 100%; padding: 16px; box-sizing: border-box; border: 1px solid var(--xc-border-soft); border-radius: 8px; background: #283034; overflow-y: auto; scrollbar-width: thin; scrollbar-color: var(--xc-border-strong) transparent; }
.province-detail__state { display: grid; min-height: 240px; place-items: center; gap: 12px; color: var(--xc-text-mute); font-size: 13px; }
header, .province-detail__score { display: flex; justify-content: space-between; gap: 12px; }
header { align-items: flex-start; padding-bottom: 13px; border-bottom: 1px solid var(--xc-border-soft); }
h2, h3, p { margin: 0; }
h2 { color: var(--xc-text-strong); font-size: 22px; font-weight: 600; line-height: 1.15; }
h3 { color: var(--xc-text-soft); font-size: 12px; font-weight: 600; }
p, small { color: var(--xc-text-mute); font-size: 11px; }
header p { margin-top: 5px; line-height: 1.45; }
.province-detail__grade { display: grid; width: 38px; height: 38px; flex: 0 0 auto; place-items: center; border: 1px solid var(--xc-status-warn); border-radius: 4px; background: var(--xc-status-warn-soft); color: var(--xc-text-strong); font-family: var(--xc-font-mono); font-size: 16px; }
.province-detail__score { align-items: center; padding: 10px 12px; border-left: 3px solid var(--xc-accent-blue); background: #323b3f; }
.province-detail__score > strong { color: var(--xc-text-strong); font-size: 28px; line-height: 1; }
.province-detail__score > span { color: var(--xc-text-mute); font-size: 11px; }
.province-detail__score div { display: grid; justify-items: end; }
.province-detail__score b { max-width: 18ch; color: var(--xc-accent-blue); font-size: 12px; text-align: right; }
section { display: grid; gap: 8px; padding-top: 1px; }
section + section { padding-top: 13px; border-top: 1px solid var(--xc-border-soft); }
h3 b { float: right; color: var(--xc-text-strong); font-weight: 500; }
.province-detail__grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.province-detail__grid article { display: grid; gap: 2px; padding: 7px 9px; border: 1px solid var(--xc-border-soft); border-radius: 4px; background: rgba(255, 255, 255, 0.025); }
.province-detail__grid span { color: var(--xc-text-mute); font-size: 11px; }
.province-detail__grid strong { color: var(--xc-text-strong); font-size: 14px; }
.province-detail__bar { display: grid; grid-template-columns: 62px 1fr 42px; align-items: center; gap: 8px; color: var(--xc-text-mute); font-size: 11px; }
.province-detail__bar i { height: 5px; background: rgba(255, 255, 255, 0.08); overflow: hidden; }
.province-detail__bar i b { display: block; height: 100%; background: var(--xc-accent-blue); }
.province-detail__bar strong { color: var(--xc-text-soft); text-align: right; }
.province-detail__capacity { --capacity-color: #54c6d6; display: grid; grid-template-columns: 3px minmax(0, 1fr) auto; align-items: stretch; gap: 8px; min-height: 46px; padding: 7px 9px 7px 6px; box-sizing: border-box; border: 1px solid var(--xc-border-soft); border-radius: 4px; background: rgba(255, 255, 255, 0.025); }
.province-detail__capacity--thermal { --capacity-color: #d9b35a; }
.province-detail__capacity--storage { --capacity-color: #66c48a; }
.province-detail__capacity-mark { width: 3px; height: 100%; min-height: 32px; background: var(--capacity-color); }
.province-detail__capacity-info, .province-detail__capacity-value { display: grid; align-content: space-between; min-width: 0; }
.province-detail__capacity-info > div { display: flex; align-items: baseline; gap: 6px; }
.province-detail__capacity-info strong { color: var(--xc-text-strong); font-size: 12px; }
.province-detail__capacity-info span, .province-detail__capacity-info small { overflow: hidden; color: var(--xc-text-mute); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.province-detail__capacity-value { justify-items: end; padding-left: 6px; }
.province-detail__capacity-value > strong { color: var(--xc-text-strong); font-size: 15px; line-height: 1; }
.province-detail__capacity-value > strong small { color: var(--xc-text-mute); font-size: 10px; font-weight: 500; }
.province-detail__capacity-value > span { color: var(--xc-status-ok); font-size: 10px; font-weight: 600; }
.province-detail__capacity-value > span.is-down { color: var(--xc-status-danger); }
.province-detail__analysis { padding: 9px 10px; border-left: 3px solid var(--xc-accent-blue); background: rgba(84, 198, 214, 0.07); line-height: 1.55; }
.province-detail .xc-btn { justify-self: stretch; }
@media (max-width: 1023px) {
  .province-detail { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px 18px; }
  .province-detail > header, .province-detail__score, .province-detail__analysis { grid-column: 1 / -1; }
  .province-detail__installed { grid-column: 1 / -1; }
}
@media (max-width: 639px) {
  .province-detail { display: grid; grid-template-columns: 1fr; padding: 14px; }
  .province-detail > header, .province-detail__score, .province-detail__analysis, .province-detail__installed { grid-column: auto; }
  h2 { font-size: 19px; }
}
</style>

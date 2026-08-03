<template>
  <aside class="province-detail">
    <div v-if="loading" class="province-detail__state">正在加载省份详情</div>
    <div v-else-if="error" class="province-detail__state"><span>{{ error }}</span><button class="xc-btn xc-btn--ghost" type="button" @click="$emit('retry')">重试</button></div>
    <div v-else-if="!detail" class="province-detail__state">该期次暂无省份详情</div>
    <template v-else>
      <header class="province-detail__hero">
        <div class="province-detail__identity">
          <div><h2>{{ detail.provinceName }}</h2><span>重点投资区域</span></div>
          <p>{{ detail.regionDescription || '—' }}</p>
        </div>
        <div
          class="province-detail__grade-ring"
          :style="{ '--grade-progress': `${gradeProgress(detail.grade, detail.indexScore)}%` }"
          :aria-label="`投资指数评级 ${detail.grade || '未知'}`"
        >
          <div><strong class="xc-num">{{ detail.grade || '—' }}</strong><span>投资指数</span></div>
        </div>
      </header>
      <section class="province-detail__score">
        <div class="province-detail__score-value"><strong class="xc-num">{{ formatNumber(detail.indexScore) }}</strong><span>/ 100</span></div>
        <p v-if="detail.investmentAdvice" class="province-detail__score-advice">{{ detail.investmentAdvice }}</p>
      </section>
      <section class="province-detail__maturity">
        <h3><span>归因分析 · 市场化成熟度</span></h3>
        <p>{{ detail.maturity?.summary || '—' }}</p>
        <div class="province-detail__grid">
          <article v-for="item in detail.maturity?.scores || []" :key="item.key">
            <div><span>{{ item.label }}</span><strong class="xc-num">{{ formatNumber(item.score) }}</strong></div>
            <i><b :style="{ width: `${clampPercent(item.score)}%` }" /></i>
          </article>
        </div>
      </section>
      <section class="province-detail__factors"><h3><span>归因分析 · 因子贡献度</span></h3><div v-for="item in detail.factorContributions || []" :key="item.key" class="province-detail__bar"><span>{{ item.label }}</span><i><b :style="{ width: `${clampPercent(item.value)}%` }" /></i><strong class="xc-num">+{{ formatNumber(item.delta) }}</strong></div></section>
      <section class="province-detail__installed">
        <h3><span>装机结构 · 在运</span><b class="xc-num">合计 {{ formatNumber(detail.installedStructure?.totalGw) }} GW</b></h3>
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

function clampPercent(value) {
  const number = Number(value)
  return Number.isFinite(number) ? Math.min(100, Math.max(0, number)) : 0
}

function gradeProgress(grade, indexScore) {
  // 评级环进度直接反映真实投资指数分数（0–100），同等级不同分省份显示各自进度。
  return clampPercent(indexScore)
}

defineProps({ detail: { type: Object, default: null }, loading: Boolean, error: { type: String, default: '' } })
defineEmits(['retry'])
</script>
<style scoped>
.province-detail { display: grid; align-content: start; gap: 16px; min-height: 0; height: 100%; padding: 18px; box-sizing: border-box; border: 1px solid rgba(130, 154, 166, 0.2); border-radius: 8px; background: #222a2e; box-shadow: inset 0 1px rgba(255, 255, 255, 0.025); overflow-y: auto; scrollbar-width: thin; scrollbar-color: var(--xc-border-strong) transparent; }
.province-detail__state { display: grid; min-height: 240px; place-items: center; gap: 12px; color: var(--xc-text-mute); font-size: 13px; }
header { display: flex; justify-content: space-between; gap: 14px; }
.province-detail__hero { align-items: flex-start; min-height: 86px; }
.province-detail__identity { min-width: 0; padding-top: 2px; }
.province-detail__identity > div { display: flex; align-items: center; gap: 8px; }
.province-detail__identity > div span { padding: 3px 6px; border: 1px solid rgba(79, 216, 226, 0.28); border-radius: 3px; background: rgba(79, 216, 226, 0.08); color: #79dbe3; font-size: 10px; line-height: 1; white-space: nowrap; }
h2, h3, p { margin: 0; }
h2 { color: var(--xc-text-strong); font-size: 22px; font-weight: 600; line-height: 1.15; }
h3 { display: flex; align-items: center; justify-content: space-between; gap: 10px; color: var(--xc-text-soft); font-size: 12px; font-weight: 600; }
h3 > span { display: flex; align-items: center; gap: 8px; }
h3 > span::before { width: 3px; height: 13px; background: linear-gradient(#4fd8e2, #8067ff); content: ''; }
p, small { color: var(--xc-text-mute); font-size: 11px; }
header p { max-width: 24ch; margin-top: 7px; line-height: 1.5; }
.province-detail__grade-ring { display: grid; width: 72px; height: 72px; flex: 0 0 auto; place-items: center; border-radius: 50%; background: conic-gradient(from -90deg, #56d9e4 0%, #8167ff var(--grade-progress), rgba(255, 255, 255, 0.08) var(--grade-progress) 100%); box-shadow: 0 0 18px rgba(93, 201, 225, 0.09); }
.province-detail__grade-ring > div { display: grid; width: 60px; height: 60px; place-content: center; justify-items: center; border-radius: 50%; background: #222a2e; }
.province-detail__grade-ring strong { color: #f1f6f7; font-size: 24px; line-height: 1; }
.province-detail__grade-ring span { margin-top: 4px; color: #8da0a7; font-size: 9px; }
.province-detail__score { container-type: inline-size; display: grid; grid-template-columns: auto minmax(0, 1fr); align-items: center; gap: 8px; min-height: 64px; padding: 13px 14px; border: 1px solid rgba(79, 216, 226, 0.22); border-radius: 6px; background: linear-gradient(105deg, rgba(79, 216, 226, 0.1), rgba(128, 103, 255, 0.06) 48%, rgba(43, 52, 56, 0.96) 78%); box-shadow: inset 0 1px rgba(255, 255, 255, 0.035); }
.province-detail__score-value { display: flex; align-items: baseline; min-width: 78px; }
.province-detail__score-value strong { color: #f3f7f8; font-size: 34px; line-height: 1; }
.province-detail__score-value span { margin-left: 4px; color: #71868e; font-size: 10px; }
.province-detail__score-advice { min-width: 0; justify-self: end; color: #f3c66f; font-size: clamp(11px, 3.5cqi, 13px); font-weight: 600; line-height: 1.45; text-align: right; text-shadow: 0 0 12px rgba(244, 180, 75, 0.14); white-space: nowrap; }
section { display: grid; gap: 9px; padding-top: 1px; }
section + section { padding-top: 15px; border-top: 1px solid rgba(130, 154, 166, 0.14); }
h3 b { color: #dce5e7; font-size: 11px; font-weight: 500; }
.province-detail__maturity > p { padding-left: 11px; line-height: 1.55; }
.province-detail__grid { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; }
.province-detail__grid article { display: grid; gap: 8px; padding: 8px 9px; border: 1px solid rgba(130, 154, 166, 0.15); border-radius: 6px; background: rgba(255, 255, 255, 0.018); }
.province-detail__grid article > div { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.province-detail__grid span { overflow: hidden; color: #8fa0a6; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.province-detail__grid strong { color: #dfe8ea; font-size: 14px; }
.province-detail__grid i { height: 2px; background: rgba(255, 255, 255, 0.07); overflow: hidden; }
.province-detail__grid i b { display: block; height: 100%; background: linear-gradient(90deg, #4fd8e2, #8067ff); }
.province-detail__bar { display: grid; grid-template-columns: 62px 1fr 42px; align-items: center; gap: 8px; color: var(--xc-text-mute); font-size: 11px; }
.province-detail__bar i { height: 4px; background: rgba(255, 255, 255, 0.07); overflow: hidden; }
.province-detail__bar i b { display: block; height: 100%; background: #56ced8; }
.province-detail__bar strong { color: var(--xc-text-soft); text-align: right; }
.province-detail__capacity { --capacity-color: #54c6d6; display: grid; grid-template-columns: 8px minmax(0, 1fr) auto; align-items: stretch; gap: 10px; min-height: 46px; padding: 8px 9px; box-sizing: border-box; border: 1px solid rgba(130, 154, 166, 0.15); border-radius: 6px; background: rgba(255, 255, 255, 0.018); }
.province-detail__capacity--thermal { --capacity-color: #f3a64a; }
.province-detail__capacity--storage { --capacity-color: #8b5cf6; }
.province-detail__capacity-mark { align-self: center; width: 8px; height: 8px; border-radius: 2px; background: var(--capacity-color); }
.province-detail__capacity-info, .province-detail__capacity-value { display: grid; align-content: space-between; min-width: 0; }
.province-detail__capacity-info > div { display: flex; align-items: baseline; gap: 6px; }
.province-detail__capacity-info strong { color: var(--xc-text-strong); font-size: 12px; }
.province-detail__capacity-info span, .province-detail__capacity-info small { overflow: hidden; color: var(--xc-text-mute); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.province-detail__capacity-value { justify-items: end; padding-left: 6px; }
.province-detail__capacity-value > strong { color: var(--xc-text-strong); font-size: 15px; line-height: 1; }
.province-detail__capacity-value > strong small { color: var(--xc-text-mute); font-size: 10px; font-weight: 500; }
.province-detail__capacity-value > span { color: var(--xc-status-ok); font-size: 10px; font-weight: 600; }
.province-detail__capacity-value > span.is-down { color: var(--xc-status-danger); }
.province-detail__analysis { padding: 10px 11px; border: 1px solid rgba(130, 154, 166, 0.15); border-radius: 6px; background: rgba(84, 198, 214, 0.055); line-height: 1.6; }
.province-detail .xc-btn { justify-self: stretch; }
@media (max-width: 1023px) {
  .province-detail { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px 18px; }
  .province-detail > header, .province-detail__score { grid-column: 1 / -1; }
  .province-detail__installed { grid-column: 1 / -1; }
}
@media (max-width: 639px) {
  .province-detail { display: grid; grid-template-columns: 1fr; padding: 14px; }
  .province-detail > header, .province-detail__score, .province-detail__installed { grid-column: auto; }
  h2 { font-size: 19px; }
  .province-detail__grade-ring { width: 66px; height: 66px; }
  .province-detail__grade-ring > div { width: 54px; height: 54px; }
}
</style>

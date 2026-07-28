<template>
  <aside class="province-detail">
    <div v-if="loading" class="province-detail__state">正在加载省份详情</div>
    <div v-else-if="error" class="province-detail__state"><span>{{ error }}</span><button class="xc-btn xc-btn--ghost" type="button" @click="$emit('retry')">重试</button></div>
    <div v-else-if="!detail" class="province-detail__state">该期次暂无省份详情</div>
    <template v-else>
      <header><div><h2>{{ detail.provinceName }}</h2><p>{{ detail.regionDescription || '—' }}</p></div><strong class="province-detail__grade">{{ detail.grade || '—' }}</strong></header>
      <section class="province-detail__score"><strong class="xc-num">{{ formatNumber(detail.indexScore) }}</strong><span>/ 100</span><div><b>{{ detail.investmentAdvice || '—' }}</b><em>年化 {{ formatNumber(detail.annualizedReturn) }}%</em></div></section>
      <section><h3>归因分析 · 市场化成熟度 <b>{{ detail.maturity?.grade || '—' }}</b></h3><p>{{ detail.maturity?.summary || '—' }}</p><div class="province-detail__grid"><article v-for="item in detail.maturity?.scores || []" :key="item.key"><span>{{ item.label }}</span><strong class="xc-num">{{ formatNumber(item.score) }}</strong></article></div></section>
      <section><h3>归因分析 · 因子贡献度</h3><div v-for="item in detail.factorContributions || []" :key="item.key" class="province-detail__bar"><span>{{ item.label }}</span><i><b :style="{ width: `${item.value || 0}%` }" /></i><strong class="xc-num">+{{ formatNumber(item.delta) }}</strong></div></section>
      <section><h3>装机结构 · 在运 <b class="xc-num">合计 {{ formatNumber(detail.installedStructure?.totalGw) }} GW</b></h3><article v-for="item in detail.installedStructure?.items || []" :key="item.key" class="province-detail__capacity"><span>{{ item.label }} {{ formatNumber(item.share) }}%</span><strong class="xc-num">{{ formatNumber(item.capacityGw) }} GW</strong><small>{{ item.description || '—' }} {{ item.deltaText || '' }}</small></article></section>
      <p class="province-detail__analysis">{{ detail.analysisText || '—' }}</p>
      <button class="xc-btn xc-btn--primary" type="button" @click="ElMessage.info('区域节点分析功能将在后续开放')">查看省级区域节点分析</button>
    </template>
  </aside>
</template>
<script setup>
import { ElMessage } from 'element-plus'
import { formatNumber } from '@/utils/formatNumber'
defineProps({ detail: { type: Object, default: null }, loading: Boolean, error: { type: String, default: '' } })
defineEmits(['retry'])
</script>
<style scoped>
.province-detail { display: grid; align-content: start; gap: var(--xc-space-4); min-height: 480px; padding: var(--xc-space-4); border: 1px solid var(--xc-border-card); border-radius: var(--xc-radius-lg); background: var(--xc-surface-card); overflow-y: auto; }
.province-detail__state { display: grid; place-items: center; gap: var(--xc-space-3); min-height: 240px; color: var(--xc-text-mute); }
header, .province-detail__score { display: flex; justify-content: space-between; gap: var(--xc-space-3); }
h2, h3, p { margin: 0; } h2 { color: var(--xc-text-strong); } h3 { color: var(--xc-text-soft); font-size: var(--xc-fs-xs); } p, small { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.province-detail__grade { display: grid; place-items: center; width: 44px; height: 44px; border: 3px solid var(--xc-accent-blue); border-radius: 50%; color: var(--xc-text-strong); }
.province-detail__score { align-items: center; padding: var(--xc-space-3); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-md); } .province-detail__score > strong { color: var(--xc-text-strong); font-size: var(--xc-fs-2xl); } .province-detail__score div { display: grid; justify-items: end; } .province-detail__score b { color: var(--xc-accent-blue); } .province-detail__score em { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); font-style: normal; }
section { display: grid; gap: var(--xc-space-2); } h3 b { float: right; color: var(--xc-text-strong); }
.province-detail__grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--xc-space-2); } .province-detail__grid article, .province-detail__capacity { display: grid; gap: 2px; padding: var(--xc-space-2); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); } .province-detail__grid span, .province-detail__capacity span { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); } .province-detail__grid strong, .province-detail__capacity strong { color: var(--xc-text-strong); }
.province-detail__bar { display: grid; grid-template-columns: 50px 1fr 36px; align-items: center; gap: var(--xc-space-2); color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); } .province-detail__bar i { height: 6px; border-radius: var(--xc-radius-full); background: var(--xc-surface-control); overflow: hidden; } .province-detail__bar i b { display: block; height: 100%; background: var(--xc-accent-blue); } .province-detail__bar strong { color: var(--xc-text-soft); text-align: right; }
.province-detail__analysis { line-height: var(--xc-lh-normal); }.province-detail .xc-btn { justify-self: stretch; }
</style>

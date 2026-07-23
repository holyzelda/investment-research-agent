<template>
  <aside class="pm-pulse" aria-label="市场脉搏">
    <header class="pm-pulse__heading"><div><p>MARKET PULSE</p><h2>市场脉搏</h2></div><span>LIVE</span></header>
    <section class="pm-pulse__stats" aria-label="咨询概览">
      <div class="pm-pulse__stats-heading"><span>咨询概览</span><span>实时</span></div>
      <div class="pm-pulse__filters">
        <label>省份<select v-model="draftFilters.province" data-filter="province" @change="emitFilters"><option v-for="option in provinceOptions" :key="option" :value="option">{{ option === 'all' ? '全部省份' : option }}</option></select></label>
        <label>时间范围<select v-model="draftFilters.period" data-filter="period" @change="emitFilters"><option v-for="option in periodOptions" :key="option.value" :value="option.value">{{ option.label }}</option></select></label>
        <label>咨询主题<select v-model="draftFilters.topic" data-filter="topic" @change="emitFilters"><option v-for="option in topicOptions" :key="option.value" :value="option.value">{{ option.label }}</option></select></label>
      </div>
      <p v-if="statsLoading" class="pm-pulse__state">正在更新统计</p><p v-else-if="statsError" class="pm-pulse__state pm-pulse__state--error">统计加载失败</p>
      <template v-else><div class="pm-pulse__total"><strong class="xc-num">{{ stats.total }}</strong><span>条咨询</span></div><div class="pm-pulse__stat-foot"><span>{{ stats.rangeLabel }}</span><span class="pm-pulse__trend">较上期 +{{ stats.trend }}%</span></div></template>
    </section>
    <div ref="newsScrollRef" class="pm-pulse__news" data-news-scroll @mouseenter="pauseAutoScroll" @mouseleave="resumeAutoScroll" @wheel="pauseAutoScroll" @touchstart="pauseAutoScroll" @pointerdown="pauseAutoScroll">
      <p v-if="loading" class="pm-pulse__state">正在加载市场资讯</p><p v-else-if="error" class="pm-pulse__state pm-pulse__state--error">{{ error }}</p><p v-else-if="!news.length" class="pm-pulse__state">暂无市场资讯</p>
      <template v-else v-for="item in news" :key="item.id">
        <a v-if="item.linkUrl" :data-news-id="item.id" class="pm-pulse__news-item" :href="item.linkUrl" target="_blank" rel="noopener noreferrer"><strong>{{ item.title }}</strong><span><b v-for="tag in item.tags" :key="tag">{{ tag }}</b>{{ formatPublishedAt(item.publishTime) }}</span></a>
        <div v-else :data-news-id="item.id" class="pm-pulse__news-item"><strong>{{ item.title }}</strong><span><b v-for="tag in item.tags" :key="tag">{{ tag }}</b>{{ formatPublishedAt(item.publishTime) }}</span></div>
      </template>
    </div>
  </aside>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'

const props = defineProps({
  filters: { type: Object, default: () => ({ province: 'all', period: 'all', topic: 'all' }) },
  stats: { type: Object, default: () => ({ total: 0, trend: 0, rangeLabel: '全部省份' }) },
  news: { type: Array, default: () => [] }, loading: { type: Boolean, default: false }, error: { type: String, default: '' }, statsLoading: { type: Boolean, default: false }, statsError: { type: String, default: '' },
})
const emit = defineEmits(['filters-change'])
const draftFilters = reactive({ ...props.filters })
const newsScrollRef = ref(null)
const AUTO_SCROLL_SPEED = 60
const AUTO_SCROLL_BOTTOM_PAUSE_MS = 1200
let animationFrameId = null
let restartTimerId = null
let lastTimestamp = null
let isAutoScrollPaused = false
const provinceOptions = ['all', '内蒙古', '山东', '江苏', '广东', '河北', '浙江']
const periodOptions = [{ value: 'all', label: '全部时间' }, { value: 'month', label: '本月' }, { value: 'quarter', label: '近三个月' }]
const topicOptions = [{ value: 'all', label: '全部主题' }, { value: '政策', label: '政策解读' }, { value: '市场', label: '市场分析' }, { value: '行业', label: '行业研究' }]
watch(() => props.filters, (filters) => Object.assign(draftFilters, filters), { deep: true })
watch(() => props.news, () => nextTick(startAutoScroll), { deep: true })
function emitFilters() { emit('filters-change', { ...draftFilters }) }
function stopAnimationFrameOnly() {
  if (animationFrameId !== null) window.cancelAnimationFrame(animationFrameId)
  animationFrameId = null
}
function stopAutoScroll() {
  stopAnimationFrameOnly()
  if (restartTimerId !== null) window.clearTimeout(restartTimerId)
  restartTimerId = null
  lastTimestamp = null
}
function stepAutoScroll(timestamp) {
  const container = newsScrollRef.value
  if (!container || isAutoScrollPaused || container.scrollHeight <= container.clientHeight) return
  if (lastTimestamp === null) {
    lastTimestamp = timestamp
  } else {
    container.scrollTop += AUTO_SCROLL_SPEED * ((timestamp - lastTimestamp) / 1000)
    lastTimestamp = timestamp
  }
  const maxScrollTop = container.scrollHeight - container.clientHeight
  if (container.scrollTop >= maxScrollTop) {
    container.scrollTop = maxScrollTop
    stopAnimationFrameOnly()
    restartTimerId = window.setTimeout(() => {
      container.scrollTop = 0
      restartTimerId = null
      lastTimestamp = null
      startAutoScroll()
    }, AUTO_SCROLL_BOTTOM_PAUSE_MS)
    return
  }
  animationFrameId = window.requestAnimationFrame(stepAutoScroll)
}
function startAutoScroll() {
  const container = newsScrollRef.value
  stopAnimationFrameOnly()
  if (!container || isAutoScrollPaused || container.scrollHeight <= container.clientHeight) return
  animationFrameId = window.requestAnimationFrame(stepAutoScroll)
}
function pauseAutoScroll() {
  isAutoScrollPaused = true
  stopAutoScroll()
}
function resumeAutoScroll() {
  isAutoScrollPaused = false
  lastTimestamp = null
  startAutoScroll()
}
onMounted(() => { nextTick(startAutoScroll) })
onBeforeUnmount(stopAutoScroll)
function formatPublishedAt(value) { if (!value) return '—'; const date = new Date(value); return Number.isNaN(date.getTime()) ? '—' : new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit' }).format(date) }
</script>

<style scoped>
.pm-pulse { min-width: 0; display: flex; flex-direction: column; gap: var(--xc-space-4); padding: var(--xc-space-5); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-md); background: var(--xc-surface-card); }.pm-pulse__heading, .pm-pulse__stats-heading, .pm-pulse__stat-foot { display: flex; align-items: center; justify-content: space-between; gap: var(--xc-space-3); }.pm-pulse__heading p { margin: 0; color: var(--xc-accent-blue); font-size: var(--xc-fs-2xs); letter-spacing: .04em; }.pm-pulse__heading h2 { margin: var(--xc-space-1) 0 0; color: var(--xc-text-strong); font-size: var(--xc-fs-h3); }.pm-pulse__heading > span { color: var(--xc-status-ok); font-size: var(--xc-fs-2xs); }.pm-pulse__stats { display: grid; gap: var(--xc-space-3); padding: var(--xc-space-4); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); background: var(--xc-surface-raised); }.pm-pulse__stats-heading, .pm-pulse__stat-foot, .pm-pulse__news-item span { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }.pm-pulse__filters { display: grid; gap: var(--xc-space-2); }.pm-pulse__filters label { display: grid; grid-template-columns: 64px minmax(0, 1fr); gap: var(--xc-space-2); color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }.pm-pulse__filters select { min-width: 0; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); padding: var(--xc-space-1) var(--xc-space-2); background: var(--xc-surface-control); color: var(--xc-text-soft); font: inherit; }.pm-pulse__total { display: flex; align-items: baseline; gap: var(--xc-space-2); color: var(--xc-text-mute); font-size: var(--xc-fs-xs); }.pm-pulse__total strong, .pm-pulse__news-item strong { color: var(--xc-text-strong); }.pm-pulse__total strong { font-size: var(--xc-fs-h1); }.pm-pulse__trend { color: var(--xc-trade-up); }.pm-pulse__news { display: grid; max-height: 432px; overflow-y: auto; overscroll-behavior: contain; }.pm-pulse__news-item { display: grid; gap: var(--xc-space-2); border-bottom: 1px solid var(--xc-border-soft); padding: var(--xc-space-3) 0; color: var(--xc-text-soft); text-align: left; text-decoration: none; }.pm-pulse__news-item a { cursor: pointer; }.pm-pulse__news-item b { color: var(--xc-accent-blue); font-weight: var(--xc-fw-medium); margin-right: var(--xc-space-2); }.pm-pulse__state { margin: var(--xc-space-3) 0; color: var(--xc-text-mute); font-size: var(--xc-fs-xs); text-align: center; }.pm-pulse__state--error { color: var(--xc-status-danger); }
</style>

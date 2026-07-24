<template>
  <aside class="pm-pulse" aria-label="市场脉搏">
    <header class="pm-pulse__heading"><div><p>MARKET PULSE</p><h2>市场脉搏</h2></div><span>LIVE</span></header>
    <section class="pm-pulse__stats" aria-label="资讯概览">
      <div class="pm-pulse__stats-heading"><span>资讯概览</span><span>实时</span></div>
      <div class="pm-pulse__filters">
        <div class="pm-pulse__filter-row">
          <span>省份</span>
          <ElPopover v-model:visible="provinceOpen" placement="bottom-end" trigger="click" popper-class="pm-filter-popper">
            <template #reference><button type="button" class="pm-pulse__filter-control" data-filter="province" aria-label="筛选省份" aria-haspopup="listbox" :aria-expanded="provinceOpen" aria-controls="pm-province-menu">{{ provinceLabel }}</button></template>
            <div id="pm-province-menu" class="pm-filter-menu" role="listbox" aria-label="省份选项"><button v-for="option in provinceOptions" :key="option" type="button" class="pm-filter-menu__option" role="option" :aria-selected="draftFilters.province === option" :class="{ 'is-selected': draftFilters.province === option }" :data-test="`province-${option}`" @click="selectFilter('province', option)">{{ option === 'all' ? '全部省份' : option }}</button></div>
          </ElPopover>
        </div>
        <div class="pm-pulse__filter-row">
          <span>时间范围</span>
          <ElPopover v-model:visible="periodOpen" placement="bottom-end" trigger="click" popper-class="pm-filter-popper">
            <template #reference><button type="button" class="pm-pulse__filter-control" data-filter="period" aria-label="筛选时间范围" aria-haspopup="listbox" :aria-expanded="periodOpen" aria-controls="pm-period-menu">{{ periodLabel }}</button></template>
            <div id="pm-period-menu" class="pm-filter-menu" role="listbox" aria-label="时间范围选项"><button v-for="option in periodOptions" :key="option.value" type="button" class="pm-filter-menu__option" role="option" :aria-selected="draftFilters.period === option.value" :class="{ 'is-selected': draftFilters.period === option.value }" :data-test="`period-${option.value}`" @click="selectFilter('period', option.value)">{{ option.label }}</button></div>
          </ElPopover>
        </div>
        <div class="pm-pulse__filter-row">
          <span>资讯主题</span>
          <ElPopover v-model:visible="topicOpen" placement="bottom-end" trigger="click" popper-class="pm-filter-popper">
            <template #reference><button type="button" class="pm-pulse__filter-control" data-filter="topic" aria-label="筛选资讯主题" aria-haspopup="listbox" :aria-expanded="topicOpen" aria-controls="pm-topic-menu">{{ topicLabel }}</button></template>
            <div id="pm-topic-menu" class="pm-filter-menu" role="listbox" aria-label="资讯主题选项"><button type="button" class="pm-filter-menu__option" role="option" :aria-selected="draftFilters.topic === 'all'" :class="{ 'is-selected': draftFilters.topic === 'all' }" data-test="topic-all" @click="selectFilter('topic', 'all')">全部主题</button><button v-for="option in topicOptions" :key="option.value" type="button" class="pm-filter-menu__option" role="option" :aria-selected="draftFilters.topic === option.value" :class="{ 'is-selected': draftFilters.topic === option.value }" :data-test="`topic-${option.value}`" @click="selectFilter('topic', option.value)">{{ option.label }}</button></div>
          </ElPopover>
        </div>
      </div>
      <p v-if="statsLoading" class="pm-pulse__state">正在更新统计</p><p v-else-if="statsError" class="pm-pulse__state pm-pulse__state--error">统计加载失败</p>
      <template v-else><div class="pm-pulse__total"><strong class="xc-num">{{ stats.total }}</strong><span>条资讯</span></div><div class="pm-pulse__stat-foot"><span>{{ stats.rangeLabel }}</span><span v-if="stats.trendPercent === null" class="pm-pulse__trend pm-pulse__trend--mute">暂无可比数据</span><span v-else class="pm-pulse__trend" :class="{ 'pm-pulse__trend--down': stats.trendPercent < 0 }">较上期 {{ stats.trendPercent > 0 ? '+' : '' }}{{ stats.trendPercent }}%</span></div></template>
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
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElPopover } from 'element-plus'

const props = defineProps({
  filters: { type: Object, default: () => ({ province: 'all', period: 'all', topic: 'all' }) },
  stats: { type: Object, default: () => ({ total: 0, trendPercent: null, rangeLabel: '全部省份 · 全部时间' }) },
  topicOptions: { type: Array, default: () => [] },
  news: { type: Array, default: () => [] }, loading: { type: Boolean, default: false }, error: { type: String, default: '' }, statsLoading: { type: Boolean, default: false }, statsError: { type: String, default: '' },
})
const emit = defineEmits(['filters-change'])
const draftFilters = reactive({ ...props.filters })
const newsScrollRef = ref(null)
const provinceOpen = ref(false)
const periodOpen = ref(false)
const topicOpen = ref(false)
const AUTO_SCROLL_SPEED = 60
const AUTO_SCROLL_BOTTOM_PAUSE_MS = 1200
let animationFrameId = null
let restartTimerId = null
let lastTimestamp = null
let isAutoScrollPaused = false
const provinceOptions = [
  'all', '内蒙古', '广西', '宁夏', '新疆', '西藏',
  '北京', '天津', '上海', '重庆', '河北', '山西', '辽宁', '吉林', '黑龙江',
  '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南', '湖北', '湖南',
  '广东', '海南', '四川', '贵州', '云南', '陕西', '甘肃', '青海', '台湾',
  '香港', '澳门',
]
const periodOptions = [{ value: 'all', label: '全部时间' }, { value: 'month', label: '本月' }, { value: 'quarter', label: '近三个月' }]
const provinceLabel = computed(() => draftFilters.province === 'all' ? '全部省份' : draftFilters.province)
const periodLabel = computed(() => periodOptions.find((item) => item.value === draftFilters.period)?.label || '全部时间')
const topicLabel = computed(() => draftFilters.topic === 'all' ? '全部主题' : props.topicOptions.find((item) => item.value === draftFilters.topic)?.label || draftFilters.topic)
watch(() => props.filters, (filters) => Object.assign(draftFilters, filters), { deep: true })
watch(() => props.news, () => nextTick(startAutoScroll), { deep: true })
function selectFilter(field, value) {
  draftFilters[field] = value
  if (field === 'province') provinceOpen.value = false
  if (field === 'period') periodOpen.value = false
  if (field === 'topic') topicOpen.value = false
  emit('filters-change', { ...draftFilters })
}
function stopAnimationFrameOnly() { if (animationFrameId !== null) window.cancelAnimationFrame(animationFrameId); animationFrameId = null }
function stopAutoScroll() { stopAnimationFrameOnly(); if (restartTimerId !== null) window.clearTimeout(restartTimerId); restartTimerId = null; lastTimestamp = null }
function stepAutoScroll(timestamp) {
  const container = newsScrollRef.value
  if (!container || isAutoScrollPaused || container.scrollHeight <= container.clientHeight) return
  if (lastTimestamp === null) lastTimestamp = timestamp
  else { container.scrollTop += AUTO_SCROLL_SPEED * ((timestamp - lastTimestamp) / 1000); lastTimestamp = timestamp }
  const maxScrollTop = container.scrollHeight - container.clientHeight
  if (container.scrollTop >= maxScrollTop) {
    container.scrollTop = maxScrollTop
    stopAnimationFrameOnly()
    restartTimerId = window.setTimeout(() => { container.scrollTop = 0; restartTimerId = null; lastTimestamp = null; startAutoScroll() }, AUTO_SCROLL_BOTTOM_PAUSE_MS)
    return
  }
  animationFrameId = window.requestAnimationFrame(stepAutoScroll)
}
function startAutoScroll() { const container = newsScrollRef.value; stopAnimationFrameOnly(); if (!container || isAutoScrollPaused || container.scrollHeight <= container.clientHeight) return; animationFrameId = window.requestAnimationFrame(stepAutoScroll) }
function pauseAutoScroll() { isAutoScrollPaused = true; stopAutoScroll() }
function resumeAutoScroll() { isAutoScrollPaused = false; lastTimestamp = null; startAutoScroll() }
onMounted(() => { nextTick(startAutoScroll) })
onBeforeUnmount(stopAutoScroll)
function formatPublishedAt(value) { if (!value) return '—'; const date = new Date(value); return Number.isNaN(date.getTime()) ? '—' : new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit' }).format(date) }
</script>

<style scoped>
.pm-pulse { min-width: 0; display: flex; flex-direction: column; gap: var(--xc-space-4); padding: var(--xc-space-5); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-md); background: var(--xc-surface-card); }.pm-pulse__heading, .pm-pulse__stats-heading, .pm-pulse__stat-foot { display: flex; align-items: center; justify-content: space-between; gap: var(--xc-space-3); }.pm-pulse__heading p { margin: 0; color: var(--xc-accent-blue); font-size: var(--xc-fs-2xs); letter-spacing: .04em; }.pm-pulse__heading h2 { margin: var(--xc-space-1) 0 0; color: var(--xc-text-strong); font-size: var(--xc-fs-h3); }.pm-pulse__heading > span { color: var(--xc-status-ok); font-size: var(--xc-fs-2xs); }.pm-pulse__stats { display: grid; gap: var(--xc-space-3); padding: var(--xc-space-4); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); background: var(--xc-surface-raised); }.pm-pulse__stats-heading, .pm-pulse__stat-foot, .pm-pulse__news-item span { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }.pm-pulse__filters { display: grid; gap: var(--xc-space-2); }.pm-pulse__filter-row { display: grid; grid-template-columns: 64px minmax(0, 1fr); gap: var(--xc-space-2); align-items: center; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }.pm-pulse__filter-control { width: 100%; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); padding: var(--xc-space-1) var(--xc-space-2); background: var(--xc-surface-control); color: var(--xc-text-soft); font: inherit; text-align: left; cursor: pointer; }.pm-pulse__filter-control:hover, .pm-pulse__filter-control:focus-visible { border-color: var(--xc-border-accent); outline: none; }.pm-pulse__total { display: flex; align-items: baseline; gap: var(--xc-space-2); color: var(--xc-text-mute); font-size: var(--xc-fs-xs); }.pm-pulse__total strong, .pm-pulse__news-item strong { color: var(--xc-text-strong); }.pm-pulse__total strong { font-size: var(--xc-fs-h1); }.pm-pulse__trend { color: var(--xc-trade-up); }.pm-pulse__trend--down { color: var(--xc-trade-down); }.pm-pulse__trend--mute { color: var(--xc-text-mute); }.pm-pulse__news { display: grid; max-height: 432px; overflow-y: auto; overscroll-behavior: contain; }.pm-pulse__news-item { display: grid; gap: var(--xc-space-2); border-bottom: 1px solid var(--xc-border-soft); padding: var(--xc-space-3) 0; color: var(--xc-text-soft); text-align: left; text-decoration: none; }.pm-pulse__news-item a { cursor: pointer; }.pm-pulse__news-item b { color: var(--xc-accent-blue); font-weight: var(--xc-fw-medium); margin-right: var(--xc-space-2); }.pm-pulse__state { margin: var(--xc-space-3) 0; color: var(--xc-text-mute); font-size: var(--xc-fs-xs); text-align: center; }.pm-pulse__state--error { color: var(--xc-status-danger); }
</style>

<style>
.pm-filter-popper.el-popper { padding: var(--xc-space-2); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); background: var(--xc-surface-raised); box-shadow: var(--xc-shadow-md); }.pm-filter-menu { display: grid; max-height: 240px; overflow-y: auto; }.pm-filter-menu__option { border: 0; border-radius: var(--xc-radius-sm); padding: var(--xc-space-2) var(--xc-space-3); background: transparent; color: var(--xc-text-soft); font: inherit; font-size: var(--xc-fs-xs); text-align: left; cursor: pointer; }.pm-filter-menu__option:hover, .pm-filter-menu__option.is-selected { background: var(--xc-surface-frosted); color: var(--xc-text-strong); }.pm-filter-menu__option:focus-visible { outline: 1px solid var(--xc-border-accent); outline-offset: -1px; }
</style>

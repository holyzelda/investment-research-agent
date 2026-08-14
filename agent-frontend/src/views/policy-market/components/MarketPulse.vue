<template>
  <aside class="pm-pulse" aria-label="市场脉搏">
    <header class="pm-pulse__heading"><div><p>POLICY FEED</p><h2>政策材料流</h2></div><div class="pm-pulse__heading-actions"><span><Radio :size="13" />实时更新</span><button type="button" class="pm-pulse__share-button" :disabled="!news.length" aria-label="分享当前政策材料" title="分享当前政策材料" data-share-button @click="openShareDialog"><Share2 :size="15" /><small>{{ news.length }}</small></button></div></header>
    <section class="pm-pulse__stats" aria-label="资讯概览">
      <div class="pm-pulse__stats-heading"><span>资讯概览</span><span>实时</span></div>
      <div class="pm-pulse__filters">
        <div class="pm-pulse__filter-row">
          <span>省份</span>
          <ElPopover v-model:visible="provinceOpen" placement="bottom-end" trigger="click" popper-class="pm-filter-popper">
            <template #reference><button type="button" class="pm-pulse__filter-control" data-filter="province" aria-label="筛选省份" aria-haspopup="listbox" :aria-expanded="provinceOpen" aria-controls="pm-province-menu"><span>{{ provinceLabel }}</span><ChevronDown :size="14" /></button></template>
            <div id="pm-province-menu" class="pm-filter-menu" role="listbox" aria-label="省份选项"><button v-for="option in provinceOptions" :key="option" type="button" class="pm-filter-menu__option" role="option" :aria-selected="draftFilters.province === option" :class="{ 'is-selected': draftFilters.province === option }" :data-test="`province-${option}`" @click="selectFilter('province', option)">{{ option === 'all' ? '全部省份' : option }}</button></div>
          </ElPopover>
        </div>
        <div class="pm-pulse__filter-row">
          <span>时间范围</span>
          <ElDatePicker
            class="pm-pulse__date-picker"
            data-filter="date-range"
            type="daterange"
            :model-value="dateRangeValue"
            value-format="YYYY-MM-DD"
            format="YYYY/MM/DD"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            unlink-panels
            clearable
            popper-class="pm-date-range-popper"
            aria-label="筛选日期范围"
            @update:model-value="handleDateRangeChange"
          />
        </div>
        <div class="pm-pulse__filter-row">
          <span>资讯主题</span>
          <ElPopover v-model:visible="topicOpen" placement="bottom-end" trigger="click" popper-class="pm-filter-popper">
            <template #reference><button type="button" class="pm-pulse__filter-control" data-filter="topic" aria-label="筛选资讯主题" aria-haspopup="listbox" :aria-expanded="topicOpen" aria-controls="pm-topic-menu"><span>{{ topicLabel }}</span><ChevronDown :size="14" /></button></template>
            <div id="pm-topic-menu" class="pm-filter-menu" role="listbox" aria-label="资讯主题选项"><button type="button" class="pm-filter-menu__option" role="option" :aria-selected="draftFilters.topic === 'all'" :class="{ 'is-selected': draftFilters.topic === 'all' }" data-test="topic-all" @click="selectFilter('topic', 'all')">全部主题</button><button v-for="option in topicOptions" :key="option.value" type="button" class="pm-filter-menu__option" role="option" :aria-selected="draftFilters.topic === option.value" :class="{ 'is-selected': draftFilters.topic === option.value }" :data-test="`topic-${option.value}`" @click="selectFilter('topic', option.value)">{{ option.label }}</button></div>
          </ElPopover>
        </div>
      </div>
      <p v-if="statsLoading" class="pm-pulse__state">正在更新统计</p><p v-else-if="statsError" class="pm-pulse__state pm-pulse__state--error">统计加载失败</p>
      <template v-else><div class="pm-pulse__total"><strong class="xc-num">{{ stats.total }}</strong><span>条资讯</span></div><div class="pm-pulse__stat-foot"><span>{{ stats.rangeLabel }}</span><span v-if="stats.trendPercent === null" class="pm-pulse__trend pm-pulse__trend--mute"></span><span v-else class="pm-pulse__trend" :class="{ 'pm-pulse__trend--down': stats.trendPercent < 0 }">较上期 {{ stats.trendPercent > 0 ? '+' : '' }}{{ stats.trendPercent }}%</span></div></template>
    </section>
    <div ref="newsScrollRef" class="pm-pulse__news" data-news-scroll @mouseenter="pauseAutoScroll" @mouseleave="resumeAutoScroll" @wheel="pauseAutoScroll" @touchstart="pauseAutoScroll" @pointerdown="pauseAutoScroll">
      <p v-if="loading" class="pm-pulse__state">正在加载市场资讯</p><p v-else-if="error" class="pm-pulse__state pm-pulse__state--error">{{ error }}</p><p v-else-if="!news.length" class="pm-pulse__state">暂无市场资讯</p>
      <article v-else v-for="item in news" :key="item.id" :data-news-id="item.id" class="pm-pulse__news-item">
        <a v-if="item.linkUrl" class="pm-pulse__news-link" :href="item.linkUrl" target="_blank" rel="noopener noreferrer"><strong>{{ item.title }}</strong><ExternalLink :size="12" /></a>
        <strong v-else class="pm-pulse__news-title">{{ item.title }}</strong>
        <div class="pm-pulse__news-footer">
          <span><b v-for="tag in item.tags" :key="tag">{{ tag }}</b>{{ formatPublishedAt(item.publishTime) }}</span>
          <button type="button" class="pm-pulse__item-share" :aria-label="`分享${item.title}`" :title="`分享${item.title}`" :data-share-news-id="item.id" @click="copySingleNews(item)">
            <Check v-if="singleShareStatus === item.id" :size="12" /><Share2 v-else :size="12" />{{ singleShareStatus === item.id ? '已复制' : '分享' }}
          </button>
        </div>
      </article>
    </div>
  </aside>
  <ElDialog v-model="shareDialogOpen" title="分享政策材料" width="min(520px, calc(100vw - 32px))" append-to-body class="pm-share-dialog" @closed="resumeAutoScroll">
    <div class="pm-share-dialog__intro"><Share2 :size="18" /><div><strong>分享当前材料流</strong><p>将按当前筛选结果分享，共 {{ news.length }} 条材料。</p></div></div>
    <div class="pm-share-dialog__scope"><span>筛选范围</span><strong>{{ shareScopeLabel }}</strong></div>
    <div class="pm-share-dialog__preview" aria-label="分享内容预览"><article v-for="(item, index) in news" :key="item.id" class="pm-share-dialog__item"><span>{{ String(index + 1).padStart(2, '0') }}</span><div><strong>{{ item.title }}</strong><small>{{ formatNewsMeta(item) }}</small></div></article></div>
    <p v-if="shareStatus" class="pm-share-dialog__status" role="status">{{ shareStatus }}</p>
    <template #footer><div class="pm-share-dialog__footer"><button type="button" class="pm-share-dialog__copy" data-copy-share @click="copyShareContent"><Copy :size="15" />复制分享内容</button></div></template>
  </ElDialog>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElDatePicker, ElDialog, ElPopover } from 'element-plus'
import { Check, ChevronDown, Copy, ExternalLink, Radio, Share2 } from '@lucide/vue'

const props = defineProps({
  filters: { type: Object, default: () => ({ province: 'all', startDate: null, endDate: null, topic: 'all' }) },
  stats: { type: Object, default: () => ({ total: 0, trendPercent: null, rangeLabel: '全部省份 · 全部时间' }) },
  topicOptions: { type: Array, default: () => [] },
  news: { type: Array, default: () => [] }, loading: { type: Boolean, default: false }, error: { type: String, default: '' }, statsLoading: { type: Boolean, default: false }, statsError: { type: String, default: '' },
})
const emit = defineEmits(['filters-change'])
const draftFilters = reactive({ ...props.filters })
const newsScrollRef = ref(null)
const provinceOpen = ref(false)
const topicOpen = ref(false)
const shareDialogOpen = ref(false)
const shareStatus = ref('')
const singleShareStatus = ref(null)
const AUTO_SCROLL_SPEED = 60
const AUTO_SCROLL_BOTTOM_PAUSE_MS = 1200
let animationFrameId = null
let restartTimerId = null
let singleShareTimerId = null
let lastTimestamp = null
let isAutoScrollPaused = false
const provinceOptions = [
  'all', '内蒙古', '广西', '宁夏', '新疆', '西藏',
  '北京', '天津', '上海', '重庆', '河北', '山西', '辽宁', '吉林', '黑龙江',
  '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南', '湖北', '湖南',
  '广东', '海南', '四川', '贵州', '云南', '陕西', '甘肃', '青海', '台湾',
  '香港', '澳门',
]
const provinceLabel = computed(() => draftFilters.province === 'all' ? '全部省份' : draftFilters.province)
const dateRangeValue = computed(() => draftFilters.startDate && draftFilters.endDate ? [draftFilters.startDate, draftFilters.endDate] : null)
const periodLabel = computed(() => dateRangeValue.value ? `${formatFilterDate(dateRangeValue.value[0])} 至 ${formatFilterDate(dateRangeValue.value[1])}` : '全部时间')
const topicLabel = computed(() => draftFilters.topic === 'all' ? '全部主题' : props.topicOptions.find((item) => item.value === draftFilters.topic)?.label || draftFilters.topic)
const shareScopeLabel = computed(() => [provinceLabel.value, periodLabel.value, topicLabel.value].join(' / '))
watch(() => props.filters, (filters) => Object.assign(draftFilters, filters), { deep: true })
watch(() => props.news, () => nextTick(startAutoScroll), { deep: true })
function selectFilter(field, value) {
  draftFilters[field] = value
  if (field === 'province') provinceOpen.value = false
  if (field === 'topic') topicOpen.value = false
  emit('filters-change', { ...draftFilters })
}
function handleDateRangeChange(value) {
  const [startDate, endDate] = Array.isArray(value) ? value : []
  draftFilters.startDate = startDate || null
  draftFilters.endDate = endDate || null
  emit('filters-change', { ...draftFilters })
}
function formatFilterDate(value) { return value ? String(value).replaceAll('-', '/') : '' }
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
function formatNewsMeta(item) { return [item.tags?.join(' · '), formatPublishedAt(item.publishTime), item.linkUrl].filter(Boolean).join(' · ') }
function buildShareContent() {
  const lines = [`政策材料流（${props.news.length} 条）`, `筛选范围：${shareScopeLabel.value}`, '']
  props.news.forEach((item, index) => lines.push(`${index + 1}. ${item.title}`, `   ${formatNewsMeta(item)}`, ''))
  return lines.join('\n').trim()
}
function buildSingleShareContent(item) {
  return ['政策材料', item.title, formatNewsMeta(item)].filter(Boolean).join('\n')
}
async function writeClipboard(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  const copied = document.execCommand('copy')
  document.body.removeChild(textarea)
  if (!copied) throw new Error('复制失败')
}
function openShareDialog() { if (props.news.length) { shareStatus.value = ''; shareDialogOpen.value = true; pauseAutoScroll() } }
async function copyShareContent() {
  try { await writeClipboard(buildShareContent()); shareStatus.value = `已复制 ${props.news.length} 条材料的分享内容。` } catch { shareStatus.value = '复制失败，请检查浏览器剪贴板权限。' }
}
async function copySingleNews(item) {
  try {
    await writeClipboard(buildSingleShareContent(item))
    singleShareStatus.value = item.id
    if (singleShareTimerId !== null) window.clearTimeout(singleShareTimerId)
    singleShareTimerId = window.setTimeout(() => { singleShareStatus.value = null; singleShareTimerId = null }, 1800)
  } catch {
    singleShareStatus.value = null
  }
}
onMounted(() => { nextTick(startAutoScroll) })
onBeforeUnmount(() => { stopAutoScroll(); if (singleShareTimerId !== null) window.clearTimeout(singleShareTimerId) })
function formatPublishedAt(value) { if (!value) return '—'; const date = new Date(value); return Number.isNaN(date.getTime()) ? '—' : new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit' }).format(date) }
</script>

<style scoped>
.pm-pulse { position: sticky; top: 20px; min-width: 0; display: flex; flex-direction: column; gap: 16px; min-height: min(700px, calc(100vh - 104px)); padding: 8px 0 8px 22px; border-left: 1px solid var(--xc-border-soft); background: transparent; }
.pm-pulse__heading, .pm-pulse__stats-heading, .pm-pulse__stat-foot { display: flex; align-items: center; justify-content: space-between; gap: var(--xc-space-3); }
.pm-pulse__heading-actions { min-width: 0; display: flex; align-items: center; justify-content: flex-end; gap: 10px; }
.pm-pulse__heading p { margin: 0; color: var(--xc-text-mute); font-family: var(--xc-font-mono); font-size: 10px; }
.pm-pulse__heading h2 { margin: 4px 0 0; color: var(--xc-text-strong); font-size: var(--xc-fs-md); }
.pm-pulse__heading-actions > span { display: inline-flex; align-items: center; gap: 5px; color: var(--xc-status-ok); font-family: var(--xc-font-mono); font-size: var(--xc-fs-2xs); }
.pm-pulse__share-button { display: inline-flex; align-items: center; gap: 5px; min-height: 28px; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-xs); padding: 5px 7px; background: transparent; color: var(--xc-text-soft); cursor: pointer; }
.pm-pulse__share-button:hover:not(:disabled), .pm-pulse__share-button:focus-visible { border-color: var(--xc-border-accent); color: var(--pm-accent, var(--xc-accent-blue)); outline: none; }
.pm-pulse__share-button:disabled { color: var(--xc-text-faint); cursor: not-allowed; opacity: .6; }
.pm-pulse__share-button small { font-family: var(--xc-font-mono); font-size: 10px; }
.pm-pulse__stats { display: grid; gap: 12px; padding: 16px; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); background: var(--pm-surface, var(--xc-surface-card)); }
.pm-pulse__stats-heading, .pm-pulse__stat-foot, .pm-pulse__news-footer span { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.pm-pulse__stats-heading > :first-child { color: var(--xc-text-strong); font-weight: var(--xc-fw-semi); }
.pm-pulse__filters { display: grid; gap: var(--xc-space-2); }
.pm-pulse__filter-row { display: grid; grid-template-columns: 64px minmax(0, 1fr); gap: var(--xc-space-2); align-items: center; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.pm-pulse__filter-control { width: 100%; min-height: 34px; display: flex; align-items: center; justify-content: space-between; gap: 6px; overflow: hidden; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); padding: 6px 8px; background: var(--pm-elevated, var(--xc-surface-control)); color: var(--xc-text-soft); font: inherit; text-align: left; cursor: pointer; }
.pm-pulse__filter-control span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pm-pulse__filter-control:hover, .pm-pulse__filter-control:focus-visible { border-color: var(--xc-border-accent); outline: none; }
.pm-pulse__date-picker { width: 100% !important; min-width: 0; height: 34px; border: 0; border-radius: var(--xc-radius-sm); padding: 0; background: transparent !important; box-shadow: none !important; --el-fill-color-blank: var(--pm-elevated, var(--xc-surface-control)); --el-fill-color-light: var(--pm-elevated, var(--xc-surface-control)); --el-border-color: var(--xc-border-soft); --el-border-color-hover: var(--xc-border-accent); --el-text-color-regular: var(--xc-text-soft); --el-text-color-placeholder: var(--xc-text-mute); }
.pm-pulse__date-picker.el-input__wrapper { min-width: 0; height: 34px; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); padding: 0 8px; background: var(--pm-elevated, var(--xc-surface-control)) !important; box-shadow: none !important; }
.pm-pulse__date-picker.el-input__wrapper:hover, .pm-pulse__date-picker.el-input__wrapper.is-active, .pm-pulse__date-picker.el-input__wrapper:focus-within { border-color: var(--xc-border-accent); box-shadow: none !important; }
.pm-pulse__date-picker :deep(.el-range-input) { min-width: 0; overflow: hidden; background: transparent; color: var(--xc-text-soft); font: inherit; font-size: var(--xc-fs-2xs); text-overflow: ellipsis; }
.pm-pulse__date-picker :deep(.el-range-input::placeholder) { color: var(--xc-text-mute); }
.pm-pulse__date-picker :deep(.el-range-separator) { flex: 0 0 auto; width: auto; padding: 0 3px; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.pm-pulse__date-picker :deep(.el-input__prefix), .pm-pulse__date-picker :deep(.el-input__suffix), .pm-pulse__date-picker :deep(.el-input__icon) { color: var(--xc-text-mute); }
.pm-pulse__date-picker :deep(.el-input__clear:hover), .pm-pulse__date-picker :deep(.el-input__icon:hover) { color: var(--pm-accent, var(--xc-accent-blue)); }
.pm-pulse__total { display: flex; align-items: baseline; gap: var(--xc-space-2); color: var(--xc-text-mute); font-size: var(--xc-fs-xs); }
.pm-pulse__total strong, .pm-pulse__news-item strong { color: var(--xc-text-strong); }
.pm-pulse__total strong { color: var(--pm-accent, var(--xc-accent-blue)); font-size: 34px; line-height: 1; }
.pm-pulse__trend { color: var(--xc-trade-up); }
.pm-pulse__trend--down { color: var(--xc-trade-down); }
.pm-pulse__trend--mute { color: var(--xc-text-mute); }
.pm-pulse__news { display: grid; max-height: min(432px, 46vh); overflow-y: auto; overscroll-behavior: contain; scrollbar-width: none; -ms-overflow-style: none; }
.pm-pulse__news::-webkit-scrollbar { display: none; width: 0; height: 0; }
.pm-pulse__news-item { display: grid; gap: 8px; border-bottom: 1px solid var(--xc-border-soft); padding: 13px 10px 13px 0; color: var(--xc-text-soft); text-align: left; text-decoration: none; transition: background-color 120ms ease, padding 120ms ease; }
.pm-pulse__news-item:hover { background: var(--xc-surface-frosted); }
.pm-pulse__news-link { min-width: 0; display: flex; align-items: flex-start; gap: 6px; color: inherit; text-decoration: none; }
.pm-pulse__news-link:focus-visible { border-radius: var(--xc-radius-xs); outline: 1px solid var(--pm-accent, var(--xc-accent-blue)); outline-offset: 2px; }
.pm-pulse__news-link svg { flex: 0 0 auto; margin-top: 3px; color: var(--xc-text-mute); }
.pm-pulse__news-link strong, .pm-pulse__news-title { display: -webkit-box; min-width: 0; overflow: hidden; font-size: var(--xc-fs-xs); line-height: var(--xc-lh-normal); -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.pm-pulse__news-footer { min-width: 0; display: flex; align-items: flex-end; justify-content: space-between; gap: 8px; }
.pm-pulse__news-footer span { min-width: 0; display: flex; align-items: center; flex-wrap: wrap; gap: 5px; font-family: var(--xc-font-mono); }
.pm-pulse__news-item b { display: inline-block; color: var(--pm-accent, var(--xc-accent-blue)); font-weight: var(--xc-fw-medium); margin-right: 2px; }
.pm-pulse__item-share { flex: 0 0 auto; display: inline-flex; align-items: center; gap: 4px; min-height: 24px; border: 0; border-radius: var(--xc-radius-xs); padding: 3px 5px; background: transparent; color: var(--xc-text-mute); font: inherit; font-size: var(--xc-fs-2xs); cursor: pointer; }
.pm-pulse__item-share:hover, .pm-pulse__item-share:focus-visible { background: var(--xc-surface-control); color: var(--pm-accent, var(--xc-accent-blue)); outline: none; }
.pm-pulse__state { margin: var(--xc-space-3) 0; color: var(--xc-text-mute); font-size: var(--xc-fs-xs); text-align: center; }
.pm-pulse__state--error { color: var(--xc-status-danger); }
@media (max-width: 1280px) { .pm-pulse { position: static; min-height: 0; padding: 26px 0 0; border-top: 1px solid var(--xc-border-soft); border-left: 0; }.pm-pulse__stats { grid-template-columns: minmax(230px, 300px) minmax(0, 1fr); align-items: start; }.pm-pulse__stats-heading, .pm-pulse__total, .pm-pulse__stat-foot { grid-column: 1; }.pm-pulse__filters { grid-column: 2; grid-row: 1 / span 3; }.pm-pulse__news { grid-template-columns: repeat(2, minmax(0, 1fr)); max-height: 360px; column-gap: 24px; }.pm-pulse__news-item { align-content: start; } }
@media (max-width: 640px) { .pm-pulse__heading { align-items: flex-start; }.pm-pulse__heading-actions { flex-wrap: wrap; gap: 6px 10px; }.pm-pulse__stats { grid-template-columns: 1fr; }.pm-pulse__stats-heading, .pm-pulse__total, .pm-pulse__stat-foot, .pm-pulse__filters { grid-column: 1; grid-row: auto; }.pm-pulse__news { grid-template-columns: 1fr; max-height: 420px; } }
@media (prefers-reduced-motion: reduce) { .pm-pulse__news-item { transition: none; } }
</style>

<style>
.pm-filter-popper.el-popper { padding: var(--xc-space-2); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); background: var(--xc-surface-raised); box-shadow: var(--xc-shadow-md); }.pm-filter-menu { display: grid; max-height: 240px; overflow-y: auto; }.pm-filter-menu__option { border: 0; border-radius: var(--xc-radius-sm); padding: var(--xc-space-2) var(--xc-space-3); background: transparent; color: var(--xc-text-soft); font: inherit; font-size: var(--xc-fs-xs); text-align: left; cursor: pointer; }.pm-filter-menu__option:hover, .pm-filter-menu__option.is-selected { background: var(--xc-surface-frosted); color: var(--xc-text-strong); }.pm-filter-menu__option:focus-visible { outline: 1px solid var(--xc-border-accent); outline-offset: -1px; }
.pm-pulse__date-picker.el-date-editor.el-range-editor.el-input__wrapper { width: 100% !important; min-width: 0 !important; height: 34px !important; box-sizing: border-box !important; border: 1px solid var(--xc-border-soft) !important; border-radius: var(--xc-radius-sm) !important; padding: 0 8px !important; background: var(--pm-elevated, var(--xc-surface-control)) !important; box-shadow: none !important; }
.pm-pulse__date-picker.el-date-editor.el-range-editor.el-input__wrapper:hover, .pm-pulse__date-picker.el-date-editor.el-range-editor.el-input__wrapper.is-active, .pm-pulse__date-picker.el-date-editor.el-range-editor.el-input__wrapper:focus-within { border-color: var(--xc-border-accent) !important; background: var(--pm-elevated, var(--xc-surface-control)) !important; box-shadow: none !important; }
.pm-pulse__date-picker.el-date-editor .el-range-input { min-width: 0 !important; width: 0 !important; flex: 1 1 0 !important; overflow: hidden !important; background: transparent !important; color: var(--xc-text-soft) !important; font: inherit !important; font-size: var(--xc-fs-2xs) !important; text-overflow: ellipsis; }
.pm-pulse__date-picker.el-date-editor .el-range-input::placeholder { color: var(--xc-text-mute) !important; }
.pm-pulse__date-picker.el-date-editor .el-range-separator { flex: 0 0 auto !important; width: auto !important; padding: 0 3px !important; color: var(--xc-text-mute) !important; font-size: var(--xc-fs-2xs) !important; }
.pm-pulse__date-picker.el-date-editor .el-input__prefix, .pm-pulse__date-picker.el-date-editor .el-input__suffix, .pm-pulse__date-picker.el-date-editor .el-input__icon { color: var(--xc-text-mute) !important; }
.pm-date-range-popper.el-picker-panel, .pm-date-range-popper.el-popper { --el-bg-color-overlay: var(--xc-surface-raised); --el-bg-color: var(--xc-surface-raised); --el-fill-color-blank: var(--xc-surface-raised); --el-fill-color-light: var(--xc-surface-frosted); --el-fill-color-lighter: var(--xc-surface-frosted); --el-border-color-light: var(--xc-border-soft); --el-border-color-lighter: var(--xc-border-soft); --el-text-color-primary: var(--xc-text-strong); --el-text-color-regular: var(--xc-text-soft); --el-text-color-secondary: var(--xc-text-mute); --el-text-color-placeholder: var(--xc-text-mute); overflow: hidden; border: 1px solid var(--xc-border-strong) !important; border-radius: var(--xc-radius-sm) !important; background: var(--xc-surface-raised) !important; box-shadow: var(--xc-shadow-md) !important; color: var(--xc-text-soft) !important; }
.pm-date-range-popper .el-picker-panel__body-wrapper, .pm-date-range-popper .el-picker-panel__body, .pm-date-range-popper .el-date-range-picker__content, .pm-date-range-popper .el-date-table, .pm-date-range-popper .el-date-table td, .pm-date-range-popper .el-date-table th { background: transparent !important; }
.pm-date-range-popper .el-date-range-picker__header { color: var(--xc-text-strong) !important; }
.pm-date-range-popper .el-date-range-picker__header button, .pm-date-range-popper .el-picker-panel__icon-btn { color: var(--xc-text-mute) !important; }
.pm-date-range-popper .el-date-range-picker__header button:hover, .pm-date-range-popper .el-picker-panel__icon-btn:hover { color: var(--pm-accent, var(--xc-accent-blue)) !important; }
.pm-date-range-popper .el-date-table th { border-bottom: 1px solid var(--xc-border-soft) !important; color: var(--xc-text-mute) !important; }
.pm-date-range-popper .el-date-table td { color: var(--xc-text-soft) !important; }
.pm-date-range-popper .el-date-table td.available:hover { color: var(--pm-accent, var(--xc-accent-blue)) !important; }
.pm-date-range-popper .el-date-table td.in-range .el-date-table-cell { background: rgba(84, 198, 214, .14) !important; }
.pm-date-range-popper .el-date-table td.start-date .el-date-table-cell, .pm-date-range-popper .el-date-table td.end-date .el-date-table-cell { background: var(--pm-accent, var(--xc-accent-blue)) !important; color: #101719 !important; }
.pm-date-range-popper .el-date-table td.prev-month, .pm-date-range-popper .el-date-table td.next-month { color: var(--xc-text-faint) !important; }
.pm-date-range-popper .el-date-table td.today .el-date-table-cell__text { color: var(--pm-accent, var(--xc-accent-blue)) !important; }
.pm-date-range-popper .el-date-table td.start-date.today .el-date-table-cell__text, .pm-date-range-popper .el-date-table td.end-date.today .el-date-table-cell__text { color: #101719 !important; }
.pm-date-range-popper .el-date-range-picker__content.is-left { border-right: 1px solid var(--xc-border-soft) !important; }
.pm-date-range-popper .el-date-picker__header-label, .pm-date-range-popper .el-date-range-picker__header-label { color: var(--xc-text-strong) !important; }
.pm-date-range-popper .el-picker-panel__footer { border-top: 1px solid var(--xc-border-soft) !important; background: var(--xc-surface-raised) !important; }
.pm-date-range-popper .el-picker-panel__link-btn, .pm-date-range-popper .el-button--text { color: var(--pm-accent, var(--xc-accent-blue)) !important; }
.pm-share-dialog { border: 1px solid var(--xc-border-strong); border-radius: var(--xc-radius-sm); background: var(--xc-surface-raised); }
.pm-share-dialog .el-dialog__header { margin-right: 0; border-bottom: 1px solid var(--xc-border-soft); padding: 18px 20px 14px; }
.pm-share-dialog .el-dialog__title { color: var(--xc-text-strong); font-size: var(--xc-fs-md); }
.pm-share-dialog .el-dialog__body { padding: 18px 20px 12px; }
.pm-share-dialog__intro, .pm-share-dialog__scope, .pm-share-dialog__footer { display: flex; align-items: center; gap: 10px; }
.pm-share-dialog__intro { color: var(--pm-accent, var(--xc-accent-blue)); }
.pm-share-dialog__intro strong { color: var(--xc-text-strong); font-size: var(--xc-fs-sm); }
.pm-share-dialog__intro p { margin: 4px 0 0; color: var(--xc-text-mute); font-size: var(--xc-fs-xs); }
.pm-share-dialog__scope { justify-content: space-between; margin: 16px 0 10px; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-xs); padding: 9px 10px; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.pm-share-dialog__scope strong { color: var(--xc-text-soft); font-weight: var(--xc-fw-medium); text-align: right; }
.pm-share-dialog__preview { max-height: 280px; overflow-y: auto; border-top: 1px solid var(--xc-border-soft); border-bottom: 1px solid var(--xc-border-soft); scrollbar-width: thin; }
.pm-share-dialog__item { display: grid; grid-template-columns: 28px minmax(0, 1fr); gap: 8px; padding: 10px 0; border-bottom: 1px solid var(--xc-border-soft); }
.pm-share-dialog__item:last-child { border-bottom: 0; }
.pm-share-dialog__item > span { color: var(--pm-accent, var(--xc-accent-blue)); font-family: var(--xc-font-mono); font-size: var(--xc-fs-2xs); }
.pm-share-dialog__item strong { display: block; overflow: hidden; color: var(--xc-text-soft); font-size: var(--xc-fs-xs); line-height: var(--xc-lh-normal); text-overflow: ellipsis; white-space: nowrap; }
.pm-share-dialog__item small { display: block; overflow: hidden; margin-top: 4px; color: var(--xc-text-mute); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.pm-share-dialog__status { margin: 10px 0 0; color: var(--pm-accent, var(--xc-accent-blue)); font-size: var(--xc-fs-2xs); text-align: right; }
.pm-share-dialog__footer { justify-content: flex-end; }
.pm-share-dialog__footer button { display: inline-flex; align-items: center; gap: 6px; border-radius: var(--xc-radius-xs); padding: 8px 12px; font: inherit; font-size: var(--xc-fs-xs); cursor: pointer; }
.pm-share-dialog__copy { border: 1px solid var(--pm-accent, var(--xc-accent-blue)); background: var(--pm-accent, var(--xc-accent-blue)); color: #101719; }
.pm-share-dialog__footer button:hover, .pm-share-dialog__footer button:focus-visible { filter: brightness(1.12); outline: none; }
@media (max-width: 480px) {
  .pm-date-range-popper .el-date-range-picker__content { padding: 8px; }
  .pm-share-dialog .el-dialog__header { padding: 16px 16px 12px; }
  .pm-share-dialog .el-dialog__body { padding: 16px 16px 10px; }
  .pm-share-dialog__scope { align-items: flex-start; flex-direction: column; gap: 5px; }
  .pm-share-dialog__scope strong { max-width: 100%; text-align: left; overflow-wrap: anywhere; }
  .pm-share-dialog__item strong, .pm-share-dialog__item small { white-space: normal; overflow-wrap: anywhere; }
  .pm-share-dialog__item strong { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
  .pm-share-dialog__item small { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
  .pm-share-dialog__footer { display: flex; }
  .pm-share-dialog__footer button { min-width: 0; justify-content: center; padding-inline: 8px; }
}
</style>

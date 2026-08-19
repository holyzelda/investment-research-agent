<template>
  <section class="ledger-page">
    <header class="ledger-head">
      <div>
        <span class="ledger-eyebrow">ZRA / PERSONAL WORKSPACE</span>
        <h1>测算台账</h1>
        <p>查询由我发起的已完成测算</p>
      </div>
      <div class="ledger-count" aria-live="polite">
        <strong>{{ total }}</strong>
        <span>条记录</span>
      </div>
    </header>

    <form class="ledger-filters" @submit.prevent="submitSearch">
      <label class="ledger-field ledger-field--keyword">
        <span>会话名称</span>
        <input v-model.trim="draft.keyword" type="search" placeholder="搜索会话名称" />
      </label>
      <label class="ledger-field">
        <span>省份</span>
        <div ref="provincePickerRef" class="ledger-province-picker">
          <button
            class="ledger-province-trigger"
            type="button"
            :aria-expanded="provinceOpen"
            aria-haspopup="listbox"
            aria-label="省份多选"
            @click="provinceOpen = !provinceOpen"
          >
            <span v-if="!draft.provinces.length" class="ledger-province-placeholder">选择省份</span>
            <span v-else class="ledger-province-summary">
              <span v-for="province in draft.provinces.slice(0, 2)" :key="province" class="ledger-province-tag">{{ province }}</span>
              <span v-if="draft.provinces.length > 2" class="ledger-province-more">+{{ draft.provinces.length - 2 }}</span>
            </span>
            <ChevronDown :class="{ 'is-open': provinceOpen }" aria-hidden="true" />
          </button>
          <div v-if="provinceOpen" class="ledger-province-menu" role="listbox" aria-multiselectable="true">
            <div class="ledger-province-menu__tools">
              <Search aria-hidden="true" />
              <input v-model.trim="provinceSearch" type="search" placeholder="搜索省份" aria-label="搜索省份" />
              <button v-if="draft.provinces.length" type="button" @click="draft.provinces = []">清空</button>
            </div>
            <div v-if="!filteredProvinces.length" class="ledger-province-empty">没有匹配的省份</div>
            <label v-for="province in filteredProvinces" :key="province" class="ledger-province-option">
              <input
                type="checkbox"
                :checked="draft.provinces.includes(province)"
                @change="toggleProvince(province)"
              />
              <span>{{ province }}</span>
            </label>
          </div>
        </div>
      </label>
      <div class="ledger-field ledger-field--date">
        <span>测算时间</span>
        <div ref="datePickerRef" class="ledger-date-picker">
          <button
            v-for="preset in presets"
            :key="preset.key"
            class="ledger-preset"
            :class="{ 'is-active': draft.preset === preset.key }"
            type="button"
            @click="setPreset(preset.key)"
          >{{ preset.label }}</button>
          <button class="ledger-date-trigger" type="button" :aria-expanded="dateOpen" @click="openDatePicker">
            <Calendar aria-hidden="true" />
            <span>{{ formatDisplayDate(draft.startDate) || '开始日期' }}</span>
            <span class="ledger-date-separator">至</span>
            <span>{{ formatDisplayDate(draft.endDate) || '结束日期' }}</span>
          </button>
          <div v-if="dateOpen" class="ledger-calendar" role="dialog" aria-label="选择测算时间范围">
            <header class="ledger-calendar__head">
              <button type="button" aria-label="上个月" @click="shiftCalendar(-1)"><ChevronLeft aria-hidden="true" /></button>
              <strong>{{ calendarTitle }}</strong>
              <button type="button" aria-label="下个月" @click="shiftCalendar(1)"><ChevronRight aria-hidden="true" /></button>
            </header>
            <div class="ledger-calendar__weekdays">
              <span v-for="weekday in weekdays" :key="weekday">{{ weekday }}</span>
            </div>
            <div class="ledger-calendar__days">
              <button
                v-for="day in calendarDays"
                :key="day.iso"
                type="button"
                :class="{ 'is-outside': !day.currentMonth, 'is-start': day.iso === draft.startDate, 'is-end': day.iso === draft.endDate, 'is-in-range': isDateInRange(day.iso) }"
                @click="selectCalendarDay(day.iso)"
              >{{ day.day }}</button>
            </div>
            <footer class="ledger-calendar__foot">
              <span>{{ calendarHint }}</span>
              <button type="button" @click="clearDates">清空</button>
            </footer>
          </div>
        </div>
      </div>
      <div class="ledger-filter-actions">
        <button class="ledger-button ledger-button--primary" type="submit" :disabled="loading">
          <Search aria-hidden="true" />
          查询
        </button>
        <button class="ledger-button ledger-button--quiet" type="button" @click="resetSearch">重置</button>
      </div>
    </form>

    <div class="ledger-table-shell">
      <div v-if="loading" class="ledger-state">正在加载测算记录...</div>
      <div v-else-if="!items.length" class="ledger-state ledger-state--empty">
        <ClipboardList aria-hidden="true" />
        <strong>暂无匹配的测算记录</strong>
        <span>调整筛选条件后重新查询</span>
      </div>
      <table v-else class="ledger-table">
        <thead>
          <tr>
            <th>测算时间</th>
            <th class="ledger-table__title">会话名称</th>
            <th>版本</th>
            <th>省份</th>
            <th>项目规模</th>
            <th>节点</th>
            <th>全投资 IRR</th>
            <th>静态回收期</th>
            <th>报告状态</th>
            <th class="ledger-table__actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.taskId">
            <td class="xc-num ledger-table__date" data-label="测算时间">{{ formatDate(item.calculatedAt) }}</td>
            <td class="ledger-table__title" data-label="会话名称">
              <strong :title="item.title || '未命名会话'">{{ item.title || '未命名会话' }}</strong>
            </td>
            <td data-label="版本"><span class="ledger-version">{{ item.version }}</span></td>
            <td data-label="省份">{{ item.province || '—' }}</td>
            <td class="xc-num" data-label="项目规模">{{ formatNumber(item.powerMw) }} MW / {{ formatNumber(item.capacityMwh) }} MWh</td>
            <td data-label="节点">{{ item.nodeName || '省级测算' }}</td>
            <td class="xc-num ledger-metric" data-label="全投资 IRR">{{ formatMetric(item.projectIrr, '%') }}</td>
            <td class="xc-num" data-label="静态回收期">{{ formatMetric(item.projectStaticPayback, ' 年') }}</td>
            <td data-label="报告状态"><span class="ledger-status" :class="`is-${item.report.status}`">{{ reportLabel(item.report.status) }}</span></td>
            <td class="ledger-actions" data-label="操作">
              <a
                class="ledger-icon-button"
                :href="resultUrl(item)"
                target="_blank"
                rel="noopener noreferrer"
                title="查看测算结果"
              >
                <ArrowUpRight aria-hidden="true" />
                <span>结果</span>
              </a>
              <a
                v-if="item.report.status === 'completed' && item.report.reportId"
                class="ledger-icon-button ledger-icon-button--report"
                :href="reportUrl(item.report.reportId)"
                target="_blank"
                rel="noopener noreferrer"
                title="查看报告"
              >
                <FileText aria-hidden="true" />
                <span>报告</span>
              </a>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer v-if="total" class="ledger-pagination">
      <span>共 {{ total }} 条</span>
      <div class="ledger-pages">
        <button class="ledger-page-button" type="button" :disabled="page <= 1" aria-label="上一页" @click="changePage(page - 1)">
          <ChevronLeft aria-hidden="true" />
        </button>
        <span class="xc-num">{{ page }} / {{ pageCount }}</span>
        <button class="ledger-page-button" type="button" :disabled="page >= pageCount" aria-label="下一页" @click="changePage(page + 1)">
          <ChevronRight aria-hidden="true" />
        </button>
      </div>
    </footer>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowUpRight, Calendar, ChevronDown, ChevronLeft, ChevronRight, ClipboardList, FileText, Search } from '@lucide/vue'
import { getLedgerProvinces, getLedgerRecords } from '@/api/ledger'

const router = useRouter()
const pageSize = 10
const items = ref([])
const provinces = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const provinceOpen = ref(false)
const provinceSearch = ref('')
const provincePickerRef = ref(null)
const dateOpen = ref(false)
const datePickerRef = ref(null)
const calendarMonth = ref(new Date(new Date().getFullYear(), new Date().getMonth(), 1))
const calendarPart = ref('start')
const weekdays = ['日', '一', '二', '三', '四', '五', '六']
const presets = [
  { key: '7d', label: '近 7 天' },
  { key: '14d', label: '近 14 天' },
  { key: '30d', label: '近 30 天' },
  { key: 'month', label: '本月' },
]

function isoDate(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function defaultDates() {
  const end = new Date()
  const start = new Date(end)
  start.setDate(end.getDate() - 29)
  return { startDate: isoDate(start), endDate: isoDate(end) }
}

const draft = reactive({ keyword: '', provinces: [], preset: '30d', ...defaultDates() })
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const filteredProvinces = computed(() => {
  const keyword = provinceSearch.value.toLowerCase()
  return provinces.value.filter((province) => !keyword || province.toLowerCase().includes(keyword))
})
const calendarTitle = computed(() => `${calendarMonth.value.getFullYear()}年${calendarMonth.value.getMonth() + 1}月`)
const calendarDays = computed(() => {
  const first = calendarMonth.value
  const start = new Date(first.getFullYear(), first.getMonth(), 1 - first.getDay())
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(start.getFullYear(), start.getMonth(), start.getDate() + index)
    return { iso: isoDate(date), day: date.getDate(), currentMonth: date.getMonth() === first.getMonth() }
  })
})
const calendarHint = computed(() => calendarPart.value === 'start' ? '先选择开始日期' : '再选择结束日期')

function toggleProvince(province) {
  draft.provinces = draft.provinces.includes(province)
    ? draft.provinces.filter((item) => item !== province)
    : [...draft.provinces, province]
}

function onProvinceOutsideClick(event) {
  if (provinceOpen.value && !provincePickerRef.value?.contains(event.target)) provinceOpen.value = false
  if (dateOpen.value && !datePickerRef.value?.contains(event.target)) dateOpen.value = false
}

function openDatePicker() {
  dateOpen.value = !dateOpen.value
  if (dateOpen.value) {
    calendarPart.value = 'start'
    const base = draft.startDate ? new Date(`${draft.startDate}T00:00:00`) : new Date()
    calendarMonth.value = new Date(base.getFullYear(), base.getMonth(), 1)
  }
}

function shiftCalendar(offset) {
  calendarMonth.value = new Date(calendarMonth.value.getFullYear(), calendarMonth.value.getMonth() + offset, 1)
}

function selectCalendarDay(value) {
  draft.preset = 'custom'
  if (calendarPart.value === 'start') {
    draft.startDate = value
    draft.endDate = ''
    calendarPart.value = 'end'
    return
  }
  if (value < draft.startDate) {
    draft.startDate = value
    draft.endDate = ''
    calendarPart.value = 'end'
    return
  }
  draft.endDate = value
  dateOpen.value = false
}

function isDateInRange(value) {
  return Boolean(draft.startDate && draft.endDate && value > draft.startDate && value < draft.endDate)
}

function clearDates() {
  draft.startDate = ''
  draft.endDate = ''
  draft.preset = 'custom'
  calendarPart.value = 'start'
}

function setPreset(key) {
  const now = new Date()
  const start = new Date(now)
  if (key === '7d') start.setDate(now.getDate() - 6)
  if (key === '14d') start.setDate(now.getDate() - 13)
  if (key === '30d') start.setDate(now.getDate() - 29)
  if (key === 'month') start.setDate(1)
  draft.preset = key
  draft.startDate = isoDate(start)
  draft.endDate = isoDate(now)
}

function queryParams(targetPage = page.value) {
  const params = { page: targetPage, page_size: pageSize, start_date: draft.startDate, end_date: draft.endDate }
  if (draft.keyword) params.keyword = draft.keyword
  if (draft.provinces.length) params.province = draft.provinces
  return params
}

async function fetchRecords(targetPage = 1) {
  loading.value = true
  try {
    const response = await getLedgerRecords(queryParams(targetPage))
    const data = response?.data || {}
    items.value = data.items || []
    total.value = data.total || 0
    page.value = data.page || targetPage
  } catch (error) {
    items.value = []
    total.value = 0
    ElMessage.error('测算台账加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function submitSearch() {
  if (draft.startDate && draft.endDate && draft.startDate > draft.endDate) {
    ElMessage.warning('开始日期不能晚于结束日期')
    return
  }
  fetchRecords(1)
}

function resetSearch() {
  Object.assign(draft, { keyword: '', provinces: [], preset: '30d', ...defaultDates() })
  fetchRecords(1)
}

function changePage(targetPage) {
  if (targetPage >= 1 && targetPage <= pageCount.value) fetchRecords(targetPage)
}

function resultUrl(item) {
  if (!item?.conversationId || item?.taskId === null || item?.taskId === undefined) return '#'
  return router.resolve({
    path: '/home',
    query: { conversationId: item.conversationId, taskId: item.taskId },
  }).href
}

function reportUrl(reportId) {
  if (!reportId) return '#'
  return router.resolve({ name: 'ReportDetail', params: { reportId } }).href
}

function formatDate(value) {
  const date = new Date(String(value || '').replace(' ', 'T'))
  if (Number.isNaN(date.getTime())) return '—'
  return `${isoDate(date)} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function formatDisplayDate(value) {
  if (!value) return ''
  const parts = String(value).split('-')
  return parts.length === 3 ? `${parts[0]}/${parts[1]}/${parts[2]}` : value
}

function formatNumber(value) {
  if (value === null || value === undefined || value === '') return '—'
  return Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function formatMetric(value, suffix = '') {
  if (value === null || value === undefined || value === '') return '—'
  return `${Number(value).toFixed(2)}${suffix}`
}

function reportLabel(status) {
  return { not_generated: '未生成', generating: '生成中', completed: '已生成', failed: '生成失败' }[status] || '未生成'
}

onMounted(async () => {
  document.addEventListener('pointerdown', onProvinceOutsideClick)
  try {
    const response = await getLedgerProvinces()
    provinces.value = response?.data?.items || []
  } catch (error) {
    provinces.value = []
  }
  fetchRecords(1)
})

onBeforeUnmount(() => document.removeEventListener('pointerdown', onProvinceOutsideClick))
</script>

<style scoped>
.ledger-page { min-height: 100%; padding: 42px clamp(24px, 4vw, 68px) 48px; color: var(--xc-text-strong); }
.ledger-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; max-width: 1500px; margin: 0 auto 30px; }
.ledger-eyebrow { color: var(--xc-accent-blue); font-family: var(--xc-font-en); font-size: var(--xc-fs-3xs); letter-spacing: .08em; }
.ledger-head h1 { margin: 9px 0 5px; font-size: 34px; font-weight: var(--xc-fw-semi); }
.ledger-head p { margin: 0; color: var(--xc-text-mute); font-size: var(--xc-fs-sm); }
.ledger-count { display: flex; align-items: baseline; gap: 7px; color: var(--xc-text-mute); }
.ledger-count strong { color: var(--xc-text-strong); font-family: var(--xc-font-en); font-size: 28px; font-weight: var(--xc-fw-medium); }
.ledger-count span { font-size: var(--xc-fs-xs); }
.ledger-filters { display: grid; grid-template-columns: minmax(180px, 1fr) 190px minmax(420px, 2fr) auto; align-items: end; gap: 16px; max-width: 1500px; margin: 0 auto 20px; padding: 16px; border: 1px solid var(--xc-border-card); border-radius: var(--xc-radius-sm); background: var(--xc-surface-raised); box-shadow: var(--xc-shadow-sm); }
.ledger-field { min-width: 0; display: flex; flex-direction: column; gap: 7px; }
.ledger-field > span { display: block; height: 16px; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); line-height: 16px; }
.ledger-field input { width: 100%; height: 36px; box-sizing: border-box; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-xs); outline: 0; background: var(--xc-surface-control); color: var(--xc-text-strong); font: inherit; font-size: var(--xc-fs-xs); }
.ledger-field input { padding: 0 10px; }
.ledger-province-picker { position: relative; width: 100%; }
.ledger-province-trigger { width: 100%; min-height: 36px; padding: 4px 9px; display: flex; align-items: center; gap: 8px; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-xs); background: var(--xc-surface-control); color: var(--xc-text-strong); font: inherit; font-size: var(--xc-fs-xs); text-align: left; cursor: pointer; }
.ledger-province-trigger:hover, .ledger-province-trigger:focus-visible { border-color: var(--xc-accent-blue); outline: 0; box-shadow: 0 0 0 2px var(--xc-status-info-soft); }
.ledger-province-trigger > svg { width: 15px; height: 15px; margin-left: auto; color: var(--xc-text-mute); transition: transform var(--xc-dur-fast); }
.ledger-province-trigger > svg.is-open { transform: rotate(180deg); }
.ledger-province-placeholder { color: var(--xc-text-mute); }
.ledger-province-summary { min-width: 0; display: flex; align-items: center; gap: 5px; overflow: hidden; }
.ledger-province-tag, .ledger-province-more { padding: 2px 6px; border-radius: var(--xc-radius-xs); background: var(--xc-status-info-soft); color: var(--xc-accent-blue); white-space: nowrap; }
.ledger-province-more { background: var(--xc-surface-2); color: var(--xc-text-mute); }
.ledger-province-menu { position: absolute; top: calc(100% + 6px); left: 0; right: 0; z-index: var(--xc-z-raised); max-height: 270px; overflow: auto; padding: 7px; border: 1px solid var(--xc-border-card); border-radius: var(--xc-radius-sm); background: var(--xc-surface-2); box-shadow: var(--xc-shadow-raised); }
.ledger-province-menu__tools { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; padding: 4px 6px; border-bottom: 1px solid var(--xc-border-soft); }
.ledger-province-menu__tools > svg { width: 14px; height: 14px; color: var(--xc-text-mute); }
.ledger-province-menu__tools input { height: 28px; padding: 0; border: 0; background: transparent; font-size: var(--xc-fs-2xs); }
.ledger-province-menu__tools input:focus { box-shadow: none; }
.ledger-province-menu__tools button { flex: 0 0 auto; margin-left: auto; padding: 3px 5px; border: 0; background: transparent; color: var(--xc-accent-blue); font: inherit; font-size: var(--xc-fs-3xs); line-height: 1; white-space: nowrap; cursor: pointer; }
.ledger-province-option { min-height: 34px; padding: 0 6px; display: flex; align-items: center; gap: 8px; border-radius: var(--xc-radius-xs); color: var(--xc-text-soft); font-size: var(--xc-fs-xs); cursor: pointer; }
.ledger-province-option:hover { background: var(--xc-surface-frosted); color: var(--xc-text-strong); }
.ledger-province-option input { width: 15px; height: 15px; accent-color: var(--xc-accent-blue); }
.ledger-province-empty { padding: 18px 8px; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); text-align: center; }
.ledger-preset { height: 36px; padding: 0 9px; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-xs); background: transparent; color: var(--xc-text-mute); font: inherit; font-size: var(--xc-fs-2xs); line-height: 1; white-space: nowrap; cursor: pointer; }
.ledger-preset:hover, .ledger-preset.is-active { border-color: var(--xc-accent-blue); background: var(--xc-status-info-soft); color: var(--xc-accent-blue); }
.ledger-date-picker { position: relative; min-width: 0; display: flex; align-items: center; gap: 6px; }
.ledger-date-trigger { min-width: 215px; height: 36px; padding: 0 8px; display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-xs); background: var(--xc-surface-control); color: var(--xc-text-soft); font: inherit; font-size: var(--xc-fs-2xs); cursor: pointer; }
.ledger-date-trigger:hover, .ledger-date-trigger:focus-visible { border-color: var(--xc-accent-blue); outline: 0; box-shadow: 0 0 0 2px var(--xc-status-info-soft); }
.ledger-date-trigger > svg { width: 14px; height: 14px; flex: 0 0 auto; color: var(--xc-accent-blue); }
.ledger-date-separator { color: var(--xc-text-faint); }
.ledger-calendar { position: absolute; top: calc(100% + 7px); right: 0; z-index: var(--xc-z-raised); width: 286px; padding: 12px; border: 1px solid var(--xc-border-card); border-radius: var(--xc-radius-sm); background: var(--xc-surface-2); box-shadow: var(--xc-shadow-raised); }
.ledger-calendar__head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; color: var(--xc-text-strong); }
.ledger-calendar__head strong { font-size: var(--xc-fs-xs); font-weight: var(--xc-fw-medium); }
.ledger-calendar__head button { width: 28px; height: 28px; display: grid; place-items: center; border: 0; border-radius: var(--xc-radius-xs); background: transparent; color: var(--xc-text-mute); cursor: pointer; }
.ledger-calendar__head button:hover, .ledger-calendar__head button:focus-visible { background: var(--xc-surface-frosted); color: var(--xc-accent-blue); }
.ledger-calendar__head svg { width: 15px; height: 15px; }
.ledger-calendar__weekdays, .ledger-calendar__days { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
.ledger-calendar__weekdays { margin-bottom: 4px; color: var(--xc-text-faint); font-size: var(--xc-fs-3xs); text-align: center; }
.ledger-calendar__days button { width: 32px; height: 30px; justify-self: center; border: 0; border-radius: var(--xc-radius-xs); background: transparent; color: var(--xc-text-soft); font: inherit; font-family: var(--xc-font-en); font-size: var(--xc-fs-2xs); cursor: pointer; }
.ledger-calendar__days button:hover, .ledger-calendar__days button:focus-visible { background: var(--xc-status-info-soft); color: var(--xc-accent-blue); outline: 0; }
.ledger-calendar__days button.is-outside { color: var(--xc-text-faint); }
.ledger-calendar__days button.is-in-range { border-radius: 0; background: var(--xc-status-info-soft); color: var(--xc-accent-blue); }
.ledger-calendar__days button.is-start, .ledger-calendar__days button.is-end { border-radius: var(--xc-radius-xs); background: var(--xc-accent-blue); color: #fff; }
.ledger-calendar__foot { min-height: 26px; margin-top: 9px; padding-top: 9px; display: flex; align-items: center; justify-content: space-between; border-top: 1px solid var(--xc-border-soft); color: var(--xc-text-mute); font-size: var(--xc-fs-3xs); }
.ledger-calendar__foot button { padding: 2px 4px; border: 0; background: transparent; color: var(--xc-accent-blue); font: inherit; cursor: pointer; }
.ledger-filter-actions { display: flex; align-items: center; gap: 8px; }
.ledger-button { height: 36px; padding: 0 13px; display: inline-flex; align-items: center; justify-content: center; gap: 6px; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-xs); font: inherit; font-size: var(--xc-fs-xs); cursor: pointer; }
.ledger-button svg { width: 15px; height: 15px; }
.ledger-button--primary { border-color: var(--xc-accent-blue); background: var(--xc-accent-blue); color: #fff; }
.ledger-button--primary:disabled { opacity: .55; cursor: wait; }
.ledger-button--quiet { background: transparent; color: var(--xc-text-mute); }
.ledger-button--quiet:hover { color: var(--xc-text-strong); background: var(--xc-surface-frosted); }
.ledger-table-shell { max-width: 1500px; min-height: 400px; margin: 0 auto; overflow: auto; border: 1px solid var(--xc-border-card); border-radius: var(--xc-radius-sm); background: var(--xc-surface-raised); box-shadow: var(--xc-shadow-sm); }
.ledger-table { width: 100%; min-width: 1120px; border-collapse: collapse; table-layout: auto; }
.ledger-table th { height: 44px; padding: 0 13px; border-bottom: 1px solid var(--xc-border-card); color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); font-weight: var(--xc-fw-medium); text-align: left; white-space: nowrap; }
.ledger-table td { height: 62px; padding: 0 13px; border-bottom: 1px solid var(--xc-border-soft); color: var(--xc-text-soft); font-size: var(--xc-fs-xs); white-space: nowrap; }
.ledger-table tbody tr:hover { background: var(--xc-surface-frosted); }
.ledger-table tbody tr:last-child td { border-bottom: 0; }
.ledger-table__title { max-width: 190px; }
.ledger-table__title strong { display: block; overflow: hidden; color: var(--xc-text-strong); font-weight: var(--xc-fw-medium); text-overflow: ellipsis; white-space: nowrap; }
.ledger-table__date { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.ledger-version { color: var(--xc-accent-blue); font-family: var(--xc-font-en); }
.ledger-metric { color: var(--xc-status-positive); font-weight: var(--xc-fw-medium); }
.ledger-status { display: inline-flex; padding: 4px 8px; border-radius: var(--xc-radius-full); font-size: var(--xc-fs-3xs); }
.ledger-status.is-not_generated { background: var(--xc-surface-control); color: var(--xc-text-mute); }
.ledger-status.is-generating { background: var(--xc-status-warn-soft); color: var(--xc-status-warn); }
.ledger-status.is-completed { background: var(--xc-status-info-soft); color: var(--xc-status-positive); }
.ledger-status.is-failed { background: var(--xc-status-danger-soft); color: var(--xc-status-danger); }
.ledger-actions { display: flex; align-items: center; gap: 4px; }
.ledger-icon-button { height: 30px; padding: 0 7px; display: inline-flex; align-items: center; gap: 4px; border: 0; border-radius: var(--xc-radius-xs); background: transparent; color: var(--xc-accent-blue); font: inherit; font-size: var(--xc-fs-2xs); text-decoration: none; cursor: pointer; }
.ledger-icon-button:hover { background: var(--xc-status-info-soft); }
.ledger-icon-button--report { color: var(--xc-status-positive); }
.ledger-icon-button--report:hover { background: var(--xc-status-info-soft); }
.ledger-icon-button svg { width: 14px; height: 14px; }
.ledger-state { min-height: 400px; display: grid; place-items: center; align-content: center; gap: 9px; color: var(--xc-text-mute); font-size: var(--xc-fs-xs); }
.ledger-state--empty svg { width: 30px; height: 30px; color: var(--xc-text-faint); }
.ledger-state--empty strong { color: var(--xc-text-soft); font-weight: var(--xc-fw-medium); }
.ledger-state--empty span { color: var(--xc-text-faint); font-size: var(--xc-fs-2xs); }
.ledger-pagination { max-width: 1500px; margin: 16px auto 0; display: flex; align-items: center; justify-content: space-between; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.ledger-pages { display: flex; align-items: center; gap: 12px; }
.ledger-page-button { width: 30px; height: 30px; display: grid; place-items: center; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-xs); background: transparent; color: var(--xc-text-soft); cursor: pointer; }
.ledger-page-button:hover:not(:disabled) { border-color: var(--xc-accent-blue); color: var(--xc-accent-blue); }
.ledger-page-button:disabled { opacity: .35; cursor: not-allowed; }
.ledger-page-button svg { width: 15px; height: 15px; }
@media (max-width: 1280px) {
  .ledger-filters { grid-template-columns: minmax(180px, 1fr) minmax(180px, 1fr) auto; }
  .ledger-field--date { grid-column: 1 / -1; grid-row: 2; }
  .ledger-filter-actions { justify-content: flex-end; }
}
@media (max-width: 900px) {
  .ledger-page { padding: 32px clamp(18px, 3vw, 32px) 42px; }
  .ledger-filters { grid-template-columns: 1fr 1fr; }
  .ledger-field--date { grid-column: 1 / -1; grid-row: auto; }
  .ledger-filter-actions { grid-column: 1 / -1; justify-content: flex-end; }
  .ledger-table { min-width: 980px; }
}
@media (max-width: 680px) {
  .ledger-page { padding: 24px 12px 32px; }
  .ledger-head { align-items: flex-start; flex-direction: column; gap: 14px; margin-bottom: 20px; }
  .ledger-head h1 { font-size: 26px; }
  .ledger-filters { grid-template-columns: 1fr; gap: 13px; padding: 13px; }
  .ledger-field--date, .ledger-filter-actions { grid-column: auto; }
  .ledger-date-picker { flex-wrap: wrap; }
  .ledger-date-trigger { min-width: 0; flex: 1 1 220px; }
  .ledger-filter-actions { justify-content: stretch; }
  .ledger-filter-actions .ledger-button { flex: 1 1 0; min-height: 40px; }
  .ledger-table-shell { overflow: visible; border: 0; background: transparent; box-shadow: none; }
  .ledger-table, .ledger-table thead, .ledger-table tbody, .ledger-table tr, .ledger-table td { display: block; }
  .ledger-table { min-width: 0; }
  .ledger-table thead { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); clip-path: inset(50%); white-space: nowrap; }
  .ledger-table tr { margin-bottom: 12px; padding: 12px 14px; border: 1px solid var(--xc-border-card); border-radius: var(--xc-radius-sm); background: var(--xc-surface-raised); box-shadow: var(--xc-shadow-sm); }
  .ledger-table td { height: auto; min-height: 28px; padding: 6px 0 6px 112px; position: relative; border-bottom: 0; white-space: normal; text-align: right; }
  .ledger-table td::before { content: attr(data-label); position: absolute; left: 0; top: 6px; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); text-align: left; }
  .ledger-table__title { max-width: none; }
  .ledger-table__title strong { white-space: normal; text-align: right; }
  .ledger-actions { justify-content: flex-end; gap: 8px; padding-top: 10px !important; margin-top: 5px; border-top: 1px solid var(--xc-border-soft) !important; }
  .ledger-icon-button { min-height: 36px; padding: 0 10px; }
  .ledger-pagination { padding: 0 2px; }
}
</style>

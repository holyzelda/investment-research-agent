<template>
  <section class="tl-power-trend" aria-label="功率趋势">
    <div class="tl-power-trend__head">
      <div>
        <span class="tl-power-trend__eyebrow">功率趋势</span>
        <strong class="tl-power-trend__caption">{{ rangeCaption }}</strong>
      </div>
    </div>

    <div class="tl-power-trend__ranges" role="group" aria-label="功率趋势日期范围">
      <button
        v-for="item in presetRanges"
        :key="item.key"
        class="tl-power-trend__range"
        :class="{ 'tl-power-trend__range--active': range?.key === item.key }"
        type="button"
        @click="selectPreset(item)"
      >{{ item.label }}</button>
      <div class="tl-power-trend__custom-wrap">
        <button
          class="tl-power-trend__range"
          :class="{ 'tl-power-trend__range--active': range?.key === 'custom' }"
          type="button"
          data-test="custom-range-trigger"
          @click="openCustom"
        >自定义</button>
        <div v-if="customVisible" class="tl-power-trend__custom-panel" role="dialog" aria-label="自定义功率趋势日期">
          <strong>自定义功率趋势日期</strong>
          <div class="tl-power-trend__date-inputs">
            <input v-model="customStartDate" type="date" :max="yesterday()" aria-label="开始日期">
            <span>至</span>
            <input v-model="customEndDate" type="date" :max="yesterday()" aria-label="结束日期">
          </div>
          <div class="tl-power-trend__dialog-actions">
            <button class="tl-power-trend__btn tl-power-trend__btn--ghost" type="button" @click="customVisible = false">取消</button>
            <button class="tl-power-trend__btn tl-power-trend__btn--primary" type="button" :disabled="!isCustomRangeValid" @click="confirmCustom">确认</button>
          </div>
        </div>
      </div>
    </div>

    <div
      ref="el"
      class="tl-power-trend__canvas"
      :class="{ 'tl-power-trend__canvas--hidden': !showChart }"
    />
    <div v-if="loading" class="tl-power-trend__skeleton" aria-live="polite">
      <span class="xc-skeleton xc-skeleton-rect" aria-hidden="true" />
      <span>正在加载功率趋势</span>
    </div>
    <div v-else-if="error" class="tl-power-trend__state" role="alert">
      <span>{{ error }}</span>
      <button class="xc-btn xc-btn--ghost" type="button" data-test="retry-power-trend" @click="$emit('retry')">重试</button>
    </div>
    <div v-else-if="isEmpty" class="tl-power-trend__state">该线路在所选日期范围内暂无功率数据</div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { formatNumber } from '@/utils/formatNumber'
import { getDefaultPowerRange, getRollingDateRange, isValidCustomPowerRange } from '@/store/modules/tieLine'
import { useEcharts, xcVar } from '@/views/home/composables/useEcharts'

const props = defineProps({
  trend: { type: Object, default: null },
  range: { type: Object, default: () => getDefaultPowerRange() },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  accentToken: { type: String, default: '--xc-chart-1' },
  ratedCapacityMw: { type: Number, default: null },
})
const emit = defineEmits(['range-change', 'retry'])

const presetRanges = [
  { key: 'yesterday', label: '昨日', days: 1 },
  { key: 'sevenDays', label: '7日', days: 7 },
  { key: 'thirtyDays', label: '30日', days: 30 },
  { key: 'ninetyDays', label: '90日', days: 90 },
]
const customVisible = ref(false)
const customStartDate = ref('')
const customEndDate = ref('')
const yesterday = () => getRollingDateRange(1).endDate
const isEmpty = computed(() => props.trend?.dataDateCount === 0)
const showChart = computed(() => Boolean(props.trend) && !props.loading && !props.error && !isEmpty.value)
const isCustomRangeValid = computed(() => isValidCustomPowerRange(customStartDate.value, customEndDate.value))
const rangeCaption = computed(() => {
  if (!props.trend) return '等待选择线路'
  const { startDate, endDate } = props.trend
  if (startDate === endDate) return `${startDate} · 单日功率`
  const dayCount = Math.round((new Date(`${endDate}T00:00:00`) - new Date(`${startDate}T00:00:00`)) / 86400000) + 1
  return `${startDate} 至 ${endDate} · 各时刻平均功率（${dayCount}日）`
})

function selectPreset(item) {
  emit('range-change', { key: item.key, ...getRollingDateRange(item.days) })
}
function openCustom() {
  customStartDate.value = props.range?.startDate || ''
  customEndDate.value = props.range?.endDate || ''
  customVisible.value = true
}
function confirmCustom() {
  if (!isCustomRangeValid.value) return
  emit('range-change', { key: 'custom', startDate: customStartDate.value, endDate: customEndDate.value })
  customVisible.value = false
}

const buildOption = () => {
  const points = props.trend?.points || []
  const values = points.map((point) => point.powerMw)
  const hasValues = values.some((value) => value !== null && value !== undefined)
  const accent = xcVar(props.accentToken) || xcVar('--xc-chart-1')
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (items) => {
        const item = items?.[0]
        if (!item) return ''
        return `${item.axisValue}<br/>功率：${formatNumber(item.data, 3)} MW`
      },
    },
    graphic: !hasValues ? [{
      type: 'text',
      left: 'center',
      top: 'middle',
      style: {
        text: '暂无实时功率数据\n数据源尚未接入',
        fill: xcVar('--xc-text-mute'),
        fontSize: 12,
        lineHeight: 20,
        align: 'center',
      },
    }] : [],
    grid: { left: 8, right: 12, top: 38, bottom: 12, containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: points.map((point) => point.time),
      axisLabel: { color: xcVar('--xc-text-mute'), fontSize: 10, interval: 11 },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: xcVar('--xc-border-soft') } },
    },
    yAxis: {
      type: 'value',
      name: 'MW',
      nameLocation: 'end',
      nameGap: 12,
      nameTextStyle: { color: xcVar('--xc-text-mute'), fontSize: 10, align: 'left' },
      axisLabel: { color: xcVar('--xc-text-mute'), fontSize: 10 },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: xcVar('--xc-border-soft') } },
    },
    series: [{
      name: '功率',
      type: 'line',
      smooth: false,
      showSymbol: false,
      connectNulls: false,
      lineStyle: { width: 2, color: accent },
      itemStyle: { color: accent },
      data: values,
      markLine: {
        symbol: 'none',
        silent: true,
        lineStyle: { color: xcVar('--xc-border-soft'), type: 'dashed', width: 1 },
        label: { color: xcVar('--xc-text-mute'), fontSize: 10 },
        data: [
          { yAxis: 0 },
          ...(props.ratedCapacityMw != null ? [{ yAxis: props.ratedCapacityMw, name: '额定容量' }] : []),
        ],
      },
    }],
  }
}
const { el } = useEcharts(buildOption)
</script>

<style scoped>
.tl-power-trend { margin-top: var(--xc-space-4); padding-top: var(--xc-space-3); border-top: 1px solid rgba(255, 255, 255, 0.08); }
.tl-power-trend__head { display: flex; align-items: start; justify-content: space-between; gap: var(--xc-space-3); }
.tl-power-trend__eyebrow { display: block; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.tl-power-trend__caption { display: block; margin-top: var(--xc-space-1); color: var(--xc-text-strong); font-size: var(--xc-fs-xs); font-weight: var(--xc-fw-semi); }
.tl-power-trend__ranges { display: grid; grid-template-columns: repeat(auto-fit, minmax(58px, 1fr)); gap: var(--xc-space-1); margin-top: var(--xc-space-2); }
.tl-power-trend__range { min-width: 0; padding: var(--xc-space-1); color: var(--xc-text-mute); background: rgba(255, 255, 255, 0.035); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: var(--xc-radius-xs); font-size: var(--xc-fs-2xs); cursor: pointer; }
.tl-power-trend__range--active { color: var(--xc-text-strong); border-color: rgba(232, 206, 139, 0.38); background: rgba(232, 206, 139, 0.09); }
.tl-power-trend__canvas { width: 100%; height: 188px; margin-top: var(--xc-space-2); }
.tl-power-trend__canvas--hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; opacity: 0; pointer-events: none; }
.tl-power-trend__skeleton, .tl-power-trend__state { display: grid; place-content: center; min-height: 188px; gap: var(--xc-space-3); color: var(--xc-text-mute); font-size: var(--xc-fs-xs); text-align: center; }
.tl-power-trend__skeleton .xc-skeleton { width: 100%; height: 128px; }
.tl-power-trend__custom-wrap { position: relative; min-width: 0; }
.tl-power-trend__custom-panel { position: absolute; top: calc(100% + 6px); right: 0; z-index: var(--xc-z-raised); display: grid; gap: 12px; width: min(300px, 78vw); margin-top: 0; padding: var(--xc-space-4); color: var(--xc-text-strong); background: var(--xc-surface-raised); border: 1px solid var(--xc-border-soft); border-radius: 6px; box-shadow: var(--xc-shadow-md); }
.tl-power-trend__custom-panel > strong { font-size: var(--xc-fs-xs); font-weight: var(--xc-fw-semi); }
.tl-power-trend__date-inputs { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); align-items: center; gap: 8px; color: var(--xc-text-mute); font-size: var(--xc-fs-xs); }
.tl-power-trend__date-inputs input { min-width: 0; height: 34px; padding: 0 10px; color: var(--xc-text-default); background: var(--xc-surface-control); border: 1px solid var(--xc-border-soft); border-radius: 6px; font: inherit; font-size: var(--xc-fs-xs); outline: 0; appearance: textfield; }
.tl-power-trend__date-inputs input:hover { border-color: var(--xc-border-strong); }
.tl-power-trend__date-inputs input:focus-visible { border-color: var(--xc-border-accent); box-shadow: 0 0 0 2px color-mix(in srgb, var(--xc-border-accent) 22%, transparent); }
.tl-power-trend__dialog-actions { display: flex; justify-content: flex-end; gap: 8px; }
.tl-power-trend__btn { height: 30px; padding: 0 12px; border: 1px solid var(--xc-border-soft); border-radius: 6px; background: var(--xc-surface-control); color: var(--xc-text-soft); font: inherit; font-size: var(--xc-fs-2xs); cursor: pointer; transition: border-color 160ms ease, background-color 160ms ease, color 160ms ease, opacity 160ms ease; }
.tl-power-trend__btn--ghost:hover:not(:disabled) { border-color: var(--xc-border-strong); background: var(--xc-surface-frosted); color: var(--xc-text-strong); }
.tl-power-trend__btn--primary { border-color: var(--xc-border-accent); background: color-mix(in srgb, var(--xc-border-accent) 14%, transparent); color: var(--xc-text-strong); }
.tl-power-trend__btn--primary:hover:not(:disabled) { background: color-mix(in srgb, var(--xc-border-accent) 20%, transparent); }
.tl-power-trend__btn:disabled { opacity: 0.35; cursor: default; }
</style>

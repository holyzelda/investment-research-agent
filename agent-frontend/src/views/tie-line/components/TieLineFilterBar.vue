<template>
  <div class="tl-filterbar" aria-label="联络线筛选工具栏">
    <div class="tl-filterbar__primary">
      <ElPopover
        v-model:visible="startRegionOpen"
        placement="bottom-start"
        trigger="click"
        :width="188"
        popper-class="tl-region-popper"
      >
        <template #reference>
          <button class="tl-filter-control tl-filter-control--select" :class="{ 'is-active': Boolean(startRegion) }" type="button" aria-label="筛选起点区域">
            <span class="tl-filter-control__label">起点</span>
            <span class="tl-filter-control__value">{{ regionLabel(startRegion) }}</span>
            <ChevronDown :size="14" class="tl-filter-control__chevron" aria-hidden="true" />
          </button>
        </template>
        <div class="tl-region-menu" role="listbox" aria-label="起点区域选项">
          <button class="tl-region-menu__option" :class="{ 'is-selected': !startRegion }" type="button" data-test="start-region-all" @click="selectStartRegion('')">全部地区</button>
          <button v-for="r in regionOptions" :key="`start-${r}`" class="tl-region-menu__option" :class="{ 'is-selected': startRegion === r }" type="button" :data-test="`start-region-${r}`" @click="selectStartRegion(r)">{{ r }}</button>
        </div>
      </ElPopover>

      <button
        class="tl-filterbar__swap"
        :class="{ 'is-spinning': swapAnimating }"
        type="button"
        aria-label="交换起点和终点区域"
        title="交换起点与终点"
        @click="handleSwap"
      >
        <ArrowLeftRight :size="16" aria-hidden="true" />
      </button>

      <ElPopover
        v-model:visible="endRegionOpen"
        placement="bottom-start"
        trigger="click"
        :width="188"
        popper-class="tl-region-popper"
      >
        <template #reference>
          <button class="tl-filter-control tl-filter-control--select" :class="{ 'is-active': Boolean(endRegion) }" type="button" aria-label="筛选终点区域">
            <span class="tl-filter-control__label">终点</span>
            <span class="tl-filter-control__value">{{ regionLabel(endRegion) }}</span>
            <ChevronDown :size="14" class="tl-filter-control__chevron" aria-hidden="true" />
          </button>
        </template>
        <div class="tl-region-menu" role="listbox" aria-label="终点区域选项">
          <button class="tl-region-menu__option" :class="{ 'is-selected': !endRegion }" type="button" data-test="end-region-all" @click="selectEndRegion('')">全部地区</button>
          <button v-for="r in regionOptions" :key="`end-${r}`" class="tl-region-menu__option" :class="{ 'is-selected': endRegion === r }" type="button" :data-test="`end-region-${r}`" @click="selectEndRegion(r)">{{ r }}</button>
        </div>
      </ElPopover>

      <ElPopover
        v-model:visible="capacityOpen"
        placement="bottom-start"
        trigger="click"
        :width="292"
        popper-class="tl-capacity-popper"
        @show="syncCapacityDraft"
      >
        <template #reference>
          <button
            class="tl-filter-control tl-filter-control--capacity"
            :class="{ 'is-active': hasCapacityFilter }"
            type="button"
            aria-label="筛选额定容量范围"
          >
            <span class="tl-filter-control__label">额定容量</span>
            <span class="tl-filter-control__value xc-num">{{ capacitySummary }}</span>
            <ChevronDown :size="14" class="tl-filter-control__chevron" aria-hidden="true" />
          </button>
        </template>

        <div class="tl-capacity-popover">
          <p class="tl-capacity-popover__title">额定容量范围（MW）</p>
          <div class="tl-capacity-popover__range xc-num">
            <input
              v-model="draftMinCapacity"
              class="tl-capacity-popover__input"
              type="number"
              min="0"
              step="1"
              inputmode="numeric"
              aria-label="额定容量下限（MW）"
              placeholder="最低容量"
            />
            <span class="tl-capacity-popover__dash">—</span>
            <input
              v-model="draftMaxCapacity"
              class="tl-capacity-popover__input"
              type="number"
              min="0"
              step="1"
              inputmode="numeric"
              aria-label="额定容量上限（MW）"
              placeholder="最高容量"
            />
          </div>

          <div class="tl-capacity-popover__presets" aria-label="常用容量范围">
            <span class="tl-capacity-popover__subtitle">常用范围</span>
            <div class="tl-capacity-popover__preset-row">
              <button class="tl-capacity-popover__preset" type="button" data-test="capacity-preset-low" @click="setCapacityDraft('', '2000')">≤ 2,000</button>
              <button class="tl-capacity-popover__preset" type="button" data-test="capacity-preset-mid" @click="setCapacityDraft('2000', '5000')">2,000-5,000</button>
              <button class="tl-capacity-popover__preset" type="button" data-test="capacity-preset-high" @click="setCapacityDraft('5000', '')">≥ 5,000</button>
            </div>
          </div>

          <div class="tl-capacity-popover__actions">
            <button class="tl-capacity-popover__btn tl-capacity-popover__btn--ghost" type="button" data-test="capacity-clear" @click="clearCapacity">清除</button>
            <button class="tl-capacity-popover__btn tl-capacity-popover__btn--primary" type="button" data-test="capacity-apply" @click="applyCapacity">确定</button>
          </div>
        </div>
      </ElPopover>
    </div>

    <div class="tl-filterbar__actions">
      <span class="tl-filterbar__result" aria-live="polite">{{ resultText }}</span>
      <button
        class="tl-filterbar__reset"
        type="button"
        :disabled="!hasActiveFilters"
        aria-label="重置筛选"
        title="重置筛选"
        @click="$emit('reset-filters')"
      >
        <RotateCcw :size="15" aria-hidden="true" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElPopover } from 'element-plus'
import { ArrowLeftRight, ChevronDown, RotateCcw } from '@lucide/vue'

const props = defineProps({
  startRegion: { type: String, default: '' },
  endRegion: { type: String, default: '' },
  minCapacityMw: { type: Number, default: null },
  maxCapacityMw: { type: Number, default: null },
  regionOptions: { type: Array, default: () => [] },
  visibleCount: { type: Number, default: 0 },
  totalCount: { type: Number, default: 0 },
})

const emit = defineEmits(['update:start-region', 'update:end-region', 'update:min-capacity-mw', 'update:max-capacity-mw', 'swap-regions', 'reset-filters'])

const capacityOpen = ref(false)
const startRegionOpen = ref(false)
const endRegionOpen = ref(false)
const draftMinCapacity = ref('')
const draftMaxCapacity = ref('')
const swapAnimating = ref(false)
let swapTimer = null

const hasCapacityFilter = computed(() => props.minCapacityMw !== null || props.maxCapacityMw !== null)
const hasActiveFilters = computed(() => Boolean(props.startRegion || props.endRegion || hasCapacityFilter.value))

const capacitySummary = computed(() => {
  const min = props.minCapacityMw
  const max = props.maxCapacityMw
  if (min === null && max === null) return '不限'
  if (min !== null && max !== null) return `${formatCapacity(min)}-${formatCapacity(max)} MW`
  if (max !== null) return `≤ ${formatCapacity(max)} MW`
  return `≥ ${formatCapacity(min)} MW`
})

const resultText = computed(() => {
  const total = props.totalCount
  const visible = props.visibleCount
  if (total > 0 && visible === 0) return '未找到符合条件的线路'
  if (hasActiveFilters.value) return `显示 ${visible} / ${total} 条线路`
  return `显示 ${total} 条线路`
})

watch(
  () => [props.minCapacityMw, props.maxCapacityMw],
  () => {
    if (!capacityOpen.value) syncCapacityDraft()
  },
)

function regionLabel(value) {
  return value || '全部地区'
}

function selectStartRegion(value) {
  emit('update:start-region', value)
  startRegionOpen.value = false
}

function selectEndRegion(value) {
  emit('update:end-region', value)
  endRegionOpen.value = false
}

function formatCapacity(value) {
  return Number(value).toLocaleString('zh-CN')
}

function syncCapacityDraft() {
  draftMinCapacity.value = props.minCapacityMw ?? ''
  draftMaxCapacity.value = props.maxCapacityMw ?? ''
}

function setCapacityDraft(min, max) {
  draftMinCapacity.value = min
  draftMaxCapacity.value = max
}

function applyCapacity() {
  emit('update:min-capacity-mw', String(draftMinCapacity.value ?? ''))
  emit('update:max-capacity-mw', String(draftMaxCapacity.value ?? ''))
  capacityOpen.value = false
}

function clearCapacity() {
  setCapacityDraft('', '')
  emit('update:min-capacity-mw', '')
  emit('update:max-capacity-mw', '')
  capacityOpen.value = false
}

function handleSwap() {
  emit('swap-regions')
  swapAnimating.value = false
  window.clearTimeout(swapTimer)
  requestAnimationFrame(() => {
    swapAnimating.value = true
    swapTimer = window.setTimeout(() => {
      swapAnimating.value = false
    }, 220)
  })
}
</script>

<style scoped>
.tl-filterbar {
  --tl-filter-border: var(--xc-border-soft);
  --tl-filter-border-hover: var(--xc-border-strong);
  --tl-filter-bg: rgba(255, 255, 255, 0.035);
  --tl-filter-bg-hover: rgba(255, 255, 255, 0.065);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 34px;
  padding: 0;
  box-sizing: border-box;
}

.tl-filterbar__primary {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: 6px;
  min-width: 0;
}

.tl-filterbar__actions {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  min-width: max-content;
  margin-left: auto;
}

.tl-filter-control {
  position: relative;
  display: inline-flex;
  align-items: center;
  height: 30px;
  min-width: 142px;
  padding: 0 9px;
  gap: 7px;
  border: 1px solid rgba(255, 255, 255, 0.075);
  border-radius: 6px;
  background: var(--tl-filter-bg);
  color: var(--xc-text-default);
  box-sizing: border-box;
  box-shadow: none;
  transition: border-color 160ms ease, box-shadow 160ms ease, background-color 160ms ease, transform 160ms ease;
}

.tl-filter-control:hover {
  border-color: var(--tl-filter-border-hover);
  background: var(--tl-filter-bg-hover);
}

.tl-filter-control.is-active {
  border-color: var(--xc-border-accent);
}

.tl-filter-control:focus-within,
.tl-filter-control:focus-visible {
  border-color: var(--xc-border-accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--xc-border-accent) 24%, transparent);
}

.tl-filter-control__label {
  flex: 0 0 auto;
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-2xs);
  line-height: 1;
  white-space: nowrap;
}

.tl-filter-control__select {
  min-width: 0;
  flex: 1 1 auto;
  width: 100%;
  height: 100%;
  padding: 0 18px 0 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--xc-text-strong);
  font: inherit;
  font-size: var(--xc-fs-xs);
  font-weight: var(--xc-fw-medium);
  appearance: none;
  cursor: pointer;
}

.tl-filter-control__chevron {
  position: absolute;
  right: 9px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--xc-text-mute);
  pointer-events: none;
}

.tl-filter-control--capacity {
  min-width: 172px;
  border-color: var(--tl-filter-border);
  cursor: pointer;
}

.tl-filter-control__value {
  min-width: 0;
  flex: 1 1 auto;
  padding-right: 16px;
  color: var(--xc-text-strong);
  font-size: var(--xc-fs-xs);
  font-weight: var(--xc-fw-medium);
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tl-filterbar__swap,
.tl-filterbar__reset {
  width: 30px;
  height: 30px;
  display: inline-grid;
  place-items: center;
  flex: 0 0 auto;
  border: 0;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--xc-text-mute);
  padding: 0;
  box-sizing: border-box;
  cursor: pointer;
  transition: background-color 160ms ease, color 160ms ease, opacity 160ms ease, transform 200ms ease;
}

.tl-filterbar__swap:hover,
.tl-filterbar__reset:not(:disabled):hover {
  border-color: rgba(232, 206, 139, 0.24);
  background: rgba(232, 206, 139, 0.055);
  color: var(--xc-text-strong);
}

.tl-filterbar__swap:focus-visible,
.tl-filterbar__reset:focus-visible {
  outline: 2px solid var(--xc-border-accent);
  outline-offset: 2px;
}

.tl-filterbar__swap.is-spinning svg {
  animation: tl-swap-spin 210ms ease;
}

.tl-filterbar__reset:not(:disabled) {
  color: var(--xc-text-secondary);
}

.tl-filterbar__reset:disabled {
  opacity: 0.35;
  cursor: default;
}

.tl-filterbar__result {
  color: rgba(232, 206, 139, 0.72);
  font-size: var(--xc-fs-2xs);
  line-height: 1;
  white-space: nowrap;
}

.tl-region-menu {
  display: grid;
  gap: 4px;
  max-height: 260px;
  overflow-y: auto;
  color: var(--xc-text-default);
}

.tl-region-menu__option {
  width: 100%;
  height: 30px;
  padding: 0 10px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--xc-text-soft);
  font: inherit;
  font-size: var(--xc-fs-xs);
  text-align: left;
  cursor: pointer;
  transition: border-color 160ms ease, background-color 160ms ease, color 160ms ease;
}

.tl-region-menu__option:hover,
.tl-region-menu__option.is-selected {
  border-color: var(--tl-filter-border-hover);
  background: var(--xc-surface-frosted);
  color: var(--xc-text-strong);
}

.tl-region-menu__option:focus-visible {
  outline: 2px solid var(--xc-border-accent);
  outline-offset: 1px;
}

.tl-capacity-popover {
  display: grid;
  gap: 12px;
  color: var(--xc-text-strong);
}

.tl-capacity-popover__title,
.tl-capacity-popover__subtitle {
  margin: 0;
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-2xs);
  line-height: var(--xc-lh-normal);
}

.tl-capacity-popover__range {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 8px;
}

.tl-capacity-popover__input {
  width: 100%;
  height: 34px;
  min-width: 0;
  padding: 0 10px;
  border: 1px solid var(--tl-filter-border);
  border-radius: 6px;
  outline: 0;
  background: var(--xc-surface-control);
  color: var(--xc-text-default);
  font: inherit;
  font-size: var(--xc-fs-xs);
  box-sizing: border-box;
  appearance: textfield;
}

.tl-capacity-popover__input::-webkit-outer-spin-button,
.tl-capacity-popover__input::-webkit-inner-spin-button {
  margin: 0;
  appearance: none;
}

.tl-capacity-popover__input:hover {
  border-color: var(--tl-filter-border-hover);
}

.tl-capacity-popover__input:focus-visible {
  border-color: var(--xc-border-accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--xc-border-accent) 22%, transparent);
}

.tl-capacity-popover__dash {
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-xs);
}

.tl-capacity-popover__presets {
  display: grid;
  gap: 6px;
}

.tl-capacity-popover__preset-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tl-capacity-popover__preset,
.tl-capacity-popover__btn {
  height: 30px;
  border: 1px solid var(--tl-filter-border);
  border-radius: 6px;
  background: var(--xc-surface-control);
  color: var(--xc-text-soft);
  font: inherit;
  font-size: var(--xc-fs-2xs);
  cursor: pointer;
  transition: border-color 160ms ease, background-color 160ms ease, color 160ms ease;
}

.tl-capacity-popover__preset {
  padding: 0 9px;
}

.tl-capacity-popover__preset:hover,
.tl-capacity-popover__btn--ghost:hover {
  border-color: var(--tl-filter-border-hover);
  background: var(--xc-surface-frosted);
  color: var(--xc-text-strong);
}

.tl-capacity-popover__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.tl-capacity-popover__btn {
  padding: 0 12px;
}

.tl-capacity-popover__btn--primary {
  border-color: var(--xc-border-accent);
  background: color-mix(in srgb, var(--xc-border-accent) 14%, transparent);
  color: var(--xc-text-strong);
}

.tl-capacity-popover__btn--primary:hover {
  background: color-mix(in srgb, var(--xc-border-accent) 20%, transparent);
}

@keyframes tl-swap-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(180deg); }
}

@media (max-width: 1180px) {
  .tl-filterbar { align-items: flex-start; flex-wrap: wrap; }
  .tl-filterbar__primary { flex-wrap: wrap; }
  .tl-filterbar__actions {
    width: 100%;
    margin-left: 0;
  }
}
</style>

<style>
.tl-region-popper.el-popper,
.tl-capacity-popper.el-popper {
  border: 1px solid var(--xc-border-soft);
  border-radius: 8px;
  background: var(--xc-surface-raised);
  box-shadow: var(--xc-shadow-md);
  box-sizing: border-box;
}
</style>

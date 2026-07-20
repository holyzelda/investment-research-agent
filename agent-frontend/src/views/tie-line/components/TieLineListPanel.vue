<template>
  <section v-if="open" class="tl-line-list" aria-label="线路列表面板">
    <header class="tl-line-list__head">
      <span>线路列表</span>
      <span class="xc-num">{{ lines.length }}</span>
    </header>
    <div v-if="!lines.length" class="tl-line-list__empty">当前筛选条件下暂无线路</div>
    <div
      v-else
      ref="listbox"
      class="tl-line-list__items"
      role="listbox"
      aria-label="联络线列表"
      @keydown="onKeydown"
    >
      <button
        v-for="(line, index) in lines"
        :key="line.id"
        :ref="(element) => setItemRef(element, index)"
        type="button"
        role="option"
        class="tl-line-list__item"
        :class="{ 'is-selected': line.id === selectedId }"
        :aria-selected="line.id === selectedId"
        :tabindex="index === focusIndex ? 0 : -1"
        @click="select(index)"
      >
        <span class="tl-line-list__name">{{ line.name || '未命名联络线' }}</span>
        <span class="tl-line-list__route">{{ line.startPoint || '—' }} → {{ line.endPoint || '—' }}</span>
        <span class="tl-line-list__meta">
          <i :style="{ background: `var(${tokenByText[line.voltageText] || '--xc-map-voltage-unknown'})` }" aria-hidden="true" />
          <span>{{ line.lengthText || '—' }}</span>
        </span>
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { buildVoltagePresentation } from '../voltagePresentation'

const props = defineProps({
  open: { type: Boolean, default: false },
  lines: { type: Array, default: () => [] },
  selectedId: { type: [Number, String], default: null },
  voltageOptions: { type: Array, default: () => [] },
})
const emit = defineEmits(['select', 'close'])

const listbox = ref(null)
const itemRefs = ref([])
const focusIndex = ref(0)
const tokenByText = computed(() => buildVoltagePresentation(props.voltageOptions).tokenByText)

function setItemRef(element, index) {
  if (element) itemRefs.value[index] = element
}
function syncFocusIndex() {
  const selectedIndex = props.lines.findIndex((line) => line.id === props.selectedId)
  focusIndex.value = selectedIndex >= 0 ? selectedIndex : 0
}
function focusCurrent() {
  nextTick(() => itemRefs.value[focusIndex.value]?.focus())
}
function select(index) {
  const line = props.lines[index]
  if (line) emit('select', line.id)
}
function moveFocus(index) {
  if (!props.lines.length) return
  focusIndex.value = (index + props.lines.length) % props.lines.length
  focusCurrent()
}
function onKeydown(event) {
  if (!props.lines.length) return
  if (event.key === 'ArrowDown') { event.preventDefault(); moveFocus(focusIndex.value + 1) }
  else if (event.key === 'ArrowUp') { event.preventDefault(); moveFocus(focusIndex.value - 1) }
  else if (event.key === 'Home') { event.preventDefault(); moveFocus(0) }
  else if (event.key === 'End') { event.preventDefault(); moveFocus(props.lines.length - 1) }
  else if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); select(focusIndex.value) }
  else if (event.key === 'Escape') { event.preventDefault(); emit('close') }
}

watch(() => [props.open, props.lines, props.selectedId], () => {
  if (!props.open) return
  itemRefs.value = []
  syncFocusIndex()
  focusCurrent()
}, { deep: true, immediate: true })
</script>

<style scoped>
.tl-line-list {
  width: min(320px, calc(100% - 32px));
  max-height: min(60%, 520px);
  display: flex;
  flex-direction: column;
  border: 1px solid var(--xc-map-legend-border);
  border-radius: var(--xc-radius-md, 10px);
  background: var(--xc-map-legend-bg);
  box-shadow: var(--xc-shadow-lg);
  overflow: hidden;
}
.tl-line-list__head { display: flex; justify-content: space-between; padding: 10px 12px; color: var(--xc-text-strong); font-size: var(--xc-fs-xs, 13px); border-bottom: 1px solid var(--xc-map-legend-border); }
.tl-line-list__items { overflow-y: auto; padding: 6px; }
.tl-line-list__item { width: 100%; display: grid; gap: 3px; padding: 9px 10px; text-align: left; border: 1px solid transparent; border-radius: var(--xc-radius-sm, 6px); background: transparent; color: var(--xc-text-soft); cursor: pointer; }
.tl-line-list__item:hover, .tl-line-list__item.is-selected { background: var(--xc-surface-frosted); border-color: var(--xc-border-accent); }
.tl-line-list__item:focus-visible { outline: 2px solid var(--xc-accent-blue); outline-offset: 1px; }
.tl-line-list__name { color: var(--xc-text-strong); font-size: var(--xc-fs-sm, 14px); }
.tl-line-list__route, .tl-line-list__meta { font-size: var(--xc-fs-2xs, 12px); color: var(--xc-text-mute); }
.tl-line-list__meta { display: inline-flex; align-items: center; gap: 6px; }
.tl-line-list__meta i { width: 14px; height: 3px; border-radius: 2px; }
.tl-line-list__empty { padding: var(--xc-space-4, 16px); color: var(--xc-text-mute); font-size: var(--xc-fs-xs, 13px); }
</style>

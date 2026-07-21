<template>
  <div class="tl-stats" aria-label="联络线统计">
    <div v-for="item in cards" :key="item.key" class="xc-kpi tl-stats__item">
      <span class="tl-stats__label">{{ item.label }}</span>
      <strong class="xc-num tl-stats__value">{{ item.value }}</strong>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stats: { type: Object, default: null },
})

const cards = computed(() => {
  const s = props.stats || {}
  return [
    { key: 'line', label: '联络线', value: s.lineCount ?? '—' },
    { key: 'region', label: '覆盖区域', value: s.regionCount ?? '—' },
    { key: 'voltage', label: '电压等级', value: s.voltageLevelCount ?? '—' },
    {
      key: 'cap',
      label: '额定容量合计',
      value: s.totalCapacityMw ? `${Number(s.totalCapacityMw).toLocaleString('zh-CN')} MW` : '—',
    },
  ]
})
</script>

<style scoped>
.tl-stats { display: grid; grid-template-columns: repeat(4, max-content); gap: var(--xc-space-5); }
.tl-stats__item { display: grid; gap: var(--xc-space-1); min-width: 72px; }
.tl-stats__label { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.tl-stats__value { color: var(--xc-text-strong); font-size: var(--xc-fs-kpi-sm); font-weight: var(--xc-fw-semi); line-height: var(--xc-lh-tight); white-space: nowrap; }
</style>

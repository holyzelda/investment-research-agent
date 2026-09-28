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
.tl-stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--xc-space-4); width: var(--tl-detail-width, 100%); min-width: 0; }
.tl-stats__item { position: relative; display: grid; gap: var(--xc-space-1); min-width: 88px; padding: 0; }
.tl-stats__item + .tl-stats__item::before { content: ''; position: absolute; left: calc(var(--xc-space-3) * -1); top: 4px; bottom: 4px; width: 1px; background: rgba(232, 206, 139, 0.18); }
.tl-stats__label { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.tl-stats__value { color: var(--xc-text-strong); font-size: var(--xc-fs-kpi-sm); font-weight: var(--xc-fw-semi); line-height: var(--xc-lh-tight); white-space: nowrap; text-shadow: 0 0 20px rgba(88, 214, 207, 0.18); }
</style>

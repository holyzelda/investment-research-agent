<template>
  <div class="tl-stats">
    <div v-for="item in cards" :key="item.key" class="tl-stats__card">
      <span class="tl-stats__value">{{ item.value }}</span>
      <span class="tl-stats__label">{{ item.label }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

// 顶部统计条。原型图的「最高/最低 MW、有数据条数」依赖功率时序，底表无此数据，
// 首版用静态数据能算的指标替换：联络线数 / 覆盖区域 / 电压档 / 额定容量合计。
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
.tl-stats {
  display: flex;
  gap: var(--xc-space-6, 24px);
  align-items: baseline;
}
.tl-stats__card {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.tl-stats__value {
  font-size: var(--xc-fs-h3, 20px);
  font-weight: var(--xc-fw-semi, 600);
  color: var(--xc-text-strong);
}
.tl-stats__label {
  font-size: var(--xc-fs-2xs, 12px);
  color: var(--xc-text-mute);
}
</style>

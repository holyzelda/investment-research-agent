<template>
  <div class="tl-legend">
    <div class="tl-legend__title">电压等级</div>
    <ul v-if="items.length" class="tl-legend__list">
      <li v-for="v in items" :key="v.text" class="tl-legend__item">
        <span class="tl-legend__swatch" :style="{ background: v.color }"></span>
        <span class="tl-legend__text">{{ v.text }}</span>
      </li>
    </ul>
    <p v-else class="tl-legend__empty">暂无数据</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

// 图例：电压等级 → 颜色（颜色映射由页面统一生成并下发，保证与地图一致）
const props = defineProps({
  voltageColors: { type: Object, default: () => ({}) },
})
const items = computed(() =>
  Object.entries(props.voltageColors).map(([text, color]) => ({ text, color })),
)
</script>

<style scoped>
.tl-legend {
  background: var(--xc-surface-glass);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-md, 10px);
  padding: 10px 14px;
  min-width: 120px;
}
.tl-legend__title {
  font-size: var(--xc-fs-2xs, 12px);
  color: var(--xc-text-mute);
  margin-bottom: 8px;
}
.tl-legend__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.tl-legend__item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.tl-legend__swatch {
  width: 18px;
  height: 4px;
  border-radius: 2px;
  flex: 0 0 auto;
}
.tl-legend__text {
  font-size: var(--xc-fs-xs, 13px);
  color: var(--xc-text-soft);
}
.tl-legend__empty {
  font-size: var(--xc-fs-2xs, 12px);
  color: var(--xc-text-mute);
  margin: 0;
}
</style>

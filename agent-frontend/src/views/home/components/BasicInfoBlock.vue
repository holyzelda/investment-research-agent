<template>
  <section class="ir-block">
    <h4 class="ir-block__title">
      <svg class="ir-block__title-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
        <path d="M4 20V9l8-5 8 5v11" stroke-linejoin="round" />
        <path d="M9 20v-6h6v6M8 10h.01M16 10h.01" stroke-linecap="round" />
      </svg>
      项目基础边界条件
    </h4>
    <!-- 一行 5 项裸排数值（无卡片边框/背景）：装机功率/装机容量/充电成本/放电返还/损耗费用。
         省份、节点不在此展示——省份由横幅标题体现，节点仅在参数区修改。
         装机功率/装机容量为规模量，数值上品牌紫；电价类保持白色。 -->
    <div class="ir-basic">
      <div v-for="metric in metrics" :key="metric.key" class="ir-basic__stat">
        <span class="ir-basic__k">
          <svg class="ir-basic__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true" v-html="metric.icon" />
          {{ metric.label }}
        </span>
        <span class="ir-basic__v xc-num" :class="{ 'ir-basic__v--accent': metric.accent }">
          {{ metric.text }}<span v-if="metric.unit" class="ir-basic__unit">{{ metric.unit }}</span>
        </span>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { formatNumber, formatPrice } from '@/utils/formatNumber'

const props = defineProps({ basicInfo: { type: Object, default: () => ({}) } })
const b = computed(() => props.basicInfo || {})

const priceText = (value) => (
  value === null || value === undefined ? '待完善' : formatPrice(value)
)

// 各项小图标（inline svg path 片段，随 currentColor 变蓝）
const ICON_POWER = '<path d="M13 2 4 14h7l-1 8 9-12h-7z" stroke-linejoin="round" stroke-linecap="round"/>'
const ICON_CAPACITY = '<rect x="4" y="7" width="14" height="10" rx="2"/><path d="M20 10v4" stroke-linecap="round"/>'
const ICON_CHARGE = '<path d="M12 3v6m0 0 3-3m-3 3L9 6" stroke-linecap="round" stroke-linejoin="round"/><rect x="5" y="11" width="14" height="10" rx="2"/>'
const ICON_DISCHARGE = '<path d="M12 21v-6m0 0 3 3m-3-3-3 3" stroke-linecap="round" stroke-linejoin="round"/><rect x="5" y="3" width="14" height="10" rx="2"/>'
const ICON_LOSS = '<circle cx="12" cy="12" r="9"/><path d="M8 12h8" stroke-linecap="round"/>'

const metrics = computed(() => [
  { key: 'powerMw', label: '装机功率', text: formatNumber(b.value.powerMw), unit: 'MW', accent: true, icon: ICON_POWER },
  { key: 'capacityMwh', label: '装机容量', text: formatNumber(b.value.capacityMwh), unit: 'MWh', accent: true, icon: ICON_CAPACITY },
  { key: 'chargeCost', label: '充电成本', text: priceText(b.value.chargeCost), unit: '元/kWh', accent: false, icon: ICON_CHARGE },
  { key: 'dischargeReturn', label: '放电返还', text: priceText(b.value.dischargeReturn), unit: '元/kWh', accent: false, icon: ICON_DISCHARGE },
  { key: 'lossCost', label: '损耗费用', text: priceText(b.value.lossCost), unit: '元/kWh', accent: false, icon: ICON_LOSS },
])
</script>

<style scoped>
.ir-block {
  padding: var(--xc-space-7);
}
.ir-block__title {
  display: flex;
  align-items: center;
  gap: var(--xc-space-2);
  font-size: var(--xc-fs-md);
  color: var(--xc-text-strong);
  font-weight: var(--xc-fw-semi);
  margin: 0 0 var(--xc-space-5);
}
.ir-block__title-icon {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
  color: var(--xc-accent-blue);
}
/* 一行 5 项裸排数值：无边框、无背景，仅靠列宽均分 */
.ir-basic {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--xc-space-5);
}
.ir-basic__stat {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--xc-space-3);
}
.ir-basic__k {
  display: inline-flex;
  align-items: center;
  gap: var(--xc-space-2);
  font-size: var(--xc-fs-xs);
  color: var(--xc-text-mute);
}
.ir-basic__icon {
  width: 14px;
  height: 14px;
  flex: 0 0 auto;
  color: var(--xc-accent-blue);
}
.ir-basic__v {
  font-size: var(--xc-fs-kpi-md);
  font-weight: var(--xc-fw-bold);
  color: var(--xc-text-strong);
  line-height: var(--xc-lh-tight);
  white-space: nowrap;
}
/* 装机功率/装机容量：品牌紫强调 */
.ir-basic__v--accent { color: var(--xc-brand-violet-2); }
.ir-basic__unit {
  font-size: var(--xc-fs-2xs);
  color: var(--xc-text-mute);
  margin-left: 3px;
}
@container (max-width: 980px) {
  .ir-basic { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@container (max-width: 560px) {
  .ir-basic { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@container (max-width: 480px) {
  .ir-block { padding: var(--xc-space-5); }
  .ir-basic { gap: var(--xc-space-5) var(--xc-space-4); }
  .ir-basic__v { font-size: var(--xc-fs-kpi-sm); }
}
</style>

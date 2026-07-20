<template>
  <section class="ir-block">
    <h4 class="ir-block__title">
      <svg class="ir-block__title-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
        <path d="M4 20V9l8-5 8 5v11" stroke-linejoin="round" />
        <path d="M9 20v-6h6v6M8 10h.01M16 10h.01" stroke-linecap="round" />
      </svg>
      项目基础边界条件
    </h4>
    <div class="ir-basic-card">
      <div class="ir-basic__row" :class="hasNode ? 'ir-basic__row--4' : 'ir-basic__row--3'">
        <div class="ir-basic__item">
          <span class="ir-basic__k">省份</span>
          <span class="ir-basic__v">{{ b.province || '—' }}</span>
        </div>
        <div v-if="hasNode" class="ir-basic__item">
          <span class="ir-basic__k">节点</span>
          <span class="ir-basic__v">{{ b.nodeName }}</span>
        </div>
        <div class="ir-basic__item">
          <span class="ir-basic__k">装机功率</span>
          <span class="ir-basic__v xc-num">{{ formatNumber(b.powerMw) }} MW</span>
        </div>
        <div class="ir-basic__item">
          <span class="ir-basic__k">装机容量</span>
          <span class="ir-basic__v xc-num">{{ formatNumber(b.capacityMwh) }} MWh</span>
        </div>
      </div>

      <div class="ir-basic__divider" />

      <div class="ir-basic__row ir-basic__row--3">
        <div class="ir-basic__item">
          <span class="ir-basic__k">充电成本</span>
          <span class="ir-basic__v xc-num">{{ formatPriceUnit(b.chargeCost) }}</span>
        </div>
        <div class="ir-basic__item">
          <span class="ir-basic__k">放电返还</span>
          <span class="ir-basic__v xc-num">{{ formatPriceUnit(b.dischargeReturn) }}</span>
        </div>
        <div class="ir-basic__item">
          <span class="ir-basic__k">损耗费用</span>
          <span class="ir-basic__v xc-num">{{ formatPriceUnit(b.lossCost) }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { formatNumber, formatPrice } from '@/utils/formatNumber'

const props = defineProps({ basicInfo: { type: Object, default: () => ({}) } })
const b = props.basicInfo
const hasNode = computed(() => !!b.nodeName)
const formatPriceUnit = (value) => (
  value === null || value === undefined ? '待完善' : `${formatPrice(value)} 元/kWh`
)
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
/* 卡片化：与②财务指标/进阶图形卡片保持一致的玻璃卡片处理，而非裸文字排布 */
.ir-basic-card {
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-md);
  background: var(--xc-surface-control);
  padding: var(--xc-space-6);
}
.ir-basic__row {
  display: grid;
  gap: var(--xc-space-4) var(--xc-space-7);
}
/* 省份/节点/装机功率/装机容量一行；无节点时该行仅三项 */
.ir-basic__row--4 { grid-template-columns: repeat(4, 1fr); }
/* 充电成本/放电返还/损耗费用一行 */
.ir-basic__row--3 { grid-template-columns: repeat(3, 1fr); }
.ir-basic__divider {
  height: 1px;
  background: var(--xc-border-soft);
  margin: var(--xc-space-4) 0;
}
.ir-basic__item {
  display: flex;
  align-items: baseline;
  gap: var(--xc-space-3);
}
.ir-basic__k {
  font-size: var(--xc-fs-xs);
  color: var(--xc-text-mute);
  flex: 0 0 auto;
}
.ir-basic__v {
  font-size: var(--xc-fs-md);
  color: var(--xc-text-default);
}
@media (max-width: 760px) {
  .ir-basic__row--4,
  .ir-basic__row--3 { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 480px) {
  .ir-basic__row--4,
  .ir-basic__row--3 { grid-template-columns: 1fr; }
}
</style>

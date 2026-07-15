<template>
  <section class="ir-block">
    <h4 class="ir-block__title">① 基本信息</h4>
    <div class="ir-basic">
      <div class="ir-basic__item">
        <span class="ir-basic__k">省份</span>
        <span class="ir-basic__v">{{ b.province || '—' }}</span>
      </div>
      <div v-if="b.nodeName" class="ir-basic__item">
        <span class="ir-basic__k">节点</span>
        <span class="ir-basic__v">{{ b.nodeName }}</span>
      </div>
      <div class="ir-basic__item">
        <span class="ir-basic__k">功率</span>
        <span class="ir-basic__v xc-num">{{ formatNumber(b.powerMw) }} MW</span>
      </div>
      <div class="ir-basic__item">
        <span class="ir-basic__k">容量</span>
        <span class="ir-basic__v xc-num">{{ formatNumber(b.capacityMwh) }} MWh</span>
      </div>
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
  </section>
</template>

<script setup>
import { formatNumber, formatPrice } from '@/utils/formatNumber'

const props = defineProps({ basicInfo: { type: Object, default: () => ({}) } })
const b = props.basicInfo
const formatPriceUnit = (value) => (
  value === null || value === undefined ? '待完善' : `${formatPrice(value)} 元/kWh`
)
</script>

<style scoped>
.ir-block {
  padding: var(--xc-space-6);
}
.ir-block__title {
  font-size: var(--xc-fs-md);
  color: var(--xc-text-strong);
  font-weight: var(--xc-fw-semi);
  margin: 0 0 var(--xc-space-5);
}
.ir-basic {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: var(--xc-space-4) var(--xc-space-7);
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
</style>

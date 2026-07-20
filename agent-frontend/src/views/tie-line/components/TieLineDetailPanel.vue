<template>
  <aside class="tl-detail">
    <template v-if="displayLine">
      <header class="tl-detail__head">
        <h3 class="tl-detail__title" :style="{ color: `var(${accentToken})` }">{{ displayLine.name }}</h3>
        <span class="tl-detail__tag">跨省跨区</span>
      </header>

      <dl class="tl-detail__grid">
        <div class="tl-detail__row"><dt>起点</dt><dd>{{ displayLine.startPoint || '—' }}</dd></div>
        <div class="tl-detail__row"><dt>终点</dt><dd>{{ displayLine.endPoint || '—' }}</dd></div>
        <div class="tl-detail__row"><dt>起始区域</dt><dd>{{ regionText }}</dd></div>
        <div class="tl-detail__row"><dt>长度</dt><dd>{{ displayLine.lengthText || '—' }}</dd></div>
        <div class="tl-detail__row"><dt>电压</dt><dd>{{ displayLine.voltageText || '—' }}</dd></div>
        <div class="tl-detail__row"><dt>额定容量</dt><dd>{{ capText }}</dd></div>
        <div class="tl-detail__row"><dt>投运年份</dt><dd>{{ displayLine.operationYear || '—' }}</dd></div>
      </dl>

      <p v-if="noteText" class="tl-detail__note">{{ noteText }}</p>

      <!-- 功率趋势：依赖联络线功率时序数据，底表暂无，占位 -->
      <section class="tl-detail__trend">
        <div class="tl-detail__trend-title">功率趋势</div>
        <div class="tl-detail__trend-empty">
          需接入联络线功率时序数据后展示<br />（当前底表仅含线路静态信息）
        </div>
      </section>
    </template>

    <div v-else class="tl-detail__placeholder">
      {{ noVisibleLines ? '当前筛选条件下暂无线路' : '点击地图上的联络线查看线路详情' }}
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  line: { type: Object, default: null },
  recommendedLine: { type: Object, default: null },
  noVisibleLines: { type: Boolean, default: false },
  accentToken: { type: String, default: '--xc-map-voltage-unknown' },
})

const displayLine = computed(() => props.line || props.recommendedLine)

const regionText = computed(() =>
  displayLine.value ? `${displayLine.value.startRegion || '—'} → ${displayLine.value.endRegion || '—'}` : '—',
)
const capText = computed(() =>
  displayLine.value && displayLine.value.ratedCapacityMw != null
    ? `${Number(displayLine.value.ratedCapacityMw).toLocaleString('zh-CN')} MW`
    : '—',
)
const noteText = computed(() => {
  if (!props.line) return ''
  return [props.line.coordinateBasis, props.line.dataBasisNote].filter(Boolean).join(' · ')
})
</script>

<style scoped>
.tl-detail {
  height: 100%;
  box-sizing: border-box;
  background: var(--xc-surface-1);
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-md, 10px);
  padding: var(--xc-space-4, 16px);
  overflow-y: auto;
}
.tl-detail__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--xc-space-2, 8px);
  margin-bottom: var(--xc-space-4, 16px);
}
.tl-detail__title {
  font-size: var(--xc-fs-h3, 18px);
  font-weight: var(--xc-fw-semi, 600);
  color: var(--xc-text-strong);
  margin: 0;
}
.tl-detail__tag {
  font-size: var(--xc-fs-2xs, 12px);
  color: var(--xc-accent-blue);
  border: 1px solid var(--xc-border-accent);
  border-radius: var(--xc-radius-sm, 6px);
  padding: 1px 8px;
  flex: 0 0 auto;
}
.tl-detail__grid {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.tl-detail__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--xc-space-3, 12px);
}
.tl-detail__row dt {
  font-size: var(--xc-fs-2xs, 12px);
  color: var(--xc-text-mute);
  flex: 0 0 auto;
}
.tl-detail__row dd {
  margin: 0;
  font-size: var(--xc-fs-sm, 14px);
  color: var(--xc-text-strong);
  text-align: right;
}
.tl-detail__note {
  margin: var(--xc-space-3, 12px) 0 0;
  font-size: var(--xc-fs-2xs, 12px);
  color: var(--xc-text-mute);
  line-height: 1.5;
}
.tl-detail__trend {
  margin-top: var(--xc-space-5, 20px);
  border-top: 1px solid var(--xc-border-soft);
  padding-top: var(--xc-space-4, 16px);
}
.tl-detail__trend-title {
  font-size: var(--xc-fs-2xs, 12px);
  color: var(--xc-text-mute);
  margin-bottom: 10px;
}
.tl-detail__trend-empty {
  height: 120px;
  display: grid;
  place-items: center;
  text-align: center;
  font-size: var(--xc-fs-2xs, 12px);
  color: var(--xc-text-mute);
  line-height: 1.6;
  background: var(--xc-surface-2);
  border-radius: var(--xc-radius-sm, 6px);
}
.tl-detail__placeholder {
  height: 100%;
  display: grid;
  place-items: center;
  text-align: center;
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-sm, 14px);
}
</style>

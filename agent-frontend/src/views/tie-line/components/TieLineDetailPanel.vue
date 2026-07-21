<template>
  <aside class="tl-detail">
    <template v-if="displayLine">
      <header class="tl-detail__head">
        <div>
          <span class="tl-detail__eyebrow">线路档案</span>
          <h3 class="tl-detail__title" :style="{ color: `var(${accentToken})` }">{{ displayLine.name }}</h3>
        </div>
        <span class="tl-detail__tag">{{ displayLine.voltageText || '电压未知' }}</span>
      </header>

      <div class="tl-detail__route" aria-label="线路起讫路径">
        <span>{{ displayLine.startPoint || '—' }}</span>
        <span class="tl-detail__route-arrow" aria-hidden="true">→</span>
        <span>{{ displayLine.endPoint || '—' }}</span>
      </div>

      <dl class="tl-detail__metrics">
        <div class="tl-detail__metric"><dt>起始区域</dt><dd>{{ regionText }}</dd></div>
        <div class="tl-detail__metric"><dt>线路长度</dt><dd class="xc-num">{{ displayLine.lengthText || '—' }}</dd></div>
        <div class="tl-detail__metric"><dt>电压等级</dt><dd>{{ displayLine.voltageText || '—' }}</dd></div>
        <div class="tl-detail__metric"><dt>额定容量</dt><dd class="tl-detail__metric-value xc-num">{{ capText }}</dd></div>
        <div class="tl-detail__metric"><dt>投运年份</dt><dd class="xc-num">{{ displayLine.operationYear || '—' }}</dd></div>
      </dl>

      <p v-if="noteText" class="tl-detail__note">{{ noteText }}</p>

      <section class="tl-detail__data-state" aria-label="功率时序数据状态">
        <span class="tl-detail__data-state-label">功率趋势</span>
        <strong>功率时序数据未接入</strong>
        <p>当前仅展示线路静态资料，接入可追溯功率时序后展示趋势。</p>
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
  padding: var(--xc-space-5);
  overflow-y: auto;
  background: var(--xc-surface-1);
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-md);
}
.tl-detail__head { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--xc-space-3); }
.tl-detail__eyebrow,
.tl-detail__data-state-label { display: block; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.tl-detail__title { margin: var(--xc-space-1) 0 0; font-size: var(--xc-fs-h3); font-weight: var(--xc-fw-semi); line-height: var(--xc-lh-snug); }
.tl-detail__tag { flex: 0 0 auto; padding: var(--xc-space-1) var(--xc-space-2); color: var(--xc-text-soft); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-xs); font-size: var(--xc-fs-2xs); }
.tl-detail__route { display: flex; align-items: center; gap: var(--xc-space-2); margin-top: var(--xc-space-4); padding: var(--xc-space-3); color: var(--xc-text-strong); background: var(--xc-surface-tinted); border-radius: var(--xc-radius-sm); font-size: var(--xc-fs-sm); }
.tl-detail__route-arrow { color: var(--xc-accent-blue); }
.tl-detail__metrics { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--xc-space-2); margin: var(--xc-space-3) 0 0; }
.tl-detail__metric { min-width: 0; padding: var(--xc-space-3); background: var(--xc-surface-tinted); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); }
.tl-detail__metric dt { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.tl-detail__metric dd { margin: var(--xc-space-1) 0 0; overflow: hidden; color: var(--xc-text-strong); font-size: var(--xc-fs-sm); text-overflow: ellipsis; white-space: nowrap; }
.tl-detail__note { margin: var(--xc-space-3) 0 0; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); line-height: var(--xc-lh-normal); }
.tl-detail__data-state { margin-top: var(--xc-space-5); padding: var(--xc-space-4); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); background: var(--xc-surface-frosted); }
.tl-detail__data-state strong { display: block; margin-top: var(--xc-space-2); color: var(--xc-text-soft); font-size: var(--xc-fs-sm); }
.tl-detail__data-state p { margin: var(--xc-space-2) 0 0; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); line-height: var(--xc-lh-normal); }
.tl-detail__placeholder { height: 100%; display: grid; place-items: center; color: var(--xc-text-mute); font-size: var(--xc-fs-sm); text-align: center; }
</style>

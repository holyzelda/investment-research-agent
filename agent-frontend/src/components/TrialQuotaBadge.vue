<template>
  <div
    v-if="isTrial"
    class="ir-trial-badge"
    :class="{ 'is-exhausted': exhausted, 'ir-trial-badge--compact': collapsed }"
    :data-tip="collapsed ? summaryText : undefined"
    :tabindex="collapsed ? 0 : undefined"
    :aria-label="collapsed ? summaryText : undefined"
    role="note"
  >
    <template v-if="collapsed">
      <span class="ir-trial-badge__dot" aria-hidden="true" />
      <span class="ir-trial-badge__mini-track" aria-hidden="true">
        <span class="ir-trial-badge__mini-fill" :style="{ width: `${percent}%` }" />
      </span>
    </template>
    <template v-else>
      <div class="ir-trial-badge__head">
        <span class="ir-trial-badge__tag">
          <i class="ir-trial-badge__dot" aria-hidden="true" />
          试用版
        </span>
        <span class="ir-trial-badge__cycle">{{ exhausted ? '今日已用完' : '每日重置' }}</span>
      </div>
      <div v-if="!exhausted" class="ir-trial-badge__stats">
        <span class="ir-trial-badge__stat">
          <span>测算</span><b class="xc-num">{{ remaining('calculation') }}</b>/{{ limit('calculation') }}
        </span>
        <span class="ir-trial-badge__stat">
          <span>报告</span><b class="xc-num">{{ remaining('report') }}</b>/{{ limit('report') }}
        </span>
        <span class="ir-trial-badge__stat">
          <span>咨询</span><b class="xc-num">{{ remaining('consultation') }}</b>/{{ limit('consultation') }}
        </span>
      </div>
      <p v-else class="ir-trial-badge__done">今日额度已用完，明日恢复</p>
      <div class="ir-trial-badge__track" aria-hidden="true">
        <span class="ir-trial-badge__fill" :style="{ width: `${percent}%` }" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  quota: { type: Object, default: null },
  collapsed: { type: Boolean, default: false },
})

const quota = computed(() => props.quota || {})
const isTrial = computed(() => quota.value.isTrial === true)

const counter = (key) => quota.value[key] || {}
const remaining = (key) => Number(counter(key).remaining ?? 0)
const used = (key) => Number(counter(key).used ?? 0)
const limit = (key) => {
  const value = Number(counter(key).limit)
  return value > 0 ? value : Math.max(0, used(key) + remaining(key))
}

const exhausted = computed(() => (
  remaining('calculation') + remaining('report') + remaining('consultation') === 0
))

const percent = computed(() => {
  const totalLimit = limit('calculation') + limit('report') + limit('consultation')
  if (totalLimit <= 0) return 0
  const totalUsed = used('calculation') + used('report') + used('consultation')
  return Math.min(100, Math.round((totalUsed / totalLimit) * 100))
})

const summaryText = computed(() => {
  if (exhausted.value) return '试用版 · 今日额度已用完'
  return [
    `试用版`,
    `测算${remaining('calculation')}/${limit('calculation')}`,
    `报告${remaining('report')}/${limit('report')}`,
    `咨询${remaining('consultation')}/${limit('consultation')}`,
  ].join(' · ')
})
</script>

<style scoped>
.ir-trial-badge {
  margin: 12px var(--xc-space-1) 0;
  padding: 10px 12px 9px;
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-sm);
  background:
    linear-gradient(135deg, rgba(34, 177, 253, 0.08) 0%, rgba(110, 42, 255, 0.05) 100%),
    var(--xc-surface-frosted);
  color: var(--xc-text-soft);
}

.ir-trial-badge__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.ir-trial-badge__tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--xc-text-strong);
  font-size: var(--xc-fs-xs);
  font-weight: var(--xc-fw-semi);
  line-height: 1;
}

.ir-trial-badge__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--xc-grad-logo);
  box-shadow: 0 0 6px rgba(0, 240, 253, 0.55);
}

.ir-trial-badge__cycle {
  color: var(--xc-text-faint);
  font-size: var(--xc-fs-3xs);
  white-space: nowrap;
}

.ir-trial-badge__stats {
  margin-top: 8px;
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-size: var(--xc-fs-2xs);
  color: var(--xc-text-mute);
  white-space: nowrap;
  overflow: hidden;
}

.ir-trial-badge__stat b {
  margin: 0 1px 0 2px;
  color: var(--xc-accent-blue);
  font-size: var(--xc-fs-sm);
  font-weight: var(--xc-fw-bold);
}

.ir-trial-badge__track {
  margin-top: 8px;
  height: 3px;
  border-radius: var(--xc-radius-full);
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.ir-trial-badge__fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--xc-brand-cyan), var(--xc-accent-blue));
  transition: width var(--xc-dur-base) var(--xc-ease-out);
}

.ir-trial-badge.is-exhausted {
  border-color: rgba(255, 170, 0, 0.35);
  background:
    linear-gradient(135deg, rgba(255, 170, 0, 0.10), rgba(255, 170, 0, 0.04)),
    var(--xc-surface-frosted);
}

.ir-trial-badge.is-exhausted .ir-trial-badge__cycle {
  color: var(--xc-status-warn);
}

.ir-trial-badge__done {
  margin: 8px 0 0;
  color: var(--xc-status-warn);
  font-size: var(--xc-fs-2xs);
  line-height: var(--xc-lh-normal);
}

.ir-trial-badge.is-exhausted .ir-trial-badge__fill {
  background: var(--xc-status-warn);
}

/* 折叠态：紧凑状态徽标 */
.ir-trial-badge--compact {
  position: relative;
  width: 40px;
  height: 40px;
  margin: var(--xc-space-4) auto 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  border-color: rgba(34, 177, 253, 0.35);
  border-radius: var(--xc-radius-sm);
  cursor: help;
  flex: 0 0 auto;
}

.ir-trial-badge--compact .ir-trial-badge__dot {
  width: 10px;
  height: 10px;
  box-shadow: 0 0 10px rgba(0, 240, 253, 0.6), 0 0 2px rgba(0, 240, 253, 0.9);
}

.ir-trial-badge--compact .ir-trial-badge__mini-track {
  width: 22px;
  height: 3px;
  border-radius: var(--xc-radius-full);
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.ir-trial-badge--compact .ir-trial-badge__mini-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--xc-brand-cyan), var(--xc-accent-blue));
  transition: width var(--xc-dur-base) var(--xc-ease-out);
}

.ir-trial-badge--compact.is-exhausted {
  border-color: rgba(255, 170, 0, 0.35);
  background:
    linear-gradient(135deg, rgba(255, 170, 0, 0.10), rgba(255, 170, 0, 0.04)),
    var(--xc-surface-frosted);
}

.ir-trial-badge--compact.is-exhausted .ir-trial-badge__dot {
  background: var(--xc-status-warn);
  box-shadow: 0 0 10px rgba(255, 170, 0, 0.55);
}

.ir-trial-badge--compact.is-exhausted .ir-trial-badge__mini-fill {
  background: var(--xc-status-warn);
}

.ir-trial-badge--compact:focus-visible {
  outline: 2px solid var(--xc-accent-blue);
  outline-offset: 2px;
}

/* 折叠态 tooltip：在小卡组件内部实现，避免 scoped 选择器够不到子组件 */
.ir-trial-badge--compact::after {
  content: attr(data-tip);
  position: absolute;
  top: 50%;
  left: calc(100% + 10px);
  z-index: var(--xc-z-tooltip);
  padding: 5px 8px;
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-xs);
  background: var(--xc-surface-2);
  box-shadow: var(--xc-shadow-sm);
  color: var(--xc-text-strong);
  font-size: var(--xc-fs-2xs);
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transform: translateY(-50%);
  transition: opacity var(--xc-dur-fast);
}

.ir-trial-badge--compact:hover::after,
.ir-trial-badge--compact:focus-visible::after {
  opacity: 1;
}
</style>
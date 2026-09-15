<template>
  <div v-if="isTrial" class="ir-trial-notice" :class="{ 'is-alert': alert }" role="note" aria-live="polite">
    <template v-if="alert">
      <CircleAlert class="ir-trial-notice__icon" :size="15" aria-hidden="true" />
      <span class="ir-trial-notice__alert-text">{{ alertText }}</span>
    </template>
    <span v-else class="ir-trial-notice__text">
      今日试用额度 · 测算 {{ remaining('calculation') }}/{{ limit('calculation') }} · 报告 {{ remaining('report') }}/{{ limit('report') }} · 咨询 {{ remaining('consultation') }}/{{ limit('consultation') }} · 每日重置
    </span>
  </div>
</template>

<script>
// module 作用域常量：defineProps 的 validator 会被提升到 setup 之外，不能引用 setup 内局部变量
export const FEATURE_LABELS = {
  calculation: '测算',
  report: '报告生成',
  consultation: '政策咨询',
}
</script>

<script setup>
import { computed } from 'vue'
import { CircleAlert } from '@lucide/vue'

const props = defineProps({
  quota: { type: Object, default: null },
  feature: {
    type: String,
    default: 'calculation',
    validator: (value) => Object.prototype.hasOwnProperty.call(FEATURE_LABELS, value),
  },
})

const quota = computed(() => props.quota || {})
const isTrial = computed(() => quota.value.isTrial === true)

const counter = (key) => quota.value[key] || {}
const remaining = (key) => Number(counter(key).remaining ?? 0)
const limit = (key) => {
  const value = Number(counter(key).limit)
  return value > 0 ? value : Math.max(0, Number(counter(key).used ?? 0) + remaining(key))
}

const alert = computed(() => remaining(props.feature) === 0)
const alertText = computed(() => `今日${FEATURE_LABELS[props.feature]}额度已用完，明日 00:00 自动恢复`)
</script>

<style scoped>
.ir-trial-notice__text {
  display: block;
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-2xs);
  line-height: var(--xc-lh-normal);
  overflow-wrap: anywhere;
}

.ir-trial-notice.is-alert {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 14px;
  border: 1px solid rgba(255, 170, 0, 0.35);
  border-radius: var(--xc-radius-sm);
  background: var(--xc-status-warn-soft);
  color: #ffc966;
  font-size: var(--xc-fs-xs);
  line-height: var(--xc-lh-normal);
}

.ir-trial-notice__icon {
  flex: 0 0 auto;
  margin-top: 2px;
  color: currentColor;
}
</style>

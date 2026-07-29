<template>
  <component :is="tag" :class="['ir-report-heading', `ir-report-heading--${level}`]">
    {{ title }}
    <span v-if="level === 2" aria-hidden="true" />
  </component>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ title: { type: String, required: true }, level: { type: Number, default: 2 } })
const tag = computed(() => (props.level === 3 ? 'h4' : 'h3'))
</script>

<style scoped>
.ir-report-heading { color: var(--xc-text-strong); break-after: avoid; }
.ir-report-heading--2 { margin: 36px 0 24px; font-size: 18px; font-weight: var(--xc-fw-semi); line-height: 1.45; }
.ir-report-heading--2 span { display: block; width: 30px; height: 2px; margin-top: 10px; background: var(--xc-accent-blue); }
.ir-report-heading--3 { margin: 0 0 8px; color: var(--xc-text-soft); font-size: 13px; font-weight: var(--xc-fw-semi); }
</style>

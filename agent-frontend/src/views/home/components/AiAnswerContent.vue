<template>
  <div class="ir-ai-answer" :class="{ 'ir-ai-answer--error': error }">
    <div class="ir-ai-answer__text">{{ text || fallback }}</div>
    <div v-if="$slots.actions" class="ir-ai-answer__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  text: { type: String, default: '' },
  fallback: { type: String, default: '' },
  error: { type: Boolean, default: false },
})
</script>

<style scoped>
.ir-ai-answer {
  width: 100%;
  box-sizing: border-box;
  padding: var(--xc-space-6);
  border-radius: var(--xc-radius-lg);
  background: var(--xc-surface-card);
  color: var(--xc-text-default);
  font-size: var(--xc-fs-md);
  line-height: var(--xc-lh-loose);
}
.ir-ai-answer--error { color: var(--xc-status-danger); }
.ir-ai-answer__text { white-space: pre-wrap; overflow-wrap: anywhere; }
.ir-ai-answer__actions { display: flex; flex-wrap: wrap; gap: var(--xc-space-3); margin-top: var(--xc-space-4); }
.ir-ai-answer__actions :deep(button) {
  min-height: 30px;
  padding: var(--xc-space-1) var(--xc-space-4);
  border: 1px solid var(--xc-accent-blue);
  border-radius: var(--xc-radius-sm);
  background: transparent;
  color: var(--xc-accent-blue);
  font-size: var(--xc-fs-xs);
  cursor: pointer;
}
</style>

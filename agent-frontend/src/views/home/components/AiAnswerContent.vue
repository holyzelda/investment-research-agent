<template>
  <div class="ir-ai-answer" :class="{ 'ir-ai-answer--error': error }">
    <div class="ir-ai-answer__markdown" v-html="renderedText" />
    <div v-if="$slots.actions" class="ir-ai-answer__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'

const props = defineProps({
  text: { type: String, default: '' },
  fallback: { type: String, default: '' },
  error: { type: Boolean, default: false },
})

const markdown = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true,
})
const renderedText = computed(() => markdown.render(props.text || props.fallback || ''))
</script>

<style scoped>
.ir-ai-answer {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  padding: var(--xc-space-7);
  border-radius: var(--xc-radius-md);
  background: color-mix(in srgb, var(--xc-text-strong) 4%, transparent);
  color: var(--xc-text-default);
  font-size: var(--xc-fs-base);
  line-height: var(--xc-lh-loose);
}
.ir-ai-answer--error { color: var(--xc-status-danger); }
.ir-ai-answer__markdown { max-width: 100%; overflow-x: auto; overflow-wrap: anywhere; }
.ir-ai-answer__markdown :deep(> :first-child) { margin-top: 0; }
.ir-ai-answer__markdown :deep(> :last-child) { margin-bottom: 0; }
.ir-ai-answer__markdown :deep(p) { margin: 0 0 var(--xc-space-3); }
.ir-ai-answer__markdown :deep(h1),
.ir-ai-answer__markdown :deep(h2),
.ir-ai-answer__markdown :deep(h3),
.ir-ai-answer__markdown :deep(h4) {
  margin: var(--xc-space-6) 0 var(--xc-space-3);
  color: var(--xc-text-strong);
  font-weight: var(--xc-fw-semi);
  line-height: var(--xc-lh-snug);
}
.ir-ai-answer__markdown :deep(h1) { font-size: var(--xc-fs-lg); }
.ir-ai-answer__markdown :deep(h2) { font-size: var(--xc-fs-md); }
.ir-ai-answer__markdown :deep(h3),
.ir-ai-answer__markdown :deep(h4) { font-size: var(--xc-fs-sm); }
.ir-ai-answer__markdown :deep(ul),
.ir-ai-answer__markdown :deep(ol) { margin: var(--xc-space-3) 0; padding-left: var(--xc-space-7); }
.ir-ai-answer__markdown :deep(li + li) { margin-top: var(--xc-space-1); }
.ir-ai-answer__markdown :deep(a) { color: var(--xc-accent-blue); text-underline-offset: 3px; }
.ir-ai-answer__markdown :deep(blockquote) {
  margin: var(--xc-space-4) 0;
  padding-left: var(--xc-space-4);
  border-left: 2px solid var(--xc-border-accent);
  color: var(--xc-text-soft);
}
.ir-ai-answer__markdown :deep(code) {
  padding: 1px var(--xc-space-2);
  border-radius: var(--xc-radius-xs);
  background: var(--xc-surface-control);
  font-family: var(--xc-font-mono);
  font-size: var(--xc-fs-xs);
}
.ir-ai-answer__markdown :deep(pre) {
  max-width: 100%;
  margin: var(--xc-space-4) 0;
  padding: var(--xc-space-4) var(--xc-space-5);
  overflow-x: auto;
  border-radius: var(--xc-radius-sm);
  background: var(--xc-surface-control);
}
.ir-ai-answer__markdown :deep(pre code) { padding: 0; background: transparent; white-space: pre; }
.ir-ai-answer__markdown :deep(hr) { margin: var(--xc-space-6) 0; border: 0; border-top: 1px solid var(--xc-border-soft); }
.ir-ai-answer__markdown :deep(table) {
  width: max-content;
  min-width: 100%;
  margin: var(--xc-space-4) 0;
  border-collapse: collapse;
  font-family: var(--xc-font-num);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.ir-ai-answer__markdown :deep(th),
.ir-ai-answer__markdown :deep(td) {
  padding: var(--xc-space-3) var(--xc-space-5);
  border-bottom: 1px solid var(--xc-border-soft);
  text-align: left;
}
.ir-ai-answer__markdown :deep(th) {
  background: var(--xc-surface-control);
  color: var(--xc-text-strong);
  font-family: var(--xc-font-zh);
  font-weight: var(--xc-fw-medium);
}
.ir-ai-answer__markdown :deep(td) { color: var(--xc-text-default); }
.ir-ai-answer__actions { display: flex; flex-wrap: wrap; gap: var(--xc-space-3); margin-top: var(--xc-space-4); }
.ir-ai-answer__actions :deep(button) {
  min-height: 44px;
  padding: var(--xc-space-1) var(--xc-space-4);
  border: 1px solid var(--xc-accent-blue);
  border-radius: var(--xc-radius-sm);
  background: transparent;
  color: var(--xc-accent-blue);
  font-size: var(--xc-fs-xs);
  cursor: pointer;
}
</style>

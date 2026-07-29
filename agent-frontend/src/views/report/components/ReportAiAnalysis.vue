<template>
  <aside class="ir-report-ai-analysis">
    <header>
      <MagicStick aria-hidden="true" />
      <h4>AI 智能分析</h4>
    </header>
    <div class="ir-report-ai-analysis__rule" />
    <div class="ir-report-ai-analysis__body" v-html="content" />
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { MagicStick } from '@element-plus/icons-vue'
import { renderReportMarkdown } from '../utils/renderReportMarkdown'

const props = defineProps({ text: { type: String, default: '' }, fallback: { type: String, default: '' } })
const content = computed(() => renderReportMarkdown(props.text || props.fallback))
</script>

<style scoped>
.ir-report-ai-analysis { margin-top: 24px; padding: 24px; border: 1px solid var(--xc-report-border); border-left: 3px solid var(--xc-accent-blue); border-radius: var(--xc-radius-sm); background: var(--xc-report-ai); break-inside: avoid; }
.ir-report-ai-analysis header { display: flex; align-items: center; gap: 9px; }
.ir-report-ai-analysis header svg { width: 17px; height: 17px; color: var(--xc-accent-blue); }
.ir-report-ai-analysis h4 { margin: 0; color: var(--xc-text-strong); font-size: 14px; font-weight: var(--xc-fw-semi); }
.ir-report-ai-analysis__rule { height: 1px; margin: 14px 0 18px; background: var(--xc-report-border); }
.ir-report-ai-analysis__body { max-inline-size: 72ch; color: var(--xc-text-default); font-size: 14px; line-height: 1.8; overflow-wrap: anywhere; }
.ir-report-ai-analysis__body :deep(:first-child) { margin-top: 0; }
.ir-report-ai-analysis__body :deep(:last-child) { margin-bottom: 0; }
.ir-report-ai-analysis__body :deep(h1), .ir-report-ai-analysis__body :deep(h2), .ir-report-ai-analysis__body :deep(h3) { margin: 20px 0 10px; color: var(--xc-text-strong); font-size: 15px; font-weight: var(--xc-fw-semi); }
.ir-report-ai-analysis__body :deep(p), .ir-report-ai-analysis__body :deep(ul), .ir-report-ai-analysis__body :deep(ol), .ir-report-ai-analysis__body :deep(blockquote) { margin: 0 0 12px; }
.ir-report-ai-analysis__body :deep(ul), .ir-report-ai-analysis__body :deep(ol) { padding-left: 1.5em; }
.ir-report-ai-analysis__body :deep(blockquote) { padding: 8px 14px; border-left: 2px solid var(--xc-accent-blue); background: var(--xc-report-note); color: var(--xc-text-soft); }
.ir-report-ai-analysis__body :deep(code) { padding: 2px 5px; border-radius: var(--xc-radius-xs); background: var(--xc-report-note); color: var(--xc-text-strong); font-family: var(--xc-font-mono); font-size: .92em; }
</style>

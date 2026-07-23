<template>
  <section class="pm-result" aria-label="咨询结果">
    <div v-if="!consultation" class="pm-result__empty">你的咨询结果将展示在这里</div>
    <div v-else-if="consultation.status === 'processing'" class="pm-result__state" role="status" aria-live="polite">
      正在分析
    </div>
    <div v-else-if="consultation.status === 'failed'" class="pm-result__state pm-result__state--error" role="alert">
      <strong>咨询失败</strong>
      <span>请重新提交问题</span>
    </div>
    <article v-else-if="consultation.status === 'completed'" class="pm-result__card">
      <p class="pm-result__eyebrow">CONSULTATION RESULT</p>
      <h2>关于「{{ consultation.title || consultation.question }}」</h2>
      <p class="pm-result__answer">{{ consultation.answer }}</p>
      <footer>
        <span>检索范围：{{ consultation.sourceScope?.join(' / ') || '—' }}</span>
        <span>状态：分析完成</span>
      </footer>
    </article>
  </section>
</template>

<script setup>
defineProps({
  consultation: { type: Object, default: null },
})
</script>

<style scoped>
.pm-result { min-height: 260px; display: grid; place-items: stretch; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-md); background: var(--xc-surface-card); }
.pm-result__empty, .pm-result__state { display: grid; place-content: center; min-height: 260px; padding: var(--xc-space-6); color: var(--xc-text-mute); text-align: center; }
.pm-result__state { gap: var(--xc-space-2); color: var(--xc-text-soft); }
.pm-result__state--error strong { color: var(--xc-status-danger); }
.pm-result__card { padding: var(--xc-space-6); }
.pm-result__eyebrow { margin: 0; color: var(--xc-accent-blue); font-size: var(--xc-fs-2xs); letter-spacing: 0.04em; }
.pm-result__card h2 { margin: var(--xc-space-3) 0; color: var(--xc-text-strong); font-size: var(--xc-fs-h3); font-weight: var(--xc-fw-semi); line-height: var(--xc-lh-snug); }
.pm-result__answer { margin: 0; color: var(--xc-text-soft); font-size: var(--xc-fs-sm); line-height: var(--xc-lh-relaxed); white-space: pre-wrap; overflow-wrap: anywhere; }
.pm-result__card footer { display: flex; flex-wrap: wrap; gap: var(--xc-space-3); margin-top: var(--xc-space-6); color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
</style>

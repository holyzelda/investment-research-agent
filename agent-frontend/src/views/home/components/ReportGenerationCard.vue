<template>
  <article class="ir-report-delivery" :class="`ir-report-delivery--${status}`">
    <header class="ir-report-delivery__header">
      <span class="ir-report-delivery__document" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
          <path d="M6 2.75h8l4 4V21.25H6z" stroke-linejoin="round" />
          <path d="M14 2.75v4h4M9 11h6M9 14.5h6M9 18h4" stroke-linecap="round" />
        </svg>
      </span>
      <span class="ir-report-delivery__identity">
        <span class="ir-report-delivery__eyebrow">投研报告</span>
        <strong>{{ title || '正式投资分析报告' }}</strong>
      </span>
      <span class="ir-report-delivery__status" role="status" aria-live="polite" aria-atomic="true">
        <span v-if="status === 'generating'" class="ir-report-delivery__pulse" aria-hidden="true" />
        <svg v-else-if="status === 'completed'" viewBox="0 0 16 16" fill="none" stroke="currentColor" aria-hidden="true"><path d="m3 8 3 3 7-7" stroke-linecap="round" stroke-linejoin="round" /></svg>
        <svg v-else viewBox="0 0 16 16" fill="none" stroke="currentColor" aria-hidden="true"><path d="M8 4v5M8 12h.01" stroke-linecap="round" /><circle cx="8" cy="8" r="6" /></svg>
        {{ statusText }}
      </span>
    </header>

    <div class="ir-report-delivery__project">
      <strong>{{ projectName || '储能投资项目' }}</strong>
      <span>{{ statusDescription }}</span>
    </div>

    <dl class="ir-report-delivery__meta">
      <div>
        <dt>关联测算</dt>
        <dd class="xc-num">{{ version || '—' }}</dd>
      </div>
      <div>
        <dt>装机功率</dt>
        <dd class="xc-num">{{ powerText }}</dd>
      </div>
      <div>
        <dt>装机容量</dt>
        <dd class="xc-num">{{ capacityText }}</dd>
      </div>
    </dl>

    <div class="ir-report-delivery__scope">
      <span>报告内容</span>
      <ul aria-label="报告内容范围">
        <li v-for="item in scope" :key="item">{{ item }}</li>
      </ul>
    </div>

    <div v-if="status === 'failed' && errorMessage" class="ir-report-delivery__error" role="alert">
      {{ errorMessage }}
    </div>

    <footer class="ir-report-delivery__footer">
      <span v-if="status === 'completed'" class="ir-report-delivery__archive">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" aria-hidden="true"><path d="M2.5 5.5h11v8h-11zM2 2.5h12v3H2zM6 8.5h4" stroke-linejoin="round" /></svg>
        {{ archived ? '已存入项目档案' : '报告已生成' }}
      </span>
      <span v-else-if="status === 'generating'" class="ir-report-delivery__archive">完成后将存入项目档案</span>
      <span v-else class="ir-report-delivery__archive">可保留当前测算结果后重新生成</span>

      <button v-if="status === 'completed' && reportId" type="button" class="ir-report-delivery__action" @click="$emit('view', reportId)">
        查看正式报告
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" aria-hidden="true"><path d="m6 3 5 5-5 5" stroke-linecap="round" stroke-linejoin="round" /></svg>
      </button>
      <button v-else-if="status === 'failed' && taskId" type="button" class="ir-report-delivery__action" @click="$emit('retry', taskId)">
        重新生成报告
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" aria-hidden="true"><path d="M13 8a5 5 0 1 1-1.45-3.53M13 3v4H9" stroke-linecap="round" stroke-linejoin="round" /></svg>
      </button>
    </footer>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, default: 'generating' },
  reportId: { type: [String, Number], default: null },
  taskId: { type: [String, Number], default: null },
  title: { type: String, default: '正式投资分析报告' },
  projectName: { type: String, default: '' },
  version: { type: String, default: '' },
  powerText: { type: String, default: '—' },
  capacityText: { type: String, default: '—' },
  errorMessage: { type: String, default: '' },
  archived: { type: Boolean, default: false },
  scope: {
    type: Array,
    default: () => ['项目概览', '财务指标', '收益结构', '偿债分析', '风险提示'],
  },
})

defineEmits(['view', 'retry'])

const statusText = computed(() => ({
  generating: '生成中',
  completed: '已完成',
  failed: '生成失败',
}[props.status] || '生成中'))

const statusDescription = computed(() => ({
  generating: '测算模型已锁定，正在重构数据维度并生成深度洞察...',
  completed: '测算推演完成，高维分析报告已生成',
  failed: '报告未能完成，可检查原因后重新生成',
}[props.status] || '正在编制正式报告'))
</script>

<style scoped>
.ir-report-delivery {
  position: relative;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  overflow: hidden;
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-sm);
  background: var(--xc-surface-card);
  box-shadow: var(--xc-shadow-sm);
}
.ir-report-delivery__header {
  display: flex;
  align-items: center;
  gap: var(--xc-space-4);
  padding: var(--xc-space-5) var(--xc-space-6);
  border-bottom: 1px solid var(--xc-border-soft);
  background: var(--xc-surface-tinted);
}
.ir-report-delivery__document {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  color: var(--xc-accent-blue);
  border: 1px solid var(--xc-border-accent);
  border-radius: var(--xc-radius-sm);
  background: var(--xc-accent-blue-soft);
}
.ir-report-delivery__document svg { width: 21px; height: 21px; }
.ir-report-delivery__identity { min-width: 0; display: flex; flex: 1; flex-direction: column; gap: 2px; }
.ir-report-delivery__identity strong { overflow: hidden; color: var(--xc-text-strong); font-size: var(--xc-fs-md); font-weight: var(--xc-fw-semi); text-overflow: ellipsis; white-space: nowrap; }
.ir-report-delivery__eyebrow { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); letter-spacing: .08em; }
.ir-report-delivery__status { display: inline-flex; align-items: center; gap: var(--xc-space-2); padding: var(--xc-space-1) var(--xc-space-3); color: var(--xc-status-info); border-radius: var(--xc-radius-full); background: var(--xc-status-info-soft); font-size: var(--xc-fs-2xs); font-weight: var(--xc-fw-medium); white-space: nowrap; }
.ir-report-delivery--completed .ir-report-delivery__status { color: var(--xc-status-ok); background: var(--xc-status-ok-soft); }
.ir-report-delivery--failed .ir-report-delivery__status { color: var(--xc-status-danger); background: var(--xc-status-danger-soft); }
.ir-report-delivery__status svg { width: 13px; height: 13px; }
.ir-report-delivery__pulse { width: 7px; height: 7px; border-radius: 50%; background: currentColor; animation: ir-report-pulse 1.2s ease-in-out infinite; }
.ir-report-delivery__project { display: flex; flex-direction: column; gap: var(--xc-space-2); padding: var(--xc-space-5) var(--xc-space-6) var(--xc-space-4); }
.ir-report-delivery__project strong { color: var(--xc-text-strong); font-size: var(--xc-fs-base); font-weight: var(--xc-fw-semi); }
.ir-report-delivery__project span { color: var(--xc-text-mute); font-size: var(--xc-fs-xs); }
.ir-report-delivery__meta { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin: 0; padding: 0 var(--xc-space-6) var(--xc-space-5); }
.ir-report-delivery__meta > div { min-width: 0; padding: 0 var(--xc-space-4); border-left: 1px solid var(--xc-border-soft); }
.ir-report-delivery__meta > div:first-child { padding-left: 0; border-left: 0; }
.ir-report-delivery__meta dt { margin-bottom: var(--xc-space-2); color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.ir-report-delivery__meta dd { margin: 0; color: var(--xc-text-strong); font-size: var(--xc-fs-sm); font-weight: var(--xc-fw-medium); }
.ir-report-delivery__scope { display: flex; align-items: flex-start; gap: var(--xc-space-4); margin: 0 var(--xc-space-6) var(--xc-space-5); padding: var(--xc-space-3) var(--xc-space-4); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); background: var(--xc-surface-control); }
.ir-report-delivery__scope > span { flex: 0 0 auto; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.ir-report-delivery__scope ul { display: flex; flex-wrap: wrap; gap: var(--xc-space-2) var(--xc-space-4); margin: 0; padding: 0; list-style: none; }
.ir-report-delivery__scope li { position: relative; color: var(--xc-text-soft); font-size: var(--xc-fs-2xs); }
.ir-report-delivery__scope li + li::before { content: '·'; position: absolute; left: calc(-1 * var(--xc-space-3)); color: var(--xc-text-faint); }
.ir-report-delivery__error { margin: calc(-1 * var(--xc-space-2)) var(--xc-space-6) var(--xc-space-5); padding: var(--xc-space-3) var(--xc-space-4); color: var(--xc-status-danger); border: 1px solid var(--xc-status-danger-soft); border-radius: var(--xc-radius-sm); background: var(--xc-status-danger-soft); font-size: var(--xc-fs-xs); }
.ir-report-delivery__footer { display: flex; align-items: center; justify-content: space-between; gap: var(--xc-space-4); min-height: 54px; padding: var(--xc-space-3) var(--xc-space-6); border-top: 1px solid var(--xc-border-soft); }
.ir-report-delivery__archive { display: inline-flex; align-items: center; gap: var(--xc-space-2); color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.ir-report-delivery__archive svg { width: 14px; height: 14px; color: var(--xc-status-ok); }
.ir-report-delivery__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--xc-space-2);
  min-height: 36px;
  padding: 0 var(--xc-space-4);
  color: var(--xc-text-soft);
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-sm);
  background: transparent;
  font: inherit;
  font-size: var(--xc-fs-xs);
  cursor: pointer;
  transition: border-color var(--xc-dur-fast), background var(--xc-dur-fast), color var(--xc-dur-fast);
}
.ir-report-delivery__action svg { width: 14px; height: 14px; }
.ir-report-delivery__action:hover {
  border-color: var(--xc-border-accent);
  background: var(--xc-surface-control);
  color: var(--xc-text-strong);
}
.ir-report-delivery__action:focus-visible { outline: 2px solid var(--xc-accent-blue); outline-offset: 2px; }
@keyframes ir-report-pulse { 0%, 100% { opacity: .35; transform: scale(.8); } 50% { opacity: 1; transform: scale(1); } }
@media (max-width: 720px) {
  .ir-report-delivery__header, .ir-report-delivery__project, .ir-report-delivery__footer { padding-left: var(--xc-space-4); padding-right: var(--xc-space-4); }
  .ir-report-delivery__meta { padding-left: var(--xc-space-4); padding-right: var(--xc-space-4); }
  .ir-report-delivery__scope, .ir-report-delivery__error { margin-left: var(--xc-space-4); margin-right: var(--xc-space-4); }
  .ir-report-delivery__meta { grid-template-columns: 1fr; gap: var(--xc-space-3); }
  .ir-report-delivery__meta > div { padding: 0; border-left: 0; }
  .ir-report-delivery__footer { align-items: flex-start; flex-direction: column; }
}
@media (prefers-reduced-motion: reduce) {
  .ir-report-delivery__pulse { animation: none; }
}
</style>

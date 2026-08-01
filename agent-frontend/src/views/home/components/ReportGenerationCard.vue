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

    <template v-if="status !== 'failed'">
      <section class="ir-report-delivery__hero">
        <span class="ir-report-delivery__hero-mark" :class="{ 'ir-report-delivery__hero-mark--generating': status === 'generating' }" aria-hidden="true">
          <svg v-if="status === 'completed'" viewBox="0 0 40 40" fill="none" stroke="currentColor">
            <circle cx="20" cy="20" r="15" />
            <path d="m13.5 20.5 4.3 4.2 8.9-9.3" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <svg v-else viewBox="0 0 40 40" fill="none" stroke="currentColor">
            <circle cx="20" cy="20" r="15" opacity=".25" />
            <path class="ir-report-delivery__hero-progress" d="M20 5a15 15 0 0 1 15 15" stroke-linecap="round" />
            <path d="M14 21h12M14 16h8M14 26h9" stroke-linecap="round" />
          </svg>
        </span>
        <span class="ir-report-delivery__hero-copy">
          <strong>{{ status === 'completed' ? 'AI 已生成正式投资分析报告' : 'AI 正在生成正式投资分析报告' }}</strong>
          <span>{{ status === 'completed' ? '测算推演完成，完整报告已生成，可立即查看' : '正在整理测算结果并生成分析章节，请稍候' }}</span>
        </span>
        <button
          v-if="status === 'completed' && reportId"
          type="button"
          class="ir-report-delivery__primary-action"
          @click="$emit('view', reportId)"
        >
          <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" aria-hidden="true">
            <path d="M4 2.5h6l4 4v9H4zM10 2.5v4h4M6.5 10h5M6.5 12.5h4" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          立即查看完整报告
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" aria-hidden="true"><path d="m6 3 5 5-5 5" stroke-linecap="round" stroke-linejoin="round" /></svg>
        </button>
      </section>

      <div class="ir-report-delivery__project">
        <strong>{{ projectName || '储能投资项目' }}</strong>
        <span>基于当前测算结果，AI 已完成投资收益分析及风险评估</span>
      </div>

      <dl class="ir-report-delivery__metrics">
        <div>
          <span class="ir-report-delivery__metric-icon" aria-hidden="true">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor"><rect x="4" y="4" width="12" height="12" rx="2" /><path d="M7 8h6M7 11h6" stroke-linecap="round" /></svg>
          </span>
          <div class="ir-report-delivery__metric-copy">
            <dt>关联测算版本</dt>
            <dd class="xc-num">{{ version || '—' }}<small>报告关联版本</small></dd>
          </div>
        </div>
        <div>
          <span class="ir-report-delivery__metric-icon" aria-hidden="true">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor"><path d="m11 2-6 9h5l-1 7 6-10h-5z" stroke-linejoin="round" /></svg>
          </span>
          <div class="ir-report-delivery__metric-copy">
            <dt>装机功率</dt>
            <dd class="xc-num">{{ powerText }}<small>总装机功率</small></dd>
          </div>
        </div>
        <div>
          <span class="ir-report-delivery__metric-icon" aria-hidden="true">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor"><rect x="3" y="5" width="14" height="11" rx="2" /><path d="M7 5V3M13 5V3M7 10h6M8.5 8.5v3M11.5 8.5v3" stroke-linecap="round" /></svg>
          </span>
          <div class="ir-report-delivery__metric-copy">
            <dt>装机容量</dt>
            <dd class="xc-num">{{ capacityText }}<small>储能容量</small></dd>
          </div>
        </div>
      </dl>

      <div v-if="status === 'completed'" class="ir-report-delivery__details ir-report-delivery__details--revealed">
        <section class="ir-report-delivery__chapters">
          <h3>
            <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" aria-hidden="true"><path d="M4 2.5h7l3 3v10H4zM11 2.5v3h3M6.5 9h5M6.5 12h5" stroke-linecap="round" stroke-linejoin="round" /></svg>
            报告包含 <span class="xc-num">6</span> 个分析章节
          </h3>
          <ul aria-label="报告分析章节">
            <li v-for="(chapter, index) in chapterItems" :key="chapter.name">
              <span class="ir-report-delivery__chapter-icon" aria-hidden="true">
                <svg v-if="index === 0" viewBox="0 0 18 18" fill="none" stroke="currentColor"><path d="M3.5 4.5h11v10h-11zM6 7h6M6 10h4" stroke-linecap="round" stroke-linejoin="round" /></svg>
                <svg v-else-if="index === 1" viewBox="0 0 18 18" fill="none" stroke="currentColor"><path d="M3 14.5h12M5 12V8M9 12V4M13 12V6" stroke-linecap="round" /></svg>
                <svg v-else-if="index === 2" viewBox="0 0 18 18" fill="none" stroke="currentColor"><circle cx="9" cy="9" r="6" /><path d="M9 6v6M6 9h6" stroke-linecap="round" /></svg>
                <svg v-else-if="index === 3" viewBox="0 0 18 18" fill="none" stroke="currentColor"><rect x="3.5" y="5" width="11" height="9" rx="2" /><path d="M6 5V3M12 5V3M6.5 9h5" stroke-linecap="round" /></svg>
                <svg v-else-if="index === 4" viewBox="0 0 18 18" fill="none" stroke="currentColor"><path d="m9 2.5 6 3v4.2c0 3-2.5 5-6 5.8-3.5-.8-6-2.8-6-5.8V5.5zM9 6v4M9 12.5h.01" stroke-linecap="round" stroke-linejoin="round" /></svg>
                <svg v-else viewBox="0 0 18 18" fill="none" stroke="currentColor"><path d="m3 14 4-4 3 2 5-7M11 5h4v4" stroke-linecap="round" stroke-linejoin="round" /></svg>
              </span>
              <span>
                <strong>{{ chapter.name }}</strong>
                <small>{{ chapter.description }}</small>
              </span>
            </li>
          </ul>
        </section>

        <aside class="ir-report-delivery__summary">
          <h3>
            <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" aria-hidden="true"><path d="m9 2 1.2 3.3L14 6.5l-3.8 1.2L9 11l-1.2-3.3L4 6.5l3.8-1.2zM14 11l.6 1.7 1.7.6-1.7.6L14 15.5l-.6-1.6-1.7-.6 1.7-.6z" stroke-linejoin="round" /></svg>
            AI 共生成
          </h3>
          <ul>
            <li>
              <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" aria-hidden="true"><path d="M4 2.5h7l3 3v10H4zM11 2.5v3h3M6.5 9h5M6.5 12h4" stroke-linecap="round" stroke-linejoin="round" /></svg>
              <span><strong><span class="xc-num">6</span> 个分析章节</strong><small>结构完整的分析框架</small></span>
            </li>
            <li>
              <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" aria-hidden="true"><path d="M3 14.5h12M5 12V8M9 12V4M13 12V6" stroke-linecap="round" /></svg>
              <span><strong><span class="xc-num">20+</span> 项财务指标</strong><small>全面覆盖投资性测算</small></span>
            </li>
            <li>
              <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" aria-hidden="true"><path d="m9 2.5 6 3v4.2c0 3-2.5 5-6 5.8-3.5-.8-6-2.8-6-5.8V5.5zM6.5 9l1.6 1.6 3.5-3.7" stroke-linecap="round" stroke-linejoin="round" /></svg>
              <span><strong><span class="xc-num">5</span> 项深度分析</strong><small>偿债、现金流、利润、敏感性与投资结论</small></span>
            </li>
            <li>
              <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" aria-hidden="true"><circle cx="9" cy="9" r="6" /><path d="M9 5.5V9l2.5 1.5" stroke-linecap="round" stroke-linejoin="round" /></svg>
              <span><strong>约 <span class="xc-num">15</span> 页报告</strong><small>预计阅读 <span class="xc-num">8–10</span> 分钟</small></span>
            </li>
          </ul>
        </aside>
      </div>

      <footer v-if="status === 'completed'" class="ir-report-delivery__footer ir-report-delivery__footer--completed">
        <span class="ir-report-delivery__archive">
          <svg viewBox="0 0 32 32" fill="none" stroke="currentColor" aria-hidden="true"><rect x="3" y="3" width="26" height="26" rx="2" /><path d="m9 16 5 5 9-10" stroke-linecap="round" stroke-linejoin="round" /></svg>
          <span><strong>{{ archived ? '已存入项目档案' : '报告已生成' }}</strong><small>可在项目文档中随时查看和管理</small></span>
        </span>
        <span class="ir-report-delivery__pdf">
          <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" aria-hidden="true"><path d="M4 2.5h7l3 3v10H4zM11 2.5v3h3M6 11h6" stroke-linecap="round" stroke-linejoin="round" /></svg>
          支持 PDF 导出
        </span>
        <button
          v-if="reportId"
          type="button"
          class="ir-report-delivery__history-action"
          @click="$emit('view-history', reportId)"
        >
          查看历史报告
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" aria-hidden="true"><path d="m6 3 5 5-5 5" stroke-linecap="round" stroke-linejoin="round" /></svg>
        </button>
      </footer>
      <footer v-else class="ir-report-delivery__footer ir-report-delivery__footer--generating">
        <span class="ir-report-delivery__generating-note">
          <span class="ir-report-delivery__pulse" aria-hidden="true" />
          报告生成完成后将自动存入项目档案
        </span>
      </footer>
    </template>

    <template v-else>
      <div class="ir-report-delivery__project">
        <strong>{{ projectName || '储能投资项目' }}</strong>
        <span>{{ statusDescription }}</span>
      </div>

      <dl class="ir-report-delivery__meta">
        <div><dt>关联测算</dt><dd class="xc-num">{{ version || '—' }}</dd></div>
        <div><dt>装机功率</dt><dd class="xc-num">{{ powerText }}</dd></div>
        <div><dt>装机容量</dt><dd class="xc-num">{{ capacityText }}</dd></div>
      </dl>

      <div class="ir-report-delivery__scope">
        <span>报告内容</span>
        <ul aria-label="报告内容范围"><li v-for="item in scope" :key="item">{{ item }}</li></ul>
      </div>

      <div v-if="status === 'failed' && errorMessage" class="ir-report-delivery__error" role="alert">{{ errorMessage }}</div>

      <footer class="ir-report-delivery__footer">
        <span class="ir-report-delivery__archive">可保留当前测算结果后重新生成</span>
        <button v-if="taskId" type="button" class="ir-report-delivery__action" @click="$emit('retry', taskId)">
          重新生成报告
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" aria-hidden="true"><path d="M13 8a5 5 0 1 1-1.45-3.53M13 3v4H9" stroke-linecap="round" stroke-linejoin="round" /></svg>
        </button>
      </footer>
    </template>
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
    default: () => ['项目基本信息', '市场与政策', '项目测算边界', '主模型分析', '敏感情景测试', '结论与投资建议'],
  },
})

defineEmits(['view', 'retry', 'view-history'])

const chapterDescriptions = {
  项目基本信息: '项目要素与基本情况',
  市场与政策: '市场供需与政策环境',
  项目测算边界: '核心参数与财务基准',
  主模型分析: '偿债、现金流与利润分析',
  敏感情景测试: '关键变量与情景压力测试',
  结论与投资建议: '风险提示与投资判断',
}

const chapterItems = computed(() => props.scope.slice(0, 6).map((name) => ({
  name,
  description: chapterDescriptions[name] || '报告专题分析',
})))

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
  border-radius: var(--xc-radius-md);
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

.ir-report-delivery__hero {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--xc-space-5);
  margin: var(--xc-space-5) var(--xc-space-6) 0;
  padding: var(--xc-space-4) var(--xc-space-5);
  overflow: hidden;
  border: 1px solid var(--xc-border-accent);
  border-radius: var(--xc-radius-sm);
  background: linear-gradient(105deg, color-mix(in srgb, var(--xc-accent-blue) 10%, var(--xc-surface-control)), color-mix(in srgb, var(--xc-accent-blue) 4%, var(--xc-surface-card)));
}
.ir-report-delivery__hero::after {
  content: '';
  position: absolute;
  right: 25%;
  bottom: -70px;
  width: 210px;
  height: 120px;
  pointer-events: none;
  border-radius: 50%;
  background: radial-gradient(circle, color-mix(in srgb, var(--xc-accent-blue) 14%, transparent), transparent 68%);
}
.ir-report-delivery__hero-mark { position: relative; display: grid; place-items: center; width: 48px; height: 48px; flex: 0 0 auto; color: var(--xc-accent-blue); filter: drop-shadow(var(--xc-glow-blue)); }
.ir-report-delivery__hero-mark svg { width: 48px; height: 48px; stroke-width: 2; animation: ir-report-complete .6s ease-out both; }
.ir-report-delivery__hero-mark--generating svg { animation: none; }
.ir-report-delivery__hero-progress { transform-origin: center; animation: ir-report-spin 1.4s linear infinite; }
.ir-report-delivery__hero-copy { position: relative; z-index: 1; display: flex; min-width: 0; flex: 1; flex-direction: column; gap: var(--xc-space-2); }
.ir-report-delivery__hero-copy strong { color: var(--xc-text-strong); font-size: var(--xc-fs-base); font-weight: var(--xc-fw-semi); }
.ir-report-delivery__hero-copy > span { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.ir-report-delivery__primary-action,
.ir-report-delivery__history-action,
.ir-report-delivery__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--xc-space-2);
  min-height: 36px;
  border-radius: var(--xc-radius-sm);
  font: inherit;
  font-size: var(--xc-fs-xs);
  cursor: pointer;
  transition: transform var(--xc-dur-fast), border-color var(--xc-dur-fast), background var(--xc-dur-fast), color var(--xc-dur-fast), box-shadow var(--xc-dur-fast);
}
.ir-report-delivery__primary-action { position: relative; z-index: 1; flex: 0 0 auto; min-height: 42px; padding: 0 var(--xc-space-5); color: var(--xc-accent-blue); border: 1px solid var(--xc-border-accent); background: var(--xc-accent-blue-soft); box-shadow: var(--xc-shadow-sm); font-weight: var(--xc-fw-medium); }
.ir-report-delivery__primary-action svg:first-child { width: 17px; height: 17px; }
.ir-report-delivery__primary-action svg:last-child,
.ir-report-delivery__history-action svg,
.ir-report-delivery__action svg { width: 14px; height: 14px; }
.ir-report-delivery__primary-action:hover { transform: translateY(-1px); border-color: var(--xc-accent-blue); color: var(--xc-text-strong); box-shadow: var(--xc-glow-blue); }
.ir-report-delivery__primary-action:focus-visible,
.ir-report-delivery__history-action:focus-visible,
.ir-report-delivery__action:focus-visible { outline: 2px solid var(--xc-accent-blue); outline-offset: 2px; }

.ir-report-delivery__project { display: flex; flex-direction: column; gap: var(--xc-space-2); padding: var(--xc-space-5) var(--xc-space-6) var(--xc-space-4); }
.ir-report-delivery__project strong { color: var(--xc-text-strong); font-size: var(--xc-fs-base); font-weight: var(--xc-fw-semi); }
.ir-report-delivery__project span { color: var(--xc-text-mute); font-size: var(--xc-fs-xs); }
.ir-report-delivery__metrics { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--xc-space-4); margin: 0; padding: 0 var(--xc-space-6) var(--xc-space-4); }
.ir-report-delivery__metrics > div { display: flex; align-items: flex-start; gap: var(--xc-space-4); min-width: 0; padding: var(--xc-space-4); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); background: var(--xc-surface-control); }
.ir-report-delivery__metric-icon,
.ir-report-delivery__chapter-icon { display: grid; place-items: center; flex: 0 0 auto; color: var(--xc-accent-blue); border-radius: var(--xc-radius-sm); background: var(--xc-accent-blue-soft); }
.ir-report-delivery__metric-icon { width: 34px; height: 34px; }
.ir-report-delivery__metric-icon svg { width: 18px; height: 18px; }
.ir-report-delivery__metric-copy { display: flex; min-width: 0; flex-direction: column; }
.ir-report-delivery__metrics dt { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.ir-report-delivery__metrics dd { display: flex; margin: var(--xc-space-1) 0 0; color: var(--xc-text-strong); font-size: var(--xc-fs-base); font-weight: var(--xc-fw-semi); flex-direction: column; }
.ir-report-delivery__metrics small { margin-top: var(--xc-space-1); color: var(--xc-text-faint); font-family: inherit; font-size: var(--xc-fs-3xs); font-weight: var(--xc-fw-regular); }

.ir-report-delivery__details { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, .9fr); gap: var(--xc-space-4); padding: 0 var(--xc-space-6) var(--xc-space-5); }
.ir-report-delivery__details--revealed { animation: ir-report-reveal var(--xc-dur-slow) ease-out both; }
.ir-report-delivery__chapters,
.ir-report-delivery__summary { min-width: 0; padding: var(--xc-space-4); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); background: var(--xc-surface-control); }
.ir-report-delivery__summary { border-color: var(--xc-border-soft); background: var(--xc-surface-control); }
.ir-report-delivery__chapters h3,
.ir-report-delivery__summary h3 { display: flex; align-items: center; gap: var(--xc-space-2); margin: 0 0 var(--xc-space-4); color: var(--xc-text-soft); font-size: var(--xc-fs-xs); font-weight: var(--xc-fw-medium); }
.ir-report-delivery__chapters h3 svg,
.ir-report-delivery__summary h3 svg { width: 17px; height: 17px; color: var(--xc-accent-blue); }
.ir-report-delivery__chapters ul { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 var(--xc-space-4); margin: 0; padding: 0; list-style: none; }
.ir-report-delivery__chapters li { display: flex; align-items: center; gap: var(--xc-space-3); min-width: 0; padding: var(--xc-space-3) 0; border-top: 1px solid var(--xc-border-soft); }
.ir-report-delivery__chapters li:nth-child(-n+2) { border-top: 0; }
.ir-report-delivery__chapter-icon { width: 26px; height: 26px; border-radius: var(--xc-radius-full); }
.ir-report-delivery__chapter-icon svg { width: 15px; height: 15px; }
.ir-report-delivery__chapters li > span:last-child,
.ir-report-delivery__summary li > span { display: flex; min-width: 0; flex-direction: column; gap: 2px; }
.ir-report-delivery__chapters strong,
.ir-report-delivery__summary strong { color: var(--xc-text-soft); font-size: var(--xc-fs-2xs); font-weight: var(--xc-fw-medium); }
.ir-report-delivery__chapters small,
.ir-report-delivery__summary small { overflow-wrap: anywhere; color: var(--xc-text-faint); font-size: var(--xc-fs-3xs); line-height: 1.4; }
.ir-report-delivery__summary ul { display: flex; flex-direction: column; gap: var(--xc-space-3); margin: 0; padding: 0; list-style: none; }
.ir-report-delivery__summary li { display: flex; align-items: flex-start; gap: var(--xc-space-3); }
.ir-report-delivery__summary li > svg { width: 18px; height: 18px; flex: 0 0 auto; margin-top: 1px; color: var(--xc-accent-blue); }
.ir-report-delivery__summary .xc-num { color: var(--xc-accent-blue); }

.ir-report-delivery__footer { display: flex; align-items: center; justify-content: space-between; gap: var(--xc-space-4); min-height: 54px; padding: var(--xc-space-3) var(--xc-space-6); border-top: 1px solid var(--xc-border-soft); }
.ir-report-delivery__footer--completed { min-height: 64px; }
.ir-report-delivery__archive { display: inline-flex; align-items: center; gap: var(--xc-space-3); color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.ir-report-delivery__archive > svg { width: 28px; height: 28px; flex: 0 0 28px; color: var(--xc-status-ok); stroke-width: 2; }
.ir-report-delivery__archive > span { display: flex; flex-direction: column; gap: 2px; }
.ir-report-delivery__archive strong { color: var(--xc-text-soft); font-weight: var(--xc-fw-medium); }
.ir-report-delivery__archive small { color: var(--xc-text-faint); font-size: var(--xc-fs-3xs); }
.ir-report-delivery__pdf { display: inline-flex; align-items: center; gap: var(--xc-space-2); margin-left: auto; padding: var(--xc-space-2) var(--xc-space-3); color: var(--xc-text-mute); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); font-size: var(--xc-fs-2xs); }
.ir-report-delivery__pdf svg { width: 14px; height: 14px; }
.ir-report-delivery__history-action { flex: 0 0 auto; padding: 0 var(--xc-space-4); color: var(--xc-text-soft); border: 0; background: transparent; }
.ir-report-delivery__history-action:hover { color: var(--xc-text-strong); }
.ir-report-delivery__generating-note { display: inline-flex; align-items: center; gap: var(--xc-space-2); color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.ir-report-delivery__action { padding: 0 var(--xc-space-4); color: var(--xc-text-soft); border: 1px solid var(--xc-border-soft); background: transparent; }
.ir-report-delivery__action:hover { border-color: var(--xc-border-accent); background: var(--xc-surface-control); color: var(--xc-text-strong); }

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

@keyframes ir-report-pulse { 0%, 100% { opacity: .35; transform: scale(.8); } 50% { opacity: 1; transform: scale(1); } }
@keyframes ir-report-complete { from { opacity: 0; transform: scale(.75) rotate(-8deg); } to { opacity: 1; transform: scale(1) rotate(0); } }
@keyframes ir-report-spin { to { transform: rotate(360deg); } }
@keyframes ir-report-reveal { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
@media (max-width: 900px) {
  .ir-report-delivery__hero { align-items: flex-start; flex-wrap: wrap; }
  .ir-report-delivery__primary-action { width: 100%; }
  .ir-report-delivery__details { grid-template-columns: 1fr; }
}
@media (max-width: 720px) {
  .ir-report-delivery__header, .ir-report-delivery__project, .ir-report-delivery__footer { padding-left: var(--xc-space-4); padding-right: var(--xc-space-4); }
  .ir-report-delivery__identity strong { white-space: normal; }
  .ir-report-delivery__hero { margin-left: var(--xc-space-4); margin-right: var(--xc-space-4); }
  .ir-report-delivery__hero-mark { width: 40px; height: 40px; }
  .ir-report-delivery__hero-mark svg { width: 40px; height: 40px; }
  .ir-report-delivery__metrics, .ir-report-delivery__details, .ir-report-delivery__meta { padding-left: var(--xc-space-4); padding-right: var(--xc-space-4); }
  .ir-report-delivery__metrics, .ir-report-delivery__meta { grid-template-columns: 1fr; gap: var(--xc-space-3); }
  .ir-report-delivery__meta > div { padding: 0; border-left: 0; }
  .ir-report-delivery__scope, .ir-report-delivery__error { margin-left: var(--xc-space-4); margin-right: var(--xc-space-4); }
  .ir-report-delivery__footer { align-items: flex-start; flex-direction: column; }
  .ir-report-delivery__pdf { margin-left: 0; }
  .ir-report-delivery__history-action { padding-left: 0; }
}
@media (max-width: 460px) {
  .ir-report-delivery__header { align-items: flex-start; flex-wrap: wrap; }
  .ir-report-delivery__status { margin-left: 50px; }
  .ir-report-delivery__hero { flex-direction: column; }
  .ir-report-delivery__chapters ul { grid-template-columns: 1fr; }
  .ir-report-delivery__chapters li:nth-child(2) { border-top: 1px solid var(--xc-border-soft); }
}
@media (prefers-reduced-motion: reduce) {
  .ir-report-delivery__pulse, .ir-report-delivery__hero-mark svg, .ir-report-delivery__hero-progress, .ir-report-delivery__details--revealed { animation: none; }
  .ir-report-delivery__primary-action, .ir-report-delivery__history-action, .ir-report-delivery__action { transition: none; }
}
</style>

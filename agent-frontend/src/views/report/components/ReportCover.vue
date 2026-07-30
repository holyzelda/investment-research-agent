<template>
  <header class="ir-report-cover">
    <img class="ir-report-cover__image" :src="coverImage" alt="AI 储能与新能源电力系统" />
    <div class="ir-report-cover__shade" />
    <div class="ir-report-cover__title">
      <p>INVESTMENT ANALYSIS REPORT</p>
      <span aria-hidden="true" />
      <h1>储能参与中国电力市场<br />前期项目测算方案</h1>
    </div>
    <dl class="ir-report-cover__summary">
      <div class="ir-report-cover__project">
        <dt>项目名称</dt>
        <dd>{{ projectName }}</dd>
      </div>
      <div>
        <dt>编制单位</dt>
        <dd>{{ preparer }}</dd>
      </div>
      <div>
        <dt>编制日期</dt>
        <dd class="xc-num">{{ generatedDate }}</dd>
      </div>
    </dl>
  </header>
</template>

<script setup>
import coverImage from '@/assets/report/report-cover.png'

defineProps({
  projectName: { type: String, required: true },
  preparer: { type: String, required: true },
  generatedDate: { type: String, default: '' },
})
</script>

<style scoped>
.ir-report-cover { position: relative; height: 297mm; overflow: hidden; color: var(--xc-text-strong); background: var(--xc-report-page); }
.ir-report-cover__image { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.ir-report-cover__shade { position: absolute; inset: 0; background: var(--xc-report-cover-overlay); }
.ir-report-cover__title { position: absolute; z-index: 1; top: 12%; left: 9%; width: 72%; }
.ir-report-cover__title p { margin: 0; color: var(--xc-report-cover-eyebrow); font-family: var(--xc-font-en); font-size: 11pt; font-weight: var(--xc-fw-medium); letter-spacing: .14em; }
.ir-report-cover__title > span { display: block; width: 21mm; height: 2px; margin: 13px 0 22px; background: var(--xc-accent-blue); }
.ir-report-cover__title h1 { margin: 0; color: var(--xc-text-strong); font-size: 26pt; font-weight: var(--xc-fw-semi); line-height: 1.3; letter-spacing: .04em; }
.ir-report-cover__summary { position: absolute; z-index: 1; right: 9%; bottom: 7%; left: 9%; display: grid; grid-template-columns: minmax(0, 2fr) minmax(110px, 1fr); gap: 22px 32px; margin: 0; padding: 24px 28px; border: 1px solid var(--xc-report-cover-card-border); border-radius: var(--xc-radius-sm); background: var(--xc-report-cover-card); backdrop-filter: blur(var(--xc-blur-sm)); }
.ir-report-cover__summary div { min-width: 0; }
.ir-report-cover__project { grid-column: 1 / -1; }
.ir-report-cover__summary dt { margin-bottom: 7px; color: var(--xc-text-mute); font-size: 10pt; }
.ir-report-cover__summary dd { margin: 0; overflow-wrap: anywhere; color: var(--xc-text-strong); font-size: 13pt; font-weight: var(--xc-fw-medium); line-height: 1.45; }
@media (max-width: 720px) { .ir-report-cover__summary { grid-template-columns: 1fr; }.ir-report-cover__project { grid-column: auto; }.ir-report-cover__title { width: 82%; }.ir-report-cover__title h1 { font-size: 22pt; } }
</style>

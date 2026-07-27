<template>
  <section class="pm-result" aria-label="咨询结果">
    <div v-if="!consultation" class="pm-result__empty">
      <span><ScanSearch :size="18" /></span>
      <div><strong>等待研究问题</strong><p>提交后，政策结论与依据将在这里展开。</p></div>
    </div>
    <div v-else-if="consultation.status === 'processing'" class="pm-result__state" role="status" aria-live="polite">
      <LoaderCircle :size="18" />
      <div>
        <strong>正在分析</strong>
        <span>系统正在整理政策依据与市场信号</span>
      </div>
      <button v-if="readerMode" type="button" @click="emitReuseQuestion">基于此问题新建研究</button>
    </div>
    <div v-else-if="consultation.status === 'failed'" class="pm-result__state pm-result__state--error" role="alert">
      <CircleAlert :size="18" />
      <div>
        <strong>咨询失败</strong>
        <span>请重新发起这次研究</span>
      </div>
      <button v-if="readerMode" type="button" @click="emitReuseQuestion">重新发起</button>
    </div>
    <article v-else-if="consultation.status === 'completed'" class="pm-result__card" :class="{ 'is-reader': readerMode }">
      <div class="pm-result__heading"><span><FileCheck2 :size="17" /></span><p>研究结论</p><b>分析完成</b></div>
      <h2 v-if="!readerMode">关于「{{ consultation.title || consultation.question }}」</h2>
      <div class="pm-result__answer-panel">
        <div class="pm-result__markdown">
          <template v-for="(block, blockIndex) in answerBlocks" :key="`${block.type}-${blockIndex}`">
            <component :is="`h${block.level}`" v-if="block.type === 'heading'" class="pm-result__markdown-heading">
              <template v-for="(part, partIndex) in renderInline(block.text)" :key="partIndex">
                <strong v-if="part.type === 'strong'">{{ part.text }}</strong>
                <code v-else-if="part.type === 'code'">{{ part.text }}</code>
                <a v-else-if="part.type === 'link'" :href="part.url" target="_blank" rel="noopener noreferrer">{{ part.text }}</a>
                <span v-else>{{ part.text }}</span>
              </template>
            </component>
            <p v-else-if="block.type === 'paragraph'" class="pm-result__answer">
              <template v-for="(part, partIndex) in renderInline(block.text)" :key="partIndex">
                <strong v-if="part.type === 'strong'">{{ part.text }}</strong>
                <code v-else-if="part.type === 'code'">{{ part.text }}</code>
                <a v-else-if="part.type === 'link'" :href="part.url" target="_blank" rel="noopener noreferrer">{{ part.text }}</a>
                <span v-else>{{ part.text }}</span>
              </template>
            </p>
            <ul v-else-if="block.type === 'ul'" class="pm-result__list">
              <li v-for="(item, itemIndex) in block.items" :key="itemIndex">
                <template v-for="(part, partIndex) in renderInline(item)" :key="partIndex">
                  <strong v-if="part.type === 'strong'">{{ part.text }}</strong>
                  <code v-else-if="part.type === 'code'">{{ part.text }}</code>
                  <a v-else-if="part.type === 'link'" :href="part.url" target="_blank" rel="noopener noreferrer">{{ part.text }}</a>
                  <span v-else>{{ part.text }}</span>
                </template>
              </li>
            </ul>
            <ol v-else-if="block.type === 'ol'" class="pm-result__list pm-result__list--ordered">
              <li v-for="(item, itemIndex) in block.items" :key="itemIndex">
                <template v-for="(part, partIndex) in renderInline(item)" :key="partIndex">
                  <strong v-if="part.type === 'strong'">{{ part.text }}</strong>
                  <code v-else-if="part.type === 'code'">{{ part.text }}</code>
                  <a v-else-if="part.type === 'link'" :href="part.url" target="_blank" rel="noopener noreferrer">{{ part.text }}</a>
                  <span v-else>{{ part.text }}</span>
                </template>
              </li>
            </ol>
            <blockquote v-else-if="block.type === 'quote'" class="pm-result__quote">
              <template v-for="(part, partIndex) in renderInline(block.text)" :key="partIndex">
                <strong v-if="part.type === 'strong'">{{ part.text }}</strong>
                <code v-else-if="part.type === 'code'">{{ part.text }}</code>
                <a v-else-if="part.type === 'link'" :href="part.url" target="_blank" rel="noopener noreferrer">{{ part.text }}</a>
                <span v-else>{{ part.text }}</span>
              </template>
            </blockquote>
            <pre v-else-if="block.type === 'codeblock'" class="pm-result__code"><code>{{ block.text }}</code></pre>
            <div v-else-if="block.type === 'table'" class="pm-result__table-wrap">
              <table class="pm-result__table">
                <thead><tr><th v-for="(header, headerIndex) in block.headers" :key="headerIndex">{{ header }}</th></tr></thead>
                <tbody><tr v-for="(row, rowIndex) in block.rows" :key="rowIndex"><td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td></tr></tbody>
              </table>
            </div>
          </template>
        </div>
      </div>
      <footer class="pm-result__sources" aria-label="信息来源">
        <div class="pm-result__sources-title">
          <span></span>
          <strong>信息来源</strong>
        </div>
        <dl>
          <div v-for="item in sourceRows" :key="item.label" class="pm-result__source-row">
            <dt>{{ item.label }}</dt>
            <dd v-if="item.links?.length" class="pm-result__source-links">
              <template v-for="(link, index) in item.links" :key="`${link.url}-${index}`">
                <a v-if="link.isUrl" :href="link.url" target="_blank" rel="noopener noreferrer">{{ link.label }}</a>
                <span v-else>{{ link.label }}</span>
              </template>
            </dd>
            <dd v-else>{{ item.value }}</dd>
          </div>
        </dl>
      </footer>
      <button v-if="readerMode" type="button" class="pm-result__reuse" @click="emitReuseQuestion">基于此问题新建研究</button>
    </article>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { CircleAlert, FileCheck2, LoaderCircle, ScanSearch } from '@lucide/vue'

const props = defineProps({
  consultation: { type: Object, default: null },
  readerMode: { type: Boolean, default: false },
})

const emit = defineEmits(['reuse-question'])

const answerBlocks = computed(() => parseMarkdownBlocks(props.consultation?.answer || ''))

const sourceRows = computed(() => {
  const sourceData = props.consultation?.sourceData || {}
  const timeliness = sourceData.timeliness || {}
  const rows = []

  if (sourceData.sources?.length) rows.push({ label: '资料来源', links: sourceData.sources.map(normalizeSourceLink) })
  if (timeliness.province) rows.push({ label: '信息范围', value: timeliness.province })
  if (timeliness.as_of) rows.push({ label: '数据时点', value: timeliness.as_of })
  if (sourceData.reminders?.length) rows.push({ label: '分析提醒', value: sourceData.reminders.join('；') })

  rows.push({ label: '案卷状态', value: '分析完成' })
  return rows
})

function emitReuseQuestion() {
  emit('reuse-question', props.consultation?.question || props.consultation?.title || '')
}

function normalizeSourceLink(source) {
  const value = typeof source === 'string' ? source : source?.url || source?.link || source?.title || source?.name || ''
  const label = typeof source === 'string' ? source : source?.title || source?.name || source?.url || source?.link || ''
  const url = typeof source === 'string' ? source : source?.url || source?.link || ''
  return { label: label || value || '来源链接', url, isUrl: isHttpUrl(url || value) }
}

function isHttpUrl(value) {
  return /^https?:\/\//i.test(String(value || '').trim())
}

function parseMarkdownBlocks(value) {
  const lines = String(value || '').replace(/\r\n/g, '\n').split('\n')
  const blocks = []
  let paragraph = []
  let list = null

  const flushParagraph = () => {
    if (!paragraph.length) return
    blocks.push({ type: 'paragraph', text: paragraph.join(' ').trim() })
    paragraph = []
  }
  const flushList = () => {
    if (!list) return
    blocks.push(list)
    list = null
  }

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index]
    const trimmed = line.trim()

    if (!trimmed) {
      flushParagraph()
      flushList()
      continue
    }

    const fenceMatch = trimmed.match(/^```(.*)$/)
    if (fenceMatch) {
      flushParagraph()
      flushList()
      const codeLines = []
      index += 1
      while (index < lines.length && !lines[index].trim().startsWith('```')) {
        codeLines.push(lines[index])
        index += 1
      }
      blocks.push({ type: 'codeblock', text: codeLines.join('\n') })
      continue
    }

    if (isTableStart(lines, index)) {
      flushParagraph()
      flushList()
      const headers = splitTableRow(lines[index])
      index += 2
      const rows = []
      while (index < lines.length && /^\s*\|.*\|\s*$/.test(lines[index])) {
        rows.push(splitTableRow(lines[index]))
        index += 1
      }
      index -= 1
      blocks.push({ type: 'table', headers, rows })
      continue
    }

    const headingMatch = trimmed.match(/^(#{1,3})\s+(.+)$/)
    if (headingMatch) {
      flushParagraph()
      flushList()
      blocks.push({ type: 'heading', level: Math.min(headingMatch[1].length + 2, 5), text: headingMatch[2].trim() })
      continue
    }

    const quoteMatch = trimmed.match(/^>\s?(.+)$/)
    if (quoteMatch) {
      flushParagraph()
      flushList()
      blocks.push({ type: 'quote', text: quoteMatch[1].trim() })
      continue
    }

    const unorderedMatch = trimmed.match(/^[-*]\s+(.+)$/)
    if (unorderedMatch) {
      flushParagraph()
      if (!list || list.type !== 'ul') {
        flushList()
        list = { type: 'ul', items: [] }
      }
      list.items.push(unorderedMatch[1].trim())
      continue
    }

    const orderedMatch = trimmed.match(/^\d+[.)]\s+(.+)$/)
    if (orderedMatch) {
      flushParagraph()
      if (!list || list.type !== 'ol') {
        flushList()
        list = { type: 'ol', items: [] }
      }
      list.items.push(orderedMatch[1].trim())
      continue
    }

    flushList()
    paragraph.push(trimmed)
  }

  flushParagraph()
  flushList()
  return blocks.length ? blocks : [{ type: 'paragraph', text: '暂无研究结论' }]
}

function renderInline(value) {
  const text = String(value || '')
  const matcher = /(\*\*([^*]+)\*\*|`([^`]+)`|\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)|(https?:\/\/[^\s)]+))/g
  const parts = []
  let cursor = 0
  let match

  while ((match = matcher.exec(text))) {
    if (match.index > cursor) parts.push({ type: 'text', text: text.slice(cursor, match.index) })
    if (match[2]) parts.push({ type: 'strong', text: match[2] })
    else if (match[3]) parts.push({ type: 'code', text: match[3] })
    else if (match[4] && match[5]) parts.push({ type: 'link', text: match[4], url: match[5] })
    else if (match[6]) parts.push({ type: 'link', text: match[6], url: match[6] })
    cursor = matcher.lastIndex
  }

  if (cursor < text.length) parts.push({ type: 'text', text: text.slice(cursor) })
  return parts.length ? parts : [{ type: 'text', text }]
}

function isTableStart(lines, index) {
  return /^\s*\|.*\|\s*$/.test(lines[index] || '') && /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(lines[index + 1] || '')
}

function splitTableRow(line) {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((cell) => cell.trim())
}
</script>

<style scoped>
.pm-result { position: relative; min-height: 190px; display: grid; place-items: stretch; margin-top: 2px; padding-left: 26px; background: transparent; }
.pm-result::before { position: absolute; inset: 0 auto 0 0; width: 1px; background: var(--xc-border-soft); content: ''; }
.pm-result::after { position: absolute; top: 24px; left: -3px; width: 7px; height: 7px; border-radius: 50%; background: var(--pm-accent, var(--xc-accent-blue)); content: ''; }
.pm-result__empty, .pm-result__state { display: flex; align-items: flex-start; justify-content: flex-start; gap: 12px; min-height: 190px; padding: 20px 0; color: var(--xc-text-mute); text-align: left; }
.pm-result__empty > span { width: 32px; height: 32px; display: grid; place-items: center; flex: 0 0 auto; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); color: var(--pm-accent, var(--xc-accent-blue)); }
.pm-result__empty div { display: grid; gap: 4px; padding-top: 3px; }
.pm-result__empty strong { color: var(--xc-text-soft); font-size: var(--xc-fs-sm); font-weight: var(--xc-fw-medium); }
.pm-result__empty p { margin: 0; font-size: var(--xc-fs-xs); }
.pm-result__state { align-items: center; min-height: 120px; color: var(--xc-text-soft); }
.pm-result__state div { display: grid; gap: 4px; }
.pm-result__state strong { color: var(--xc-text-strong); font-size: var(--xc-fs-sm); font-weight: var(--xc-fw-semi); }
.pm-result__state span { color: var(--xc-text-mute); font-size: var(--xc-fs-xs); }
.pm-result__state svg { color: var(--pm-accent, var(--xc-accent-blue)); }
.pm-result__state--error strong { color: var(--xc-status-danger); }
.pm-result__state button, .pm-result__reuse { min-height: 38px; display: inline-flex; align-items: center; justify-content: center; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); padding: 8px 12px; background: transparent; color: var(--xc-text-strong); font: inherit; font-size: var(--xc-fs-xs); cursor: pointer; }
.pm-result__state button { margin-left: auto; }
.pm-result__state button:hover, .pm-result__state button:focus-visible, .pm-result__reuse:hover, .pm-result__reuse:focus-visible { border-color: var(--pm-accent, var(--xc-accent-blue)); outline: none; background: var(--xc-surface-frosted); }
.pm-result__card { padding: 18px 0 24px; }
.pm-result__heading { display: flex; align-items: center; gap: 8px; color: var(--pm-accent, var(--xc-accent-blue)); }
.pm-result__heading > span { width: 30px; height: 30px; display: grid; place-items: center; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); }
.pm-result__heading p { margin: 0; color: var(--xc-text-strong); font-size: var(--xc-fs-sm); font-weight: var(--xc-fw-semi); }
.pm-result__heading b { margin-left: auto; color: var(--xc-status-ok); font-family: var(--xc-font-mono); font-size: var(--xc-fs-2xs); font-weight: var(--xc-fw-medium); }
.pm-result__card h2 { margin: 18px 0 12px; color: var(--xc-text-strong); font-size: var(--xc-fs-h3); font-weight: var(--xc-fw-semi); line-height: var(--xc-lh-snug); }
.pm-result__card.is-reader .pm-result__answer { margin-top: 18px; }
.pm-result__answer-panel { padding: 18px 18px 16px; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); background: var(--xc-surface-raised); box-shadow: 0 10px 24px rgb(0 0 0 / 8%); }
.pm-result__markdown { display: grid; gap: 14px; max-width: 82ch; color: var(--xc-text-soft); font-size: var(--xc-fs-sm); line-height: 1.85; overflow-wrap: anywhere; }
.pm-result__markdown > * { margin: 0; }
.pm-result__markdown-heading { margin-top: 6px; color: var(--xc-text-strong); font-size: 17px; font-weight: var(--xc-fw-semi); line-height: 1.55; }
.pm-result__markdown-heading:first-child { margin-top: 0; }
.pm-result__answer { color: var(--xc-text-soft); white-space: pre-wrap; }
.pm-result__markdown strong { color: var(--xc-text-strong); font-weight: var(--xc-fw-semi); }
.pm-result__markdown code { border: 1px solid var(--xc-border-soft); border-radius: 4px; padding: 1px 5px; background: rgb(255 255 255 / 6%); color: var(--pm-accent, var(--xc-accent-blue)); font-family: var(--xc-font-mono); font-size: .92em; }
.pm-result__markdown a { color: var(--pm-accent, var(--xc-accent-blue)); text-decoration: none; text-underline-offset: 3px; }
.pm-result__markdown a:hover, .pm-result__markdown a:focus-visible { outline: none; text-decoration: underline; }
.pm-result__list { display: grid; gap: 9px; padding-left: 0; list-style: none; }
.pm-result__list li { position: relative; padding-left: 22px; }
.pm-result__list li::before { position: absolute; top: .78em; left: 4px; width: 6px; height: 6px; border-radius: 50%; background: var(--pm-accent, var(--xc-accent-blue)); content: ''; }
.pm-result__list--ordered { counter-reset: pm-result-list; }
.pm-result__list--ordered li { counter-increment: pm-result-list; }
.pm-result__list--ordered li::before { top: .15em; left: 0; width: 18px; height: 18px; display: grid; place-items: center; border: 1px solid var(--xc-border-soft); border-radius: 50%; background: transparent; color: var(--pm-accent, var(--xc-accent-blue)); font-family: var(--xc-font-mono); font-size: 10px; content: counter(pm-result-list); }
.pm-result__quote { border-left: 3px solid var(--pm-accent, var(--xc-accent-blue)); padding: 10px 14px; background: rgb(255 255 255 / 5%); color: var(--xc-text-soft); }
.pm-result__code { max-width: 100%; overflow: auto; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); padding: 12px; background: rgb(0 0 0 / 18%); color: var(--xc-text-soft); font-size: var(--xc-fs-xs); line-height: 1.7; }
.pm-result__code code { border: 0; padding: 0; background: transparent; color: inherit; }
.pm-result__table-wrap { max-width: 100%; overflow-x: auto; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); }
.pm-result__table { width: 100%; border-collapse: collapse; min-width: 420px; font-size: var(--xc-fs-xs); }
.pm-result__table th, .pm-result__table td { border-bottom: 1px solid var(--xc-border-soft); padding: 9px 10px; text-align: left; vertical-align: top; }
.pm-result__table th { background: rgb(255 255 255 / 6%); color: var(--xc-text-strong); font-weight: var(--xc-fw-semi); }
.pm-result__table tr:last-child td { border-bottom: 0; }
.pm-result__sources { display: grid; gap: 12px; margin-top: 16px; padding: 16px 0 0; border-top: 1px solid var(--xc-border-soft); }
.pm-result__sources-title { display: flex; align-items: center; gap: 8px; color: var(--xc-text-strong); font-size: var(--xc-fs-xs); font-weight: var(--xc-fw-semi); }
.pm-result__sources-title span { width: 8px; height: 8px; border-radius: 50%; background: var(--pm-accent, var(--xc-accent-blue)); }
.pm-result__sources dl { display: grid; gap: 10px; margin: 0; }
.pm-result__source-row { display: grid; grid-template-columns: 86px minmax(0, 1fr); gap: 12px; align-items: start; }
.pm-result__source-row dt { color: var(--xc-text-mute); font-family: var(--xc-font-mono); font-size: var(--xc-fs-2xs); }
.pm-result__source-row dd { margin: 0; color: var(--xc-text-soft); font-size: var(--xc-fs-xs); line-height: 1.7; overflow-wrap: anywhere; }
.pm-result__source-links { display: grid; gap: 6px; }
.pm-result__source-links a { color: var(--pm-accent, var(--xc-accent-blue)); text-decoration: none; text-underline-offset: 3px; }
.pm-result__source-links a:hover, .pm-result__source-links a:focus-visible { outline: none; text-decoration: underline; }
.pm-result__reuse { margin-top: 18px; }
@media (max-width: 520px) { .pm-result { padding-left: 18px; }.pm-result__heading b { display: none; }.pm-result__answer-panel { padding: 16px 14px 14px; }.pm-result__source-row { grid-template-columns: 1fr; gap: 4px; } }
@media (prefers-reduced-motion: no-preference) { .pm-result__state .lucide-loader-circle { animation: pm-result-spin 1.2s linear infinite; } }
@keyframes pm-result-spin { to { transform: rotate(360deg); } }
</style>

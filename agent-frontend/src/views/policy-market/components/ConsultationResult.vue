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
              <MarkdownInline :text="block.text" :reference-titles="referenceTitles" @cite-click="scrollToSource" />
            </component>
            <p v-else-if="block.type === 'paragraph'" class="pm-result__answer">
              <MarkdownInline :text="block.text" :reference-titles="referenceTitles" @cite-click="scrollToSource" />
            </p>
            <ul v-else-if="block.type === 'ul'" class="pm-result__list">
              <li v-for="(item, itemIndex) in block.items" :key="itemIndex">
                <MarkdownInline :text="item" :reference-titles="referenceTitles" @cite-click="scrollToSource" />
              </li>
            </ul>
            <ol v-else-if="block.type === 'ol'" class="pm-result__list pm-result__list--ordered">
              <li v-for="(item, itemIndex) in block.items" :key="itemIndex">
                <MarkdownInline :text="item" :reference-titles="referenceTitles" @cite-click="scrollToSource" />
              </li>
            </ol>
            <blockquote v-else-if="block.type === 'quote'" class="pm-result__quote">
              <MarkdownInline :text="block.text" :reference-titles="referenceTitles" @cite-click="scrollToSource" />
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
        <ol v-if="references.length" class="pm-result__refs">
          <li
            v-for="item in references"
            :id="`pm-source-${item.index}`"
            :key="item.index"
            class="pm-result__ref"
            :class="{ 'is-highlighted': highlightedIndex === item.index }"
          >
            <span class="pm-result__ref-index">{{ item.index }}</span>
            <div class="pm-result__ref-body">
              <button
                v-if="item.downloadUrl"
                type="button"
                class="pm-result__ref-file"
                :disabled="loadingToken === item.token"
                data-source-file
                @click="openSourceFile(item)"
              >
                {{ item.title }}
                <LoaderCircle v-if="loadingToken === item.token" :size="12" />
              </button>
              <a v-else-if="item.url" :href="item.url" target="_blank" rel="noopener noreferrer">{{ item.title }}</a>
              <span v-else>{{ item.title }}</span>
              <em class="pm-result__ref-type">{{ item.typeLabel }}</em>
              <em v-if="failedToken === item.token" class="pm-result__ref-error" role="alert">{{ sourceError }}</em>
            </div>
          </li>
        </ol>
        <p v-else class="pm-result__sources-empty">本次结论基于通用知识给出，没有可引用的源文件。</p>
      </footer>
      <button v-if="readerMode" type="button" class="pm-result__reuse" @click="emitReuseQuestion">基于此问题新建研究</button>
    </article>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { CircleAlert, FileCheck2, LoaderCircle, ScanSearch } from '@lucide/vue'
import { downloadSourceFile } from '@/api/policyMarket'
import MarkdownInline from './MarkdownInline.vue'

const props = defineProps({
  consultation: { type: Object, default: null },
  readerMode: { type: Boolean, default: false },
})

const emit = defineEmits(['reuse-question'])

const REFERENCE_TYPE_LABELS = { wiki: '知识库', web: '联网' }
const HIGHLIGHT_DURATION = 1500
// 浏览器能直接渲染的类型开新标签页预览，其余（docx/xlsx 等）存盘。
const PREVIEWABLE_TYPE = /^(application\/pdf|text\/plain|image\/)/i

const highlightedIndex = ref(0)
const loadingToken = ref('')
const failedToken = ref('')
const sourceError = ref('')
let highlightTimer = null
// 已创建但还没释放的 blob URL：立即 revoke 会让新标签页加载不出来，
// 只能延迟释放，并在组件卸载时兜底清一遍，避免连点多个文件时泄漏。
const objectUrls = new Set()

const answerBlocks = computed(() => parseMarkdownBlocks(props.consultation?.answer || ''))

const references = computed(() => {
  const sourceData = props.consultation?.sourceData || {}
  const list = sourceData.references
  if (Array.isArray(list) && list.length) {
    return list
      .filter((item) => item && item.index)
      .map((item) => ({
        index: Number(item.index),
        title: item.title || item.url || '来源链接',
        url: isHttpUrl(item.url) ? item.url : '',
        token: String(item.token || ''),
        // 后端只给知识库来源补代理地址；公网链接保持直跳。
        downloadUrl: String(item.downloadUrl || ''),
        typeLabel: REFERENCE_TYPE_LABELS[item.type] || '资料',
      }))
  }
  // 历史快照只存了 URL 列表（没有标题与类型），归一化成同一形状，
  // 否则旧咨询记录会整块丢失来源。
  return (Array.isArray(sourceData.sources) ? sourceData.sources : [])
    .map((source) => normalizeLegacySource(source))
    .filter((item) => item.title)
    .map((item, index) => ({ ...item, index: index + 1 }))
})

// 角标 hover 提示用：编号 → 文件名。
const referenceTitles = computed(() =>
  Object.fromEntries(references.value.map((item) => [item.index, `${item.title}（${item.typeLabel}）`])),
)

onBeforeUnmount(() => {
  if (highlightTimer) clearTimeout(highlightTimer)
  objectUrls.forEach((url) => URL.revokeObjectURL(url))
  objectUrls.clear()
})

// 飞书源文件：外部用户打不开原链接，经后端代理取回二进制再本地打开。
async function openSourceFile(item) {
  if (loadingToken.value) return
  loadingToken.value = item.token
  failedToken.value = ''

  try {
    const blob = await downloadSourceFile(item.token)
    const message = await readErrorMessage(blob)
    // 端点成功时返二进制、失败时返 {code,msg,data} JSON 壳；不识别的话
    // 用户会"下载到一个 JSON 文件"而不是看到报错。
    if (message) throw new Error(message)

    const objectUrl = URL.createObjectURL(blob)
    objectUrls.add(objectUrl)
    if (PREVIEWABLE_TYPE.test(blob.type)) window.open(objectUrl, '_blank', 'noopener')
    else triggerDownload(objectUrl, item.title)
    // 立即 revoke 会让新标签页/下载还没读完就失效，延迟释放；卸载时兜底。
    setTimeout(() => {
      URL.revokeObjectURL(objectUrl)
      objectUrls.delete(objectUrl)
    }, 60000)
  } catch (error) {
    failedToken.value = item.token
    sourceError.value = error?.message || '源文件打开失败，请稍后重试'
  } finally {
    loadingToken.value = ''
  }
}

// 失败响应是 JSON blob，读出 msg 当错误文案；成功的二进制返回空串。
async function readErrorMessage(blob) {
  if (!blob || !/^application\/json/i.test(blob.type || '')) return ''
  try {
    const payload = JSON.parse(await blob.text())
    return payload?.msg || '源文件打开失败，请稍后重试'
  } catch {
    return '源文件打开失败，请稍后重试'
  }
}

function triggerDownload(objectUrl, filename) {
  const anchor = document.createElement('a')
  anchor.href = objectUrl
  // 后端 Content-Disposition 已给了原始文件名，但 blob URL 走不到那里，只能用标题。
  anchor.download = filename || '政策源文件'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
}

function scrollToSource(index) {
  highlightedIndex.value = index
  if (highlightTimer) clearTimeout(highlightTimer)
  highlightTimer = setTimeout(() => { highlightedIndex.value = 0 }, HIGHLIGHT_DURATION)

  const target = document.getElementById(`pm-source-${index}`)
  if (!target?.scrollIntoView) return
  // 与 policy-market/index.vue 的滚动策略一致：窄屏用平滑滚动，宽屏直接定位。
  const isCompact = window.matchMedia?.('(max-width: 1100px)')?.matches
  target.scrollIntoView({ behavior: isCompact ? 'smooth' : 'auto', block: 'nearest' })
}

function emitReuseQuestion() {
  emit('reuse-question', props.consultation?.question || props.consultation?.title || '')
}

// 历史快照的 sources 只有 URL（或松散对象），补齐成与 references 一致的形状。
function normalizeLegacySource(source) {
  const url = typeof source === 'string' ? source : source?.url || source?.link || ''
  const title = typeof source === 'string' ? source : source?.title || source?.name || url
  return { title: title || url, url: isHttpUrl(url) ? url : '', typeLabel: '资料' }
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
.pm-result__sources-empty { margin: 0; color: var(--xc-text-mute); font-size: var(--xc-fs-xs); line-height: 1.7; }
.pm-result__refs { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; counter-reset: none; }
/* scroll-margin-top 补偿吸顶 reader bar，与 index.vue 的 result-anchor 同值 */
.pm-result__ref { display: grid; grid-template-columns: 18px minmax(0, 1fr); gap: 10px; align-items: start; border-radius: var(--xc-radius-sm); padding: 4px 6px; scroll-margin-top: 82px; transition: background-color .25s ease; }
.pm-result__ref.is-highlighted { background: var(--xc-surface-frosted); }
.pm-result__ref-index { width: 18px; height: 18px; display: grid; place-items: center; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-full); color: var(--pm-accent, var(--xc-accent-blue)); font-family: var(--xc-font-mono); font-size: var(--xc-fs-3xs); }
.pm-result__ref-body { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px; color: var(--xc-text-soft); font-size: var(--xc-fs-xs); line-height: 1.7; overflow-wrap: anywhere; }
.pm-result__ref-body a { color: var(--pm-accent, var(--xc-accent-blue)); text-decoration: none; text-underline-offset: 3px; }
.pm-result__ref-body a:hover, .pm-result__ref-body a:focus-visible { outline: none; text-decoration: underline; }
.pm-result__ref-type { flex: 0 0 auto; color: var(--xc-text-mute); font-family: var(--xc-font-mono); font-size: var(--xc-fs-2xs); font-style: normal; }
/* 飞书源文件走后端代理，是按钮而非链接，但视觉上与来源链接保持一致 */
.pm-result__ref-file { display: inline-flex; align-items: center; gap: 6px; border: 0; padding: 0; background: transparent; color: var(--pm-accent, var(--xc-accent-blue)); font: inherit; text-align: left; cursor: pointer; }
.pm-result__ref-file:hover, .pm-result__ref-file:focus-visible { outline: none; text-decoration: underline; text-underline-offset: 3px; }
.pm-result__ref-file:disabled { color: var(--xc-text-mute); cursor: progress; }
.pm-result__ref-error { flex: 1 0 100%; color: var(--xc-status-danger); font-size: var(--xc-fs-2xs); font-style: normal; }
.pm-result__reuse { margin-top: 18px; }
@media (max-width: 520px) { .pm-result { padding-left: 18px; }.pm-result__heading b { display: none; }.pm-result__answer-panel { padding: 16px 14px 14px; } }
@media (prefers-reduced-motion: no-preference) { .pm-result__state .lucide-loader-circle, .pm-result__ref-file .lucide-loader-circle { animation: pm-result-spin 1.2s linear infinite; } }
@keyframes pm-result-spin { to { transform: rotate(360deg); } }
</style>

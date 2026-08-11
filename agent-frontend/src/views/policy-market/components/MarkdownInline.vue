<template>
  <template v-for="(part, partIndex) in parts" :key="partIndex">
    <strong v-if="part.type === 'strong'">{{ part.text }}</strong>
    <code v-else-if="part.type === 'code'">{{ part.text }}</code>
    <a v-else-if="part.type === 'link'" :href="part.url" target="_blank" rel="noopener noreferrer">{{ part.text }}</a>
    <button
      v-else-if="part.type === 'cite'"
      type="button"
      class="xc-reset-button pm-cite"
      :title="citeTitle(part.index)"
      :aria-label="`跳转到第 ${part.index} 条来源`"
      @click="$emit('cite-click', part.index)"
    >{{ part.index }}</button>
    <span v-else>{{ part.text }}</span>
  </template>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  text: { type: String, default: '' },
  // 来源标题表：角标 hover 时提示对应文件，省得用户必须滚到底部才知道引了什么。
  referenceTitles: { type: Object, default: () => ({}) },
})

defineEmits(['cite-click'])

const parts = computed(() => renderInline(props.text))

function citeTitle(index) {
  return props.referenceTitles?.[index] || `第 ${index} 条来源`
}

function renderInline(value) {
  const text = String(value || '')
  const matcher = /(\*\*([^*]+)\*\*|`([^`]+)`|\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)|(https?:\/\/[^\s)]+)|\[(\d{1,2})\])/g
  const parts = []
  let cursor = 0
  let match

  while ((match = matcher.exec(text))) {
    if (match.index > cursor) parts.push({ type: 'text', text: text.slice(cursor, match.index) })
    if (match[2]) parts.push({ type: 'strong', text: match[2] })
    else if (match[3]) parts.push({ type: 'code', text: match[3] })
    else if (match[4] && match[5]) parts.push({ type: 'link', text: match[4], url: match[5] })
    else if (match[6]) parts.push({ type: 'link', text: match[6], url: match[6] })
    // 引用角标放在最后：链接式 [文本](url) 的分支必须先匹配，否则 [1] 会被误判。
    else if (match[7]) parts.push({ type: 'cite', index: Number(match[7]) })
    cursor = matcher.lastIndex
  }

  if (cursor < text.length) parts.push({ type: 'text', text: text.slice(cursor) })
  return parts.length ? parts : [{ type: 'text', text }]
}

defineExpose({ renderInline })
</script>

<style scoped>
/* 上标角标：样式沿用有序列表的圆形数字标记，保持同一套视觉语言。
   颜色必须写 var(--pm-accent, ...) 的 fallback —— --pm-accent 定义在父级
   policy-market/index.vue，组件单独挂载时拿不到。 */
.pm-cite {
  min-width: 15px;
  height: 15px;
  display: inline-grid;
  place-items: center;
  margin: 0 1px;
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-full);
  padding: 0 3px;
  color: var(--pm-accent, var(--xc-accent-blue));
  font-family: var(--xc-font-mono);
  font-size: var(--xc-fs-3xs);
  line-height: 1;
  vertical-align: super;
  cursor: pointer;
}
.pm-cite:hover, .pm-cite:focus-visible { border-color: var(--pm-accent, var(--xc-accent-blue)); background: var(--xc-surface-frosted); }
</style>

<template>
  <component
    :is="'el-dialog'"
    :model-value="modelValue"
    width="min(560px, calc(100vw - 32px))"
    :show-close="true"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <template #header>
      <p class="pm-news-dialog__category">{{ news?.category || '市场资讯' }}</p>
      <h2>{{ news?.title || '资讯详情' }}</h2>
    </template>
    <time class="pm-news-dialog__time">{{ formatPublishedAt(news?.publishedAt) }}</time>
    <p class="pm-news-dialog__content">{{ news?.content || '暂无详情内容' }}</p>
    <footer class="pm-news-dialog__source">来源：{{ news?.source || '—' }}</footer>
  </component>
</template>

<script setup>
defineProps({
  modelValue: { type: Boolean, default: false },
  news: { type: Object, default: null },
})

defineEmits(['update:modelValue'])

function formatPublishedAt(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  const parts = new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(date)
  const values = Object.fromEntries(parts.filter((part) => part.type !== 'literal').map((part) => [part.type, part.value]))
  return `${values.year}.${values.month}.${values.day}`
}
</script>

<style scoped>
.pm-news-dialog__category { margin: 0; color: var(--xc-accent-blue); font-size: var(--xc-fs-2xs); letter-spacing: 0.04em; }
.pm-news-dialog__category + h2 { margin: var(--xc-space-2) 0 0; color: var(--xc-text-strong); font-size: var(--xc-fs-h3); font-weight: var(--xc-fw-semi); line-height: var(--xc-lh-snug); }
.pm-news-dialog__time, .pm-news-dialog__source { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.pm-news-dialog__content { margin: var(--xc-space-5) 0; color: var(--xc-text-soft); font-size: var(--xc-fs-sm); line-height: var(--xc-lh-relaxed); white-space: pre-wrap; overflow-wrap: anywhere; }
</style>

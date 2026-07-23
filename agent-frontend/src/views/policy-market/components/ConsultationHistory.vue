<template>
  <aside class="pm-history" aria-label="我的提问">
    <div class="pm-history__heading">
      <h2>我的提问</h2>
      <button type="button" class="pm-history__new" aria-label="新建提问" @click="$emit('new-question')">+</button>
    </div>
    <p class="pm-history__caption">历史咨询记录</p>
    <p v-if="!consultations.length" class="pm-history__empty">暂无咨询记录</p>
    <nav v-else class="pm-history__list" aria-label="历史咨询记录">
      <button
        v-for="item in consultations"
        :key="item.id"
        type="button"
        class="pm-history__item"
        :class="{ 'is-active': item.id === selectedId }"
        :data-consultation-id="item.id"
        :aria-current="item.id === selectedId ? 'page' : undefined"
        @click="$emit('select', item.id)"
      >
        <span class="pm-history__title">{{ item.title || item.question }}</span>
        <time>{{ formatHistoryTime(item.createdAt) }}</time>
      </button>
    </nav>
  </aside>
</template>

<script setup>
defineProps({
  consultations: { type: Array, default: () => [] },
  selectedId: { type: [String, Number], default: null },
})

defineEmits(['new-question', 'select'])

function formatHistoryTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit' }).format(date)
}
</script>

<style scoped>
.pm-history { min-width: 0; display: flex; flex-direction: column; padding: var(--xc-space-5); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-md); background: var(--xc-surface-card); }
.pm-history__heading { display: flex; align-items: center; justify-content: space-between; gap: var(--xc-space-3); }
.pm-history__heading h2 { margin: 0; color: var(--xc-text-strong); font-size: var(--xc-fs-md); font-weight: var(--xc-fw-semi); }
.pm-history__new { width: 28px; height: 28px; border: 1px solid var(--xc-border-soft); border-radius: 50%; background: var(--xc-surface-control); color: var(--xc-text-strong); font-size: var(--xc-fs-lg); line-height: 1; cursor: pointer; }
.pm-history__new:hover, .pm-history__new:focus-visible { border-color: var(--xc-border-accent); background: var(--xc-surface-raised); }
.pm-history__caption, .pm-history__empty { margin: var(--xc-space-2) 0 0; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.pm-history__list { display: grid; gap: var(--xc-space-2); margin-top: var(--xc-space-5); overflow-y: auto; }
.pm-history__item { display: grid; gap: var(--xc-space-2); width: 100%; border: 1px solid transparent; border-radius: var(--xc-radius-sm); padding: var(--xc-space-3); background: transparent; color: var(--xc-text-soft); text-align: left; cursor: pointer; }
.pm-history__item:hover, .pm-history__item:focus-visible, .pm-history__item.is-active { border-color: var(--xc-border-accent); background: var(--xc-surface-raised); color: var(--xc-text-strong); }
.pm-history__title { overflow: hidden; font-size: var(--xc-fs-xs); line-height: var(--xc-lh-normal); text-overflow: ellipsis; white-space: nowrap; }
.pm-history__item time { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
</style>

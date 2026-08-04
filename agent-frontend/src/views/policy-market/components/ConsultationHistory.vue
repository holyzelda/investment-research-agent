<template>
  <aside class="pm-history" aria-label="我的提问">
    <div class="pm-history__heading">
      <div><span>RESEARCH FILES</span><h2>研究案卷</h2></div>
      <button type="button" class="pm-history__new" aria-label="新建提问" title="新建提问" @click="$emit('new-question')"><Plus :size="17" /></button>
    </div>
    <p class="pm-history__caption">{{ consultations.length }} 项历史研究</p>
    <p v-if="!consultations.length" class="pm-history__empty">暂无咨询记录</p>
    <nav v-else class="pm-history__list" aria-label="历史咨询记录">
      <div
        v-for="item in consultations"
        :key="item.id"
        class="pm-history__item"
        :class="{ 'is-active': item.id === selectedId }"
      >
        <button
          type="button"
          class="pm-history__select"
          :data-consultation-id="item.id"
          :aria-current="item.id === selectedId ? 'page' : undefined"
          @click="$emit('select', item.id)"
        >
          <span class="pm-history__content">
            <span class="pm-history__title">{{ item.title || item.question }}</span>
            <time>{{ formatHistoryTime(item.createdAt) }}</time>
          </span>
        </button>
        <button
          type="button"
          class="pm-history__delete"
          aria-label="删除研究记录"
          title="删除研究记录"
          @click.stop="$emit('delete', item.id)"
        >
          <Trash2 :size="15" />
        </button>
      </div>
    </nav>
  </aside>
</template>

<script setup>
import { Plus, Trash2 } from '@lucide/vue'

defineProps({
  consultations: { type: Array, default: () => [] },
  selectedId: { type: [String, Number], default: null },
})

defineEmits(['new-question', 'select', 'delete'])

function formatHistoryTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit' }).format(date)
}
</script>

<style scoped>
.pm-history { position: sticky; top: 20px; min-width: 0; display: flex; flex-direction: column; min-height: min(700px, calc(100vh - 104px)); padding: 8px 20px 8px 0; border-right: 1px solid var(--xc-border-soft); background: transparent; }
.pm-history__heading { display: flex; align-items: center; justify-content: space-between; gap: var(--xc-space-3); }
.pm-history__heading > div { display: grid; gap: 4px; }
.pm-history__heading span { color: var(--xc-text-mute); font-family: var(--xc-font-mono); font-size: 10px; }
.pm-history__heading h2 { margin: 0; color: var(--xc-text-strong); font-size: var(--xc-fs-md); font-weight: var(--xc-fw-semi); }
.pm-history__new { width: 36px; height: 36px; display: grid; place-items: center; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); background: transparent; color: var(--xc-text-strong); line-height: 1; cursor: pointer; }
.pm-history__new:hover, .pm-history__new:focus-visible { border-color: var(--xc-border-accent); background: var(--xc-surface-raised); }
.pm-history__caption, .pm-history__empty { margin: var(--xc-space-2) 0 0; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.pm-history__list { display: grid; max-height: calc(100vh - 190px); margin-top: 18px; overflow-y: auto; scrollbar-width: none; }
.pm-history__list::-webkit-scrollbar { display: none; }
.pm-history__item { position: relative; min-width: 0; border-top: 1px solid var(--xc-border-soft); }
.pm-history__select { display: block; width: 100%; border: 0; border-radius: 0; padding: 13px 44px 13px 12px; background: transparent; color: var(--xc-text-soft); text-align: left; cursor: pointer; }
.pm-history__content { min-width: 0; display: grid; gap: 7px; }
.pm-history__delete { position: absolute; top: 10px; right: 8px; width: 28px; height: 28px; display: grid; place-items: center; border: 0; border-radius: var(--xc-radius-sm); padding: 0; background: transparent; color: var(--xc-text-mute); cursor: pointer; opacity: 0; transition: opacity 160ms ease, background-color 160ms ease, color 160ms ease; }
.pm-history__item:hover .pm-history__delete, .pm-history__item:focus-within .pm-history__delete { opacity: 1; }
.pm-history__delete:hover, .pm-history__delete:focus-visible { background: color-mix(in srgb, var(--xc-status-danger) 16%, transparent); color: var(--xc-status-danger); outline: none; }
.pm-history__delete:focus-visible { box-shadow: 0 0 0 2px var(--xc-status-danger); }
.pm-history__item::before { position: absolute; inset: 10px auto 10px 0; width: 2px; background: transparent; content: ''; }
.pm-history__select:hover, .pm-history__select:focus-visible { outline: none; background: var(--xc-surface-frosted); color: var(--xc-text-strong); }
.pm-history__select:focus-visible { box-shadow: inset 0 0 0 2px var(--pm-accent, var(--xc-accent-blue)); }
.pm-history__item.is-active { background: var(--xc-surface-frosted); color: var(--xc-text-strong); }
.pm-history__item.is-active::before { background: var(--pm-accent, var(--xc-accent-blue)); }
.pm-history__title { display: -webkit-box; overflow: hidden; font-size: var(--xc-fs-xs); line-height: var(--xc-lh-normal); -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.pm-history__item time { color: var(--xc-text-mute); font-family: var(--xc-font-mono); font-size: var(--xc-fs-2xs); }
@media (max-width: 1100px) {
  .pm-history { position: static; min-height: 0; padding: 4px 0 18px; border-right: 0; border-bottom: 1px solid var(--xc-border-soft); }
  .pm-history__caption { margin-top: 4px; }
  .pm-history__list { grid-auto-flow: column; grid-auto-columns: minmax(188px, 23%); max-height: none; margin-top: 12px; overflow-x: auto; overflow-y: hidden; }
  .pm-history__item { border-top: 1px solid var(--xc-border-soft); }
}
@media (max-width: 640px) { .pm-history__list { grid-auto-columns: minmax(200px, 68vw); } }
</style>

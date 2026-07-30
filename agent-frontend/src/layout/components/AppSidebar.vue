<template>
  <div
    class="ir-shell-wrap"
    :class="{
      'is-collapsed': collapsed && !drawerOpen,
      'is-drawer-open': drawerOpen,
    }"
  >
    <button
      v-if="drawerOpen"
      class="ir-shell__drawer-scrim"
      type="button"
      aria-label="关闭菜单"
      @click="$emit('close-drawer')"
    />

    <aside class="ir-shell" data-testid="app-shell" aria-label="应用菜单">
      <header class="ir-shell__brand">
        <span class="ir-shell__logo-frame">
          <img class="ir-shell__logo" src="/brand-logo.svg" alt="" aria-hidden="true" />
        </span>
        <span class="ir-shell__brand-copy">
          <strong>朱雀投研智能体</strong>
          <small>ZRA · STORAGE INVESTMENT AI</small>
        </span>
        <button
          class="ir-shell__toggle"
          type="button"
          :aria-label="drawerOpen ? '关闭菜单' : collapsed ? '展开侧栏' : '折叠侧栏'"
          :data-tip="drawerOpen ? '关闭菜单' : collapsed ? '展开侧栏' : '折叠侧栏'"
          @click="onToggle"
        >
          <X v-if="drawerOpen" aria-hidden="true" />
          <PanelLeftOpen v-else-if="collapsed" aria-hidden="true" />
          <PanelLeftClose v-else aria-hidden="true" />
        </button>
      </header>

      <button
        class="ir-shell__new"
        type="button"
        data-tip="新建会话"
        @click="$emit('new-chat')"
      >
        <Plus class="ir-shell__new-icon" aria-hidden="true" />
        <span class="ir-shell__label">新建会话</span>
      </button>

      <div class="ir-shell__section-title">投资分析工作台</div>
      <nav class="ir-shell__nav" aria-label="投资分析工作台">
        <button
          v-for="item in navItems"
          :key="item.key || item.path"
          class="ir-shell__nav-item"
          :class="{
            'is-active': (item.key || item.path) === active,
            'is-disabled': item.disabled,
          }"
          type="button"
          :disabled="item.disabled"
          :aria-current="(item.key || item.path) === active ? 'page' : undefined"
          :aria-label="item.label"
          :data-tip="item.label"
          @click="onNav(item)"
        >
          <span class="ir-shell__nav-icon" v-html="item.icon" aria-hidden="true" />
          <span class="ir-shell__nav-label ir-shell__label">{{ item.label }}</span>
          <span v-if="item.meta" class="ir-shell__nav-meta ir-shell__label">{{ item.meta }}</span>
        </button>
      </nav>

      <section class="ir-shell__history" aria-labelledby="ir-shell-history-title">
        <div class="ir-shell__divider" />
        <div id="ir-shell-history-title" class="ir-shell__history-title">历史测算</div>
        <p v-if="!history.length" class="ir-shell__history-empty">暂无历史测算</p>
        <ul v-else class="ir-shell__history-list">
          <li
            v-for="conversation in history"
            :key="conversation.conversationId"
            class="ir-shell__history-item"
            :class="{ 'is-current': conversation.conversationId === current }"
            :title="conversation.title || '未命名会话'"
            role="button"
            tabindex="0"
            @click="$emit('open-history', conversation.conversationId)"
            @keydown.enter="$emit('open-history', conversation.conversationId)"
            @keydown.space.prevent="$emit('open-history', conversation.conversationId)"
          >
            <span v-if="conversation.createdAt" class="ir-shell__history-date xc-num">
              {{ formatDateLabel(conversation.createdAt) }}
            </span>
            <span class="ir-shell__history-name">{{ conversation.title || '未命名会话' }}</span>
            <span class="ir-shell__history-actions" @click.stop @keydown.stop>
              <button
                class="ir-shell__history-action ir-shell__history-edit"
                type="button"
                aria-label="编辑标题"
                @click="$emit('rename-history', conversation)"
              >
                <Pencil aria-hidden="true" />
              </button>
              <button
                class="ir-shell__history-action ir-shell__history-delete"
                type="button"
                aria-label="删除"
                @click="$emit('delete-history', conversation.conversationId)"
              >
                <Trash2 aria-hidden="true" />
              </button>
            </span>
          </li>
        </ul>
      </section>

      <footer class="ir-shell__user">
        <img v-if="userAvatar" class="ir-shell__user-avatar" :src="userAvatar" alt="" aria-hidden="true" />
        <span v-else class="ir-shell__user-fallback" aria-hidden="true">{{ userInitial }}</span>
        <span class="ir-shell__user-copy ir-shell__label">
          <small>当前用户</small>
          <strong>{{ username || '访客' }}</strong>
        </span>
      </footer>
    </aside>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { PanelLeftClose, PanelLeftOpen, Pencil, Plus, Trash2, X } from '@lucide/vue'

const ICON = {
  home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
  index: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 3v18h18"/><path d="M7 14l4-4 3 3 5-6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  line: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="5" cy="12" r="2.25"/><circle cx="19" cy="12" r="2.25"/><path d="M7.5 10.1c2.2-3.3 6.8-3.3 9 0"/><path d="M7.5 13.9c2.2 3.3 6.8 3.3 9 0"/></svg>',
  policy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h4" stroke-linecap="round"/></svg>',
  calculation: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 7h8M8 11h2m4 0h2M8 15h2m4 0h2" stroke-linecap="round"/></svg>',
  default: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 12h6M12 9v6" stroke-linecap="round"/></svg>',
}

const fallbackItems = [
  { key: 'home', path: '/home', label: '首页', icon: ICON.home },
  { key: 'index', path: '/index-map', label: '全国指数地图', icon: ICON.index },
  { key: 'line', path: '/tie-line', label: '联络线地图', icon: ICON.line },
  { key: 'policy', path: '/policy-market', label: '政策与市场', icon: ICON.policy },
]

const MENU_PRESENTATION = {
  '/home': { label: '朱雀星核', meta: '引擎' },
  '/index-map': { label: '朱雀寻龙图', meta: 'MAP' },
  '/policy-market': { label: '专业数据速查' },
}

const props = defineProps({
  items: { type: Array, default: null },
  active: { type: String, default: 'home' },
  history: { type: Array, default: () => [] },
  current: { type: [Number, String], default: null },
  username: { type: String, default: '访客' },
  userAvatar: { type: String, default: '' },
  collapsed: { type: Boolean, default: false },
  drawerOpen: { type: Boolean, default: false },
})

const emit = defineEmits([
  'nav',
  'new-chat',
  'open-history',
  'delete-history',
  'rename-history',
  'update:collapsed',
  'close-drawer',
])

function onToggle() {
  if (props.drawerOpen) emit('close-drawer')
  else emit('update:collapsed', !props.collapsed)
}

const navItems = computed(() => {
  const source = props.items?.length ? props.items : fallbackItems
  return source.map((item) => ({
    ...item,
    ...(MENU_PRESENTATION[item.path] || {}),
    icon: item.icon?.startsWith('<svg') ? item.icon : ICON[item.icon] || ICON.default,
  }))
})

const userInitial = computed(() => String(props.username || '访').trim().slice(0, 1) || '访')

function onNav(item) {
  if (item.disabled) return
  emit('nav', item.path || item.key)
}

function formatDateLabel(value) {
  if (!value) return ''
  const date = new Date(String(value).replace(' ', 'T'))
  if (Number.isNaN(date.getTime())) return ''
  const dayKey = (item) => `${item.getFullYear()}-${item.getMonth()}-${item.getDate()}`
  const today = new Date()
  if (dayKey(date) === dayKey(today)) return '今日'
  const yesterday = new Date(today)
  yesterday.setDate(today.getDate() - 1)
  if (dayKey(date) === dayKey(yesterday)) return '昨天'
  return `${date.getMonth() + 1}/${date.getDate()}`
}
</script>

<style scoped>
.ir-shell-wrap {
  position: relative;
  z-index: var(--xc-z-nav);
  width: calc(var(--xc-sidebar-w) + 24px);
  height: 100%;
  flex: 0 0 auto;
  transition: width var(--xc-dur-base) var(--xc-ease-out);
}

.ir-shell {
  width: var(--xc-sidebar-w);
  height: calc(100% - 24px);
  margin: 12px;
  padding: var(--xc-space-5);
  display: flex;
  flex-direction: column;
  min-height: 0;
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-sm);
  background: var(--xc-surface-raised);
  box-shadow: var(--xc-shadow-raised);
  backdrop-filter: blur(var(--xc-blur-lg));
  -webkit-backdrop-filter: blur(var(--xc-blur-lg));
  overflow: visible;
  transition: width var(--xc-dur-base) var(--xc-ease-out), padding var(--xc-dur-base) var(--xc-ease-out);
}

.ir-shell__brand {
  height: 48px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: var(--xc-space-3);
  min-width: 0;
}

.ir-shell__logo-frame {
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-sm);
  background: var(--xc-surface-control);
}

.ir-shell__logo {
  width: 18px;
  height: 30px;
  object-fit: contain;
}

.ir-shell__brand-copy {
  min-width: 0;
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  line-height: var(--xc-lh-snug);
  white-space: nowrap;
  overflow: hidden;
}

.ir-shell__brand-copy strong {
  overflow: hidden;
  color: var(--xc-text-strong);
  font-size: var(--xc-fs-md);
  font-weight: var(--xc-fw-semi);
  text-overflow: ellipsis;
}

.ir-shell__brand-copy small {
  overflow: hidden;
  color: var(--xc-text-mute);
  font-family: var(--xc-font-en);
  font-size: var(--xc-fs-3xs);
  letter-spacing: 0;
  text-overflow: ellipsis;
}

.ir-shell__toggle,
.ir-shell__history-action {
  border: 0;
  display: grid;
  place-items: center;
  background: transparent;
  color: var(--xc-text-mute);
  cursor: pointer;
}

.ir-shell__toggle {
  position: relative;
  width: 30px;
  height: 30px;
  flex: 0 0 auto;
  border-radius: var(--xc-radius-xs);
}

.ir-shell__toggle:hover,
.ir-shell__toggle:focus-visible,
.ir-shell__history-action:hover,
.ir-shell__history-action:focus-visible {
  color: var(--xc-text-strong);
  background: var(--xc-surface-frosted);
}

.ir-shell__toggle svg { width: 18px; height: 18px; }

.ir-shell__new {
  position: relative;
  width: 100%;
  height: 42px;
  min-height: 42px;
  margin-top: var(--xc-space-5);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--xc-space-3);
  border: 0;
  border-radius: var(--xc-radius-sm);
  background: var(--xc-grad-brand);
  box-shadow: var(--xc-glow-blue);
  color: var(--xc-text-strong);
  font-family: inherit;
  font-size: var(--xc-fs-sm);
  font-weight: var(--xc-fw-semi);
  cursor: pointer;
}

.ir-shell__new:hover { filter: brightness(1.08); }
.ir-shell__new-icon { width: 18px; height: 18px; }

.ir-shell__section-title,
.ir-shell__history-title {
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-2xs);
  font-weight: var(--xc-fw-medium);
}

.ir-shell__section-title {
  margin: var(--xc-space-7) var(--xc-space-4) var(--xc-space-2);
}

.ir-shell__nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ir-shell__nav-item {
  position: relative;
  width: 100%;
  min-height: 40px;
  padding: 0 var(--xc-space-4);
  display: flex;
  align-items: center;
  gap: var(--xc-space-4);
  border: 0;
  border-radius: var(--xc-radius-sm);
  background: transparent;
  color: var(--xc-text-soft);
  font-family: inherit;
  font-size: var(--xc-fs-sm);
  font-weight: var(--xc-fw-medium);
  text-align: left;
  cursor: pointer;
  transition: background var(--xc-dur-fast), color var(--xc-dur-fast);
}

.ir-shell__nav-item:hover:not(.is-disabled),
.ir-shell__nav-item:focus-visible:not(.is-disabled) {
  background: var(--xc-surface-frosted);
  color: var(--xc-text-strong);
}

.ir-shell__nav-item.is-active {
  background: var(--xc-surface-control);
  color: var(--xc-text-strong);
}

.ir-shell__nav-item.is-disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.ir-shell__nav-icon {
  width: 20px;
  height: 20px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
}

.ir-shell__nav-icon :deep(svg) { width: 20px; height: 20px; }

.ir-shell__nav-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ir-shell__nav-meta {
  margin-left: auto;
  flex: 0 0 auto;
  color: var(--xc-text-mute);
  font-family: var(--xc-font-en);
  font-size: var(--xc-fs-3xs);
  font-weight: var(--xc-fw-bold);
  letter-spacing: 0;
}

.ir-shell__history {
  min-height: 0;
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.ir-shell__divider {
  height: 1px;
  margin: var(--xc-space-5) var(--xc-space-1) var(--xc-space-4);
  flex: 0 0 auto;
  background: var(--xc-border-soft);
}

.ir-shell__history-title {
  padding: 0 var(--xc-space-4);
  margin-bottom: var(--xc-space-2);
}

.ir-shell__history-empty {
  margin: 0;
  padding: var(--xc-space-2) var(--xc-space-4);
  color: var(--xc-text-faint);
  font-size: var(--xc-fs-2xs);
}

.ir-shell__history-list {
  min-height: 0;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  list-style: none;
  overflow-y: auto;
}

.ir-shell__history-item {
  min-height: 36px;
  padding: 0 var(--xc-space-2) 0 var(--xc-space-4);
  display: flex;
  align-items: center;
  gap: var(--xc-space-2);
  border-radius: var(--xc-radius-sm);
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-xs);
  cursor: pointer;
  transition: background var(--xc-dur-fast), color var(--xc-dur-fast);
}

.ir-shell__history-item:hover,
.ir-shell__history-item:focus-visible,
.ir-shell__history-item.is-current {
  background: var(--xc-surface-frosted);
  color: var(--xc-text-strong);
}

.ir-shell__history-date {
  flex: 0 0 auto;
  color: var(--xc-text-faint);
  font-size: var(--xc-fs-3xs);
}

.ir-shell__history-name {
  min-width: 0;
  flex: 1 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ir-shell__history-actions {
  display: flex;
  flex: 0 0 auto;
}

.ir-shell__history-action {
  width: 24px;
  height: 24px;
  border-radius: var(--xc-radius-xs);
  opacity: 0;
  transition: opacity var(--xc-dur-fast), background var(--xc-dur-fast), color var(--xc-dur-fast);
}

.ir-shell__history-action svg { width: 14px; height: 14px; }
.ir-shell__history-item:hover .ir-shell__history-action,
.ir-shell__history-item:focus-within .ir-shell__history-action,
.ir-shell__history-item.is-current .ir-shell__history-action { opacity: 1; }
.ir-shell__history-edit:hover { color: var(--xc-accent-blue); }
.ir-shell__history-delete:hover { color: var(--xc-status-danger); }

.ir-shell__user {
  min-height: 48px;
  margin-top: var(--xc-space-4);
  padding: var(--xc-space-2);
  display: flex;
  align-items: center;
  gap: var(--xc-space-3);
  flex: 0 0 auto;
  border-top: 1px solid var(--xc-border-soft);
}

.ir-shell__user-avatar,
.ir-shell__user-fallback {
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  border-radius: 50%;
}

.ir-shell__user-avatar { object-fit: cover; }
.ir-shell__user-fallback {
  display: grid;
  place-items: center;
  background: var(--xc-grad-avatar);
  color: var(--xc-text-strong);
  font-size: var(--xc-fs-sm);
}

.ir-shell__user-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  line-height: var(--xc-lh-snug);
}

.ir-shell__user-copy small { color: var(--xc-text-mute); font-size: var(--xc-fs-3xs); }
.ir-shell__user-copy strong {
  overflow: hidden;
  color: var(--xc-text-strong);
  font-size: var(--xc-fs-xs);
  font-weight: var(--xc-fw-medium);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ir-shell button:focus-visible,
.ir-shell [role='button']:focus-visible {
  outline: 2px solid var(--xc-accent-blue);
  outline-offset: 2px;
}

.ir-shell-wrap.is-collapsed { width: 68px; }
.ir-shell-wrap.is-collapsed .ir-shell {
  width: 56px;
  margin-left: 6px;
  margin-right: 6px;
  padding: var(--xc-space-2);
  overflow: visible;
}
.ir-shell-wrap.is-collapsed .ir-shell__brand {
  height: auto;
  flex-direction: column;
  gap: var(--xc-space-2);
}
.ir-shell-wrap.is-collapsed .ir-shell__logo-frame { width: 38px; height: 38px; }
.ir-shell-wrap.is-collapsed .ir-shell__brand-copy,
.ir-shell-wrap.is-collapsed .ir-shell__label,
.ir-shell-wrap.is-collapsed .ir-shell__section-title,
.ir-shell-wrap.is-collapsed .ir-shell__history { display: none; }
.ir-shell-wrap.is-collapsed .ir-shell__new {
  width: 40px;
  margin-top: var(--xc-space-4);
  padding: 0;
  align-self: center;
}
.ir-shell-wrap.is-collapsed .ir-shell__nav {
  margin-top: var(--xc-space-5);
  gap: var(--xc-space-2);
}
.ir-shell-wrap.is-collapsed .ir-shell__nav-item {
  width: 40px;
  height: 40px;
  min-height: 40px;
  padding: 0;
  justify-content: center;
}
.ir-shell-wrap.is-collapsed .ir-shell__user {
  margin-top: auto;
  padding: var(--xc-space-2) 0 0;
  justify-content: center;
}

.ir-shell-wrap.is-collapsed [data-tip]::after {
  content: attr(data-tip);
  position: absolute;
  top: 50%;
  left: calc(100% + 10px);
  z-index: var(--xc-z-tooltip);
  padding: 5px 8px;
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-xs);
  background: var(--xc-surface-2);
  box-shadow: var(--xc-shadow-sm);
  color: var(--xc-text-strong);
  font-size: var(--xc-fs-2xs);
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transform: translateY(-50%);
  transition: opacity var(--xc-dur-fast);
}
.ir-shell-wrap.is-collapsed [data-tip]:hover::after,
.ir-shell-wrap.is-collapsed [data-tip]:focus-visible::after { opacity: 1; }

.ir-shell__drawer-scrim { display: none; }

@media (max-width: 767px) {
  .ir-shell-wrap,
  .ir-shell-wrap.is-collapsed {
    position: fixed;
    inset: 0;
    z-index: var(--xc-z-overlay);
    width: 0;
    pointer-events: none;
  }

  .ir-shell-wrap.is-drawer-open {
    width: 100%;
    pointer-events: auto;
  }

  .ir-shell__drawer-scrim {
    position: fixed;
    inset: 0;
    display: block;
    width: 100%;
    height: 100%;
    padding: 0;
    border: 0;
    background: var(--xc-surface-overlay);
  }

  .ir-shell-wrap .ir-shell,
  .ir-shell-wrap.is-collapsed .ir-shell {
    position: absolute;
    top: 0;
    left: 0;
    width: min(var(--xc-sidebar-w), calc(100vw - 48px));
    height: calc(100% - 16px);
    margin: 8px;
    padding: var(--xc-space-5);
    transform: translateX(calc(-100% - 16px));
    transition: transform var(--xc-dur-base) var(--xc-ease-out);
  }

  .ir-shell-wrap.is-drawer-open .ir-shell { transform: translateX(0); }
  .ir-shell-wrap.is-drawer-open .ir-shell__brand { height: 48px; flex-direction: row; }
  .ir-shell-wrap.is-drawer-open .ir-shell__logo-frame { width: 42px; height: 42px; }
  .ir-shell-wrap.is-drawer-open .ir-shell__brand-copy,
  .ir-shell-wrap.is-drawer-open .ir-shell__label,
  .ir-shell-wrap.is-drawer-open .ir-shell__section-title,
  .ir-shell-wrap.is-drawer-open .ir-shell__history { display: flex; }
  .ir-shell-wrap.is-drawer-open .ir-shell__section-title { display: block; }
  .ir-shell-wrap.is-drawer-open .ir-shell__new { width: 100%; margin-top: var(--xc-space-5); }
  .ir-shell-wrap.is-drawer-open .ir-shell__nav { margin-top: 0; gap: 2px; }
  .ir-shell-wrap.is-drawer-open .ir-shell__nav-item {
    width: 100%;
    min-height: 40px;
    padding: 0 var(--xc-space-4);
    justify-content: flex-start;
  }
  .ir-shell-wrap.is-drawer-open .ir-shell__user {
    margin-top: var(--xc-space-4);
    padding: var(--xc-space-2);
    justify-content: flex-start;
  }
}

@media (prefers-reduced-motion: reduce) {
  .ir-shell-wrap,
  .ir-shell,
  .ir-shell-wrap .ir-shell { transition: none; }
}
</style>

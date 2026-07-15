<template>
  <aside class="ir-sider" :class="{ 'ir-sider--collapsed': collapsed }">
    <!-- 品牌头 + 折叠按钮 -->
    <div class="ir-sider__head">
      <span class="ir-sider__logo" aria-hidden="true" v-html="logoSvg" />
      <span v-show="!collapsed" class="ir-sider__brand">朱雀投研智能体</span>
      <button
        class="ir-sider__toggle"
        :aria-label="collapsed ? '展开侧栏' : '折叠侧栏'"
        @click="$emit('toggle')"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">
          <rect x="3" y="4" width="18" height="16" rx="3" />
          <path d="M9 4v16" stroke-linecap="round" />
        </svg>
      </button>
    </div>

    <!-- 新建会话：青→紫渐变胶囊 -->
    <button class="ir-sider__new" @click="$emit('new-chat')">
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M8 3.33V12.67M3.33 8h9.34" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
      </svg>
      <span v-show="!collapsed">新建会话</span>
    </button>

    <!-- 导航项：投资分析工作台 -->
    <nav class="ir-sider__nav">
      <div v-show="!collapsed" class="ir-sider__group">投资分析工作台</div>
      <button
        v-for="it in items"
        :key="it.key"
        class="ir-sider__item"
        :class="{ 'is-active': it.key === active, 'is-disabled': it.disabled }"
        :disabled="it.disabled"
        :title="it.disabled ? it.label + '（后续 PRD）' : it.label"
        @click="onNav(it)"
      >
        <span class="ir-sider__icon" v-html="it.icon" />
        <span v-show="!collapsed" class="ir-sider__label">{{ it.label }}</span>
        <span v-if="it.disabled && !collapsed" class="ir-sider__soon">待建</span>
      </button>
    </nav>

    <!-- 历史会话：位于全部功能项之后 -->
    <div v-show="!collapsed" class="ir-sider__hist">
      <div class="ir-sider__divider" />
      <div class="ir-sider__hist-label">历史会话</div>
      <p v-if="!history.length" class="ir-sider__hist-empty">暂无历史，发起测算后自动记录</p>
      <ul v-else class="ir-sider__hist-list">
        <li
          v-for="h in history"
          :key="h.conversationId"
          class="ir-sider__hist-item"
          :class="{ 'is-current': h.conversationId === current }"
          :title="h.title || '未命名会话'"
          @click="$emit('open-history', h.conversationId)"
        >
          <span class="ir-sider__hist-title">{{ h.title || '未命名会话' }}</span>
          <span class="ir-sider__hist-actions" @click.stop>
            <button
              class="ir-sider__hist-more"
              aria-label="更多"
              @click.stop="toggleMenu(h.conversationId)"
            >
              <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <circle cx="5" cy="12" r="1.6" /><circle cx="12" cy="12" r="1.6" /><circle cx="19" cy="12" r="1.6" />
              </svg>
            </button>
            <div v-show="openMenu === h.conversationId" class="ir-sider__hist-menu">
              <button class="ir-sider__hist-del" @click.stop="onDelete(h.conversationId)">删除</button>
            </div>
          </span>
        </li>
      </ul>
    </div>
  </aside>
</template>

<script setup>
import { ref } from 'vue'
import logoSvg from '@/assets/logo.svg?raw'
defineProps({
  collapsed: { type: Boolean, default: false },
  active: { type: String, default: 'calc' },
  history: { type: Array, default: () => [] },
  current: { type: [Number, String], default: null },
})
const emit = defineEmits(['toggle', 'new-chat', 'nav', 'open-history', 'delete-history'])

const openMenu = ref(null)
function toggleMenu(id) {
  openMenu.value = openMenu.value === id ? null : id
}
function onDelete(id) {
  openMenu.value = null
  emit('delete-history', id)
}

// 图标用内联 SVG，避免引额外图标库依赖
const ICON = {
  calc: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"/></svg>',
  index: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 3v18h18"/><path d="M7 14l4-4 3 3 5-6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  line: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="6" cy="7" r="2"/><circle cx="18" cy="17" r="2"/><path d="M8 8l8 8" stroke-linecap="round"/></svg>',
  policy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h4" stroke-linecap="round"/></svg>',
}

// 三大模块命名以 PRD 为准（全国指数地图 / 联络线地图 / 政策与市场），后三占位
const items = [
  { key: 'calc', label: '测算对话', icon: ICON.calc, disabled: false },
  { key: 'index', label: '全国指数地图', icon: ICON.index, disabled: true },
  { key: 'line', label: '联络线地图', icon: ICON.line, disabled: true },
  { key: 'policy', label: '政策与市场', icon: ICON.policy, disabled: true },
]

function onNav(it) {
  if (it.disabled) return
  emit('nav', it.key)
}
</script>

<style scoped>
.ir-sider {
  width: 232px;
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--xc-space-3);
  padding: var(--xc-space-5) var(--xc-space-4);
  background: var(--xc-surface-glass);
  backdrop-filter: blur(var(--xc-blur-md));
  border-right: 1px solid var(--xc-border-soft);
  transition: width var(--xc-dur-base) var(--xc-ease-out);
}
.ir-sider--collapsed {
  width: 64px;
  align-items: stretch;
}

.ir-sider__head {
  display: flex;
  align-items: center;
  gap: var(--xc-space-3);
  height: 44px;
  padding-left: var(--xc-space-2);
}
.ir-sider__logo {
  width: 28px;
  height: 28px;
  flex: 0 0 auto;
  border-radius: var(--xc-radius-sm);
  --zra-icon-bg: rgba(255, 255, 255, 0.05);
  --zra-icon-border: rgba(255, 255, 255, 0.12);
  --zra-icon-mark: #f2f4f7;
  --zra-icon-accent: #e95a4f;
}
.ir-sider__logo :deep(svg) {
  display: block;
  width: 100%;
  height: 100%;
}
.ir-sider__brand {
  font-size: var(--xc-fs-lg);
  font-weight: var(--xc-fw-medium);
  color: var(--xc-text-strong);
  letter-spacing: 0.02em;
  flex: 1 1 auto;
}
.ir-sider__toggle {
  width: 28px;
  height: 28px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: var(--xc-radius-sm);
  background: transparent;
  color: var(--xc-text-soft);
  cursor: pointer;
  transition: background var(--xc-dur-fast), color var(--xc-dur-fast);
}
.ir-sider__toggle:hover { background: var(--xc-surface-frosted); color: var(--xc-text-strong); }
.ir-sider__toggle svg { width: 18px; height: 18px; }
/* 折叠态：头部竖排，logo 在上、折叠按钮在下且始终可见 */
.ir-sider--collapsed .ir-sider__head {
  flex-direction: column;
  height: auto;
  gap: var(--xc-space-3);
  padding-left: 0;
  align-items: center;
}

.ir-sider__new {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--xc-space-3);
  height: 42px;
  border: 0;
  border-radius: var(--xc-radius-md);
  background: var(--xc-grad-brand);
  color: #fff;
  font-size: var(--xc-fs-sm);
  font-weight: var(--xc-fw-medium);
  letter-spacing: 0.02em;
  cursor: pointer;
  box-shadow: var(--xc-glow-blue);
}
.ir-sider__new svg { width: 16px; height: 16px; flex: 0 0 auto; }

.ir-sider__nav {
  display: flex;
  flex-direction: column;
  gap: var(--xc-space-2);
  margin-top: var(--xc-space-4);
}
.ir-sider__group {
  font-size: var(--xc-fs-3xs);
  font-weight: var(--xc-fw-semi);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--xc-text-faint);
  padding: 0 var(--xc-space-4);
  margin-bottom: var(--xc-space-1);
}
.ir-sider__item {
  display: flex;
  align-items: center;
  gap: var(--xc-space-4);
  height: 42px;
  padding: 0 var(--xc-space-4);
  border: 0;
  border-radius: var(--xc-radius-md);
  background: transparent;
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-sm);
  cursor: pointer;
  transition: background var(--xc-dur-fast);
}
.ir-sider__item:hover:not(.is-disabled) { background: var(--xc-surface-frosted); }
.ir-sider__item.is-active {
  background: var(--xc-accent-blue-soft);
  color: var(--xc-text-strong);
}
.ir-sider__item.is-disabled { color: var(--xc-text-faint); cursor: not-allowed; }
.ir-sider__icon { width: 18px; height: 18px; flex: 0 0 auto; display: grid; place-items: center; }
.ir-sider__icon :deep(svg) { width: 18px; height: 18px; }
.ir-sider__label { flex: 1 1 auto; text-align: left; }
.ir-sider__soon {
  font-size: var(--xc-fs-3xs);
  color: var(--xc-text-faint);
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-xs);
  padding: 0 var(--xc-space-2);
}
.ir-sider--collapsed .ir-sider__item { justify-content: center; padding: 0; }
.ir-sider--collapsed .ir-sider__new { padding: 0; }

/* ---------- 历史会话 ---------- */
.ir-sider__hist {
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1 1 auto;
  margin-top: var(--xc-space-3);
}
.ir-sider__divider {
  height: 1px;
  background: var(--xc-border-soft);
  margin: var(--xc-space-2) var(--xc-space-2) var(--xc-space-3);
}
.ir-sider__hist-label {
  font-size: var(--xc-fs-xs);
  color: var(--xc-text-mute);
  padding: 0 var(--xc-space-4);
  margin-bottom: var(--xc-space-2);
}
.ir-sider__hist-empty {
  font-size: var(--xc-fs-2xs);
  color: var(--xc-text-faint);
  line-height: var(--xc-lh-loose);
  padding: 0 var(--xc-space-4);
  margin: 0;
}
.ir-sider__hist-list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.ir-sider__hist-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--xc-space-2);
  padding: var(--xc-space-2) var(--xc-space-4);
  border-radius: var(--xc-radius-sm);
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-sm);
  cursor: pointer;
  transition: background var(--xc-dur-fast), color var(--xc-dur-fast);
}
.ir-sider__hist-item:hover { background: var(--xc-surface-frosted); color: var(--xc-text-strong); }
.ir-sider__hist-item.is-current {
  background: var(--xc-accent-blue-soft);
  color: var(--xc-text-strong);
}
.ir-sider__hist-item.is-current .ir-sider__hist-more { opacity: 1; }
.ir-sider__hist-title {
  flex: 1 1 auto;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ir-sider__hist-actions { position: relative; flex: 0 0 auto; display: flex; }
.ir-sider__hist-more {
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: var(--xc-radius-xs);
  background: transparent;
  color: var(--xc-text-mute);
  cursor: pointer;
  opacity: 0;
  transition: opacity var(--xc-dur-fast), background var(--xc-dur-fast);
}
.ir-sider__hist-item:hover .ir-sider__hist-more { opacity: 1; }
.ir-sider__hist-more:hover { background: var(--xc-surface-2); color: var(--xc-text-strong); }
.ir-sider__hist-more svg { width: 15px; height: 15px; }
.ir-sider__hist-menu {
  position: absolute;
  top: 100%;
  right: 0;
  z-index: 20;
  margin-top: 2px;
  padding: var(--xc-space-1);
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-sm);
  background: var(--xc-surface-2);
  box-shadow: var(--xc-shadow-md);
}
.ir-sider__hist-del {
  display: block;
  width: 100%;
  padding: var(--xc-space-1) var(--xc-space-4);
  border: 0;
  border-radius: var(--xc-radius-xs);
  background: transparent;
  color: var(--xc-status-danger, #e95a4f);
  font-size: var(--xc-fs-sm);
  text-align: left;
  cursor: pointer;
}
.ir-sider__hist-del:hover { background: var(--xc-surface-frosted); }
</style>

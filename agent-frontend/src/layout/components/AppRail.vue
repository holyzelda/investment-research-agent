<template>
  <div class="ir-rail-wrap">
    <nav class="ir-rail" aria-label="模块导航">
      <button
        v-for="it in items"
        :key="it.key"
        type="button"
        class="ir-rail-btn"
        :class="{ 'is-active': it.key === active, 'is-disabled': it.disabled }"
        :data-tip="it.disabled ? it.label + '（待建）' : it.label"
        :aria-current="it.key === active ? 'page' : undefined"
        :aria-label="it.label"
        :disabled="it.disabled"
        @click="onClick(it)"
      >
        <span class="ir-rail-icon" v-html="it.icon" />
      </button>
    </nav>
  </div>
</template>

<script setup>
// 图标沿用历史会话侧栏原有的四套 SVG（首页/全国指数地图/联络线地图/政策与市场）
const ICON = {
  home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
  index: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 3v18h18"/><path d="M7 14l4-4 3 3 5-6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  line: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="6" cy="7" r="2"/><circle cx="18" cy="17" r="2"/><path d="M8 8l8 8" stroke-linecap="round"/></svg>',
  policy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h4" stroke-linecap="round"/></svg>',
}

// 待建三模块（全国指数地图/联络线地图/政策与市场）命名以 PRD 为准
const items = [
  { key: 'home', label: '首页', icon: ICON.home, disabled: false },
  { key: 'index', label: '全国指数地图', icon: ICON.index, disabled: true },
  { key: 'line', label: '联络线地图', icon: ICON.line, disabled: true },
  { key: 'policy', label: '政策与市场', icon: ICON.policy, disabled: true },
]

defineProps({
  active: { type: String, default: 'home' },
})
const emit = defineEmits(['nav'])

function onClick(it) {
  if (it.disabled) return
  emit('nav', it.key)
}
</script>

<style scoped>
.ir-rail-wrap {
  width: var(--xc-rail-w);
  flex: 0 0 auto;
  height: 100%;
  position: relative;
  z-index: var(--xc-z-nav);
}

/* 从顶部往下排列，与右侧历史侧栏（30px 上边距）的起始高度对齐，而非整体垂直居中 */
.ir-rail {
  position: absolute;
  left: 0;
  top: 30px;
  width: var(--xc-rail-w);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 右半圆按钮 — 半透明灰底 + blur，与 nx AppRail 视觉一致 */
.ir-rail-btn {
  position: relative;
  width: 46px;
  height: 46px;
  border-radius: 0 23px 23px 0;
  background: rgba(88, 88, 88, 0.5);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  display: grid;
  place-items: center;
  color: rgba(255, 255, 255, 0.85);
  cursor: pointer;
  border: 0;
  padding: 0;
  transition: background var(--xc-dur-fast) var(--xc-ease-out);
  flex-shrink: 0;
}
.ir-rail-btn:hover:not(.is-disabled) {
  background: rgba(120, 120, 120, 0.6);
}
.ir-rail-btn:focus-visible {
  outline: 2px solid var(--xc-accent-blue);
  outline-offset: 2px;
}

/* 激活：纯蓝底 + 白图标 + 蓝阴影 */
.ir-rail-btn.is-active {
  background: var(--xc-accent-blue);
  color: #fff;
  box-shadow: var(--xc-glow-blue);
}

.ir-rail-btn.is-disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.ir-rail-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
}
.ir-rail-icon :deep(svg) {
  width: 22px;
  height: 22px;
}

/* CSS-only tooltip — 右侧弹出 */
.ir-rail-btn[data-tip]:hover::after,
.ir-rail-btn[data-tip]:focus-visible::after {
  content: attr(data-tip);
  position: absolute;
  left: calc(100% + 12px);
  top: 50%;
  transform: translateY(-50%);
  background: var(--xc-surface-2);
  color: var(--xc-text-strong);
  font-size: var(--xc-fs-2xs);
  font-weight: var(--xc-fw-medium);
  padding: 4px 10px;
  border-radius: var(--xc-radius-sm);
  white-space: nowrap;
  box-shadow: var(--xc-shadow-md);
  pointer-events: none;
  z-index: var(--xc-z-tooltip);
  border: 1px solid var(--xc-border-soft);
  font-family: var(--xc-font-zh);
}
</style>

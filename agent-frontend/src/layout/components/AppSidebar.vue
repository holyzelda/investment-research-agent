<template>
  <!-- 固定定位上下文：折叠态悬浮预览以此为锚点展开，而非相对整页居中 -->
  <div v-if="!hidden" class="ir-sider-wrap" :style="{ width: isCollapsed ? '56px' : 'var(--xc-sidebar-w)' }">
    <aside
      class="ir-sider"
      data-testid="history-sidebar"
      :class="{ 'ir-sider--collapsed': isCollapsed, 'ir-sider--hover-expand': isHoverExpand }"
      @mouseenter="handleMouseEnter"
      @mouseleave="handleMouseLeave"
      @click="handleClick"
    >
      <div class="ir-sider__content" v-show="!isCollapsed || isHoverExpand">
        <!-- 品牌头 + 折叠按钮 -->
        <div class="ir-sider__head">
          <img class="ir-sider__logo" src="/brand-logo.svg" alt="" aria-hidden="true" />
          <span class="ir-sider__brand">朱雀投研智能体</span>
          <button
            v-if="canHide"
            class="ir-sider__hide"
            aria-label="隐藏历史会话栏"
            @click.stop="$emit('visibility-change', true)"
          >
            隐藏
          </button>
          <button
            class="ir-sider__toggle"
            aria-label="折叠侧栏"
            @click.stop="toggleCollapse"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">
              <rect x="3" y="4" width="18" height="16" rx="3" />
              <path d="M9 4v16" stroke-linecap="round" />
            </svg>
          </button>
        </div>

        <!-- 新建会话：青→紫渐变胶囊 -->
        <button class="ir-sider__new" @click.stop="$emit('new-chat')">
          <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M8 3.33V12.67M3.33 8h9.34" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
          </svg>
          <span>新建会话</span>
        </button>

        <!-- 历史会话 -->
        <div class="ir-sider__hist">
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
              @click.stop="$emit('open-history', h.conversationId)"
            >
              <span v-if="h.createdAt" class="ir-sider__hist-date xc-num">{{ formatDateLabel(h.createdAt) }}</span>
              <span class="ir-sider__hist-title">{{ h.title || '未命名会话' }}</span>
              <button
                class="ir-sider__hist-action ir-sider__hist-edit"
                aria-label="编辑标题"
                @click.stop="$emit('rename-history', h)"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="M12 20h9" />
                  <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
                </svg>
              </button>
              <button
                class="ir-sider__hist-action ir-sider__hist-delete"
                aria-label="删除"
                @click.stop="$emit('delete-history', h.conversationId)"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="M3 6h18" />
                  <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                  <path d="M10 11v6M14 11v6" />
                </svg>
              </button>
            </li>
          </ul>
        </div>
      </div>

      <!-- 折叠态：只保留一个折叠图标；悬浮时上方内容以浮层预览展开，移开即收起 -->
      <div v-show="isCollapsed && !isHoverExpand" class="ir-sider__collapsed-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">
          <rect x="3" y="4" width="18" height="16" rx="3" />
          <path d="M9 4v16" stroke-linecap="round" />
        </svg>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  history: { type: Array, default: () => [] },
  current: { type: [Number, String], default: null },
  hidden: { type: Boolean, default: false },
  canHide: { type: Boolean, default: false },
})
const emit = defineEmits(['new-chat', 'open-history', 'delete-history', 'rename-history', 'collapse-change', 'visibility-change'])

// 历史条目时间标签：今日 / 昨天 / M/D（对齐 trader fullscreen-chat 历史栏）
function formatDateLabel(value) {
  if (!value) return ''
  const d = new Date(String(value).replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return ''
  const key = (dt) => `${dt.getFullYear()}-${dt.getMonth()}-${dt.getDate()}`
  const today = new Date()
  if (key(d) === key(today)) return '今日'
  const yesterday = new Date(today)
  yesterday.setDate(today.getDate() - 1)
  if (key(d) === key(yesterday)) return '昨天'
  return `${d.getMonth() + 1}/${d.getDate()}`
}

// ---------- 折叠 / 悬浮预览 / 点击展开 ----------
// 对齐 trader（etrader-agent-nx）fullscreen-chat 历史栏的交互：
// 折叠后只剩一个圆形图标；鼠标悬浮短暂延迟后以浮层预览折叠前的内容，移开即收起；
// 只有点击（无论是折叠图标还是浮层内的折叠按钮）才会真正恢复为展开状态。
const isCollapsed = ref(false)
const isHoverExpand = ref(false)
let hoverTimer = null

watch(() => props.hidden, (hidden) => {
  if (!hidden) return
  clearTimeout(hoverTimer)
  isCollapsed.value = false
  isHoverExpand.value = false
})
onBeforeUnmount(() => clearTimeout(hoverTimer))

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
  isHoverExpand.value = false
  emit('collapse-change', isCollapsed.value)
}

function handleMouseEnter() {
  if (!isCollapsed.value) return
  clearTimeout(hoverTimer)
  hoverTimer = setTimeout(() => {
    isHoverExpand.value = true
  }, 200)
}

function handleMouseLeave() {
  if (!isCollapsed.value) return
  clearTimeout(hoverTimer)
  hoverTimer = setTimeout(() => {
    isHoverExpand.value = false
  }, 300)
}

function handleClick() {
  if (isCollapsed.value && !isHoverExpand.value) {
    isCollapsed.value = false
    emit('collapse-change', false)
  }
}
</script>

<style scoped>
/* 悬浮玻璃面板：与外层图标 rail 一起构成两层左侧导航，不再使用直角分割线。
   尺寸对齐 trader（etrader-agent-nx）fullscreen-chat 历史栏：300px 宽、上下 30px 浮空边距。 */
.ir-sider-wrap {
  position: relative;
  flex-shrink: 0;
  height: 100%;
  transition: width var(--xc-dur-base) var(--xc-ease-out);
}

.ir-sider {
  width: var(--xc-sidebar-w);
  height: calc(100% - 60px);
  margin: 30px 0;
  display: flex;
  flex-direction: column;
  gap: var(--xc-space-3);
  padding: var(--xc-space-5) var(--xc-space-4);
  /* 毛玻璃：深海军蓝半透 + 背景模糊，透出全屏底图的光色又压暗背景保证文字清晰，
     海军蓝调与底图和谐、不像灰底那样跳出成独立分区 */
  background: var(--xc-surface-sider);
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-xl);
  backdrop-filter: blur(var(--xc-blur-lg));
  -webkit-backdrop-filter: blur(var(--xc-blur-lg));
  overflow: hidden;
  transition: width var(--xc-dur-base) var(--xc-ease-out),
              height var(--xc-dur-base) var(--xc-ease-out),
              margin var(--xc-dur-base) var(--xc-ease-out),
              border-radius var(--xc-dur-base) var(--xc-ease-out);
}

/* 折叠态：收缩为单一圆形图标 */
.ir-sider--collapsed {
  width: 56px;
  height: 56px;
  margin: 100px 0 0;
  padding: 0;
  border-radius: var(--xc-radius-full);
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

/* 悬浮预览态：以浮层形式在折叠图标所在位置展开折叠前的内容，不影响主内容布局、也不居中于整页 */
.ir-sider--hover-expand {
  position: absolute;
  top: 0;
  left: 0;
  width: var(--xc-sidebar-w);
  height: calc(100% - 130px);
  margin: 100px 0 0;
  padding: var(--xc-space-5) var(--xc-space-4);
  border-radius: var(--xc-radius-xl);
  cursor: default;
  /* 悬浮预览是临时浮层，用不透明暗底保证内容可读（不同于常态透明历史栏） */
  background: var(--xc-surface-workspace);
  box-shadow: var(--xc-shadow-xl);
  z-index: var(--xc-z-overlay);
}

.ir-sider__content {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: var(--xc-space-3);
}

.ir-sider__collapsed-icon {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  color: var(--xc-text-strong);
}
.ir-sider__collapsed-icon svg { width: 22px; height: 22px; }

.ir-sider__head {
  display: flex;
  align-items: center;
  gap: var(--xc-space-3);
  height: 44px;
  padding-left: var(--xc-space-2);
  flex: 0 0 auto;
}
.ir-sider__logo {
  width: 21px;
  height: 34px;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  object-fit: contain;
}
.ir-sider__logo :deep(svg) {
  width: 100%;
  height: 100%;
  display: block;
}
.ir-sider__brand {
  font-size: var(--xc-fs-lg);
  font-weight: var(--xc-fw-medium);
  color: var(--xc-text-strong);
  letter-spacing: 0.02em;
  flex: 1 1 auto;
}
.ir-sider__hide {
  border: 0;
  background: transparent;
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-2xs);
  cursor: pointer;
  padding: 4px 6px;
}
.ir-sider__hide:hover,
.ir-sider__hide:focus-visible { color: var(--xc-text-strong); }
.ir-sider__hide:focus-visible { outline: 2px solid var(--xc-accent-blue); outline-offset: 2px; }

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

.ir-sider__new {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--xc-space-3);
  height: 42px;
  flex: 0 0 auto;
  border: 0;
  border-radius: var(--xc-radius-md);
  background: var(--xc-grad-brand);
  color: var(--xc-text-strong);
  font-size: var(--xc-fs-sm);
  font-weight: var(--xc-fw-medium);
  letter-spacing: 0.02em;
  cursor: pointer;
  box-shadow: var(--xc-glow-blue);
}
.ir-sider__new svg { width: 16px; height: 16px; flex: 0 0 auto; }

/* ---------- 历史会话 ---------- */
.ir-sider__hist {
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1 1 auto;
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
.ir-sider__hist-item.is-current .ir-sider__hist-action { opacity: 1; }
.ir-sider__hist-date {
  flex: 0 0 auto;
  font-size: var(--xc-fs-2xs);
  color: var(--xc-text-faint);
  user-select: none;
}
.ir-sider__hist-title {
  flex: 1 1 auto;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* 悬浮才出现的行内操作：编辑标题 / 删除，替代原三点菜单 */
.ir-sider__hist-action {
  flex: 0 0 auto;
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
  transition: opacity var(--xc-dur-fast), background var(--xc-dur-fast), color var(--xc-dur-fast);
}
.ir-sider__hist-action svg { width: 15px; height: 15px; }
.ir-sider__hist-item:hover .ir-sider__hist-action { opacity: 1; }
.ir-sider__hist-edit:hover { background: var(--xc-surface-2); color: var(--xc-accent-blue); }
.ir-sider__hist-delete:hover { background: var(--xc-surface-2); color: var(--xc-status-danger); }
</style>

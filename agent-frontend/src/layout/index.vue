<template>
  <div class="ir-layout xc-app">
    <div
      v-if="isWelcome"
      class="ir-layout__welcome-backdrop"
      :style="{ '--ir-welcome-bg': `url(${welcomeBackgroundSrc})` }"
      aria-hidden="true"
    />

    <div class="ir-layout__body" :class="{ 'is-report-view': isReportView }">
      <button
        v-if="!isReportView"
        ref="menuTrigger"
        class="ir-layout__menu-trigger"
        type="button"
        aria-label="打开应用菜单"
        :aria-expanded="drawerOpen"
        @click="openDrawer"
      >
        <Menu aria-hidden="true" />
      </button>

      <AppSidebar
        v-if="!isReportView"
        :items="navItems"
        :active="activeRail"
        :history="calc.history"
        :current="calc.conversationId"
        :username="session.nickname || session.username || '访客'"
        :user-avatar="userAvatar"
        :collapsed="sidebarCollapsed"
        :drawer-open="drawerOpen"
        @update:collapsed="sidebarCollapsed = $event"
        @close-drawer="closeDrawer"
        @nav="onNav"
        @new-chat="onNewChat"
        @open-history="onOpenHistory"
        @delete-history="onDeleteHistory"
        @rename-history="onRenameHistory"
      />

      <section class="ir-layout__content">
        <div v-if="isWelcome" class="ir-layout__welcome-metrics" aria-label="平台概览">
          <div v-for="metric in metrics" :key="metric.label" class="ir-layout__welcome-metric">
            <span class="ir-layout__welcome-metric-icon" v-html="metric.icon" aria-hidden="true" />
            <span class="ir-layout__welcome-metric-copy">
              <span class="ir-layout__welcome-metric-label">{{ metric.label }}</span>
              <strong class="ir-layout__welcome-metric-value xc-num">
                {{ metric.value }}<em>{{ metric.unit }}</em>
              </strong>
            </span>
          </div>
        </div>
        <main class="ir-layout__viewport">
          <router-view />
        </main>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Menu } from '@lucide/vue'
import { useSessionStore } from '@/store/modules/session'
import { useCalculationStore } from '@/store/modules/calculation'
import { usePermissionStore } from '@/store/modules/permission'
import AppSidebar from './components/AppSidebar.vue'
import userAvatar from '@/assets/user.png'
import welcomeBackgroundSrc from '@/assets/home-welcome-background.png'

const session = useSessionStore()
const calc = useCalculationStore()
const permission = usePermissionStore()
const route = useRoute()
const router = useRouter()

const navItems = computed(() => permission.railRoutes.length
  ? permission.railRoutes.map((item) => ({
      key: item.path.replace(/^\//, ''),
      path: item.path,
      label: item.title,
      icon: item.icon,
    }))
  : null)

const RAIL_TO_PATH = { home: '/home', index: '/index-map', line: '/tie-line', policy: '/policy-market' }
const PATH_TO_RAIL = { '/home': 'home', '/index-map': 'index', '/tie-line': 'line', '/policy-market': 'policy' }
const activeRail = computed(() => PATH_TO_RAIL[route.path] || route.path.replace(/^\//, ''))
const isReportView = computed(() => route.name === 'ReportDetail')
// 欢迎态：仅首页且无会话时铺满全屏背景并在顶栏展示平台指标；发首条消息 / 打开历史 / 切换页面后自动隐藏
const isWelcome = computed(() => route.name === 'Home' && calc.messages.length === 0)

const sidebarCollapsed = ref(Boolean(route.meta.collapseSidebar))
const drawerOpen = ref(false)
const menuTrigger = ref(null)
let previousBodyOverflow = ''
let homeSidebarMedia = null

const metrics = [
  {
    label: '累计测算次数', value: '1,286', unit: '次',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M3 12h4l2 6 4-14 2 8h6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  },
  {
    label: '测算项目数', value: '128', unit: '个',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="m12 3 8 4.5-8 4.5-8-4.5L12 3Z"/><path d="M4 7.5V16l8 5 8-5V7.5"/><path d="M12 12v9"/></svg>',
  },
  {
    label: '生成报告', value: '256', unit: '份',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5M9 13h6M9 17h6" stroke-linecap="round"/></svg>',
  },
  {
    label: '可调测算参数', value: '20+', unit: '项',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h7M15 18h5" stroke-linecap="round"/><circle cx="15" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="13" cy="18" r="2"/></svg>',
  },
  {
    label: '覆盖省份', value: '28', unit: '个',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></svg>',
  },
]

function syncHomeSidebarFromViewport() {
  if (route.name !== 'Home' || route.meta.collapseSidebar || !homeSidebarMedia) return
  sidebarCollapsed.value = homeSidebarMedia.matches
}

watch(() => route.fullPath, () => {
  closeDrawer(false)
  syncHomeSidebarFromViewport()
})

watch(drawerOpen, (open) => {
  if (typeof document === 'undefined') return
  if (open) {
    previousBodyOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = previousBodyOverflow
  }
})

async function goHome() {
  if (router.currentRoute.value.path !== '/home') await router.push('/home')
  closeDrawer(false)
}

async function onNewChat() {
  calc.resetConversation()
  await goHome()
}

async function onNav(target) {
  const path = RAIL_TO_PATH[target] || target
  if (path && router.currentRoute.value.path !== path) await router.push(path)
  closeDrawer(false)
}

async function onOpenHistory(conversationId) {
  try {
    await calc.openConversation(conversationId)
    await goHome()
  } catch (error) {
    ElMessage.error('打开历史会话失败，请稍后重试')
  }
}

async function onDeleteHistory(conversationId) {
  try {
    await ElMessageBox.confirm('删除后该会话将从列表移除，确定删除吗？', '删除历史会话', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch (error) {
    return
  }
  try {
    await calc.removeConversation(conversationId)
    ElMessage.success('已删除')
  } catch (error) {
    ElMessage.error('删除失败，请稍后重试')
  }
}

async function onRenameHistory(conversation) {
  const currentTitle = conversation.title || '未命名会话'
  let value
  try {
    ;({ value } = await ElMessageBox.prompt('请输入新的会话名称', '编辑会话标题', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputValue: currentTitle,
      inputValidator: (input) => (input && String(input).trim() ? true : '标题不能为空'),
    }))
  } catch (error) {
    return
  }
  const title = String(value || '').trim()
  if (!title || title === conversation.title) return
  try {
    await calc.renameConversation(conversation.conversationId, title)
    ElMessage.success('已修改')
  } catch (error) {
    ElMessage.error('修改失败，请稍后重试')
  }
}

async function openDrawer() {
  drawerOpen.value = true
  await nextTick()
  document.querySelector('.ir-shell-wrap.is-drawer-open .ir-shell__toggle')?.focus()
}

function closeDrawer(restoreFocus = true) {
  if (!drawerOpen.value) return
  drawerOpen.value = false
  if (restoreFocus) nextTick(() => menuTrigger.value?.focus())
}

function onDocumentKeydown(event) {
  if (!drawerOpen.value) return
  if (event.key === 'Escape') {
    event.preventDefault()
    closeDrawer()
    return
  }
  if (event.key !== 'Tab') return

  const shell = document.querySelector('.ir-shell-wrap.is-drawer-open .ir-shell')
  const focusable = shell
    ? [...shell.querySelectorAll('button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])')]
    : []
  if (!focusable.length) return
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

onMounted(() => {
  if (typeof window.matchMedia === 'function') {
    homeSidebarMedia = window.matchMedia('(max-width: 1439px)')
    syncHomeSidebarFromViewport()
    homeSidebarMedia.addEventListener?.('change', syncHomeSidebarFromViewport)
  }
  window.addEventListener('keydown', onDocumentKeydown)
  session.loadUserInfo()
  calc.loadHistory().catch(() => {})
})

onBeforeUnmount(() => {
  homeSidebarMedia?.removeEventListener?.('change', syncHomeSidebarFromViewport)
  window.removeEventListener('keydown', onDocumentKeydown)
  document.body.style.overflow = previousBodyOverflow
})
</script>

<style scoped>
.ir-layout {
  position: relative;
  isolation: isolate;
  height: 100vh;
  overflow: hidden;
  background: var(--xc-surface-workspace);
}

.ir-layout::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background: var(--xc-grad-atmosphere);
}

.ir-layout__welcome-backdrop {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background: var(--xc-grad-atmosphere), var(--ir-welcome-bg) center / cover no-repeat;
}

.ir-layout__welcome-backdrop::after {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, var(--xc-surface-workspace) 0%, transparent 72%),
    linear-gradient(0deg, var(--xc-surface-workspace) 0%, var(--xc-surface-workspace) 100%);
  opacity: 0.48;
}

.ir-layout__body {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
  display: flex;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.ir-layout__content {
  min-width: 0;
  min-height: 0;
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.ir-layout__body.is-report-view .ir-layout__content { width: 100%; }

.ir-layout__welcome-metrics {
  min-width: 0;
  min-height: 72px;
  margin: 12px var(--xc-gutter-x) 0;
  padding: var(--xc-space-4) var(--xc-space-6);
  display: flex;
  align-items: stretch;
  flex: 0 0 auto;
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-sm);
  background: var(--xc-surface-card);
  backdrop-filter: blur(var(--xc-blur-lg));
  -webkit-backdrop-filter: blur(var(--xc-blur-lg));
}

.ir-layout__welcome-metric {
  min-width: 0;
  flex: 1 1 0;
  padding: 0 var(--xc-space-5);
  display: flex;
  align-items: center;
  gap: var(--xc-space-4);
}

.ir-layout__welcome-metric + .ir-layout__welcome-metric { border-left: 1px solid var(--xc-border-card); }
.ir-layout__welcome-metric:first-child { padding-left: 0; }
.ir-layout__welcome-metric:last-child { padding-right: 0; }

.ir-layout__welcome-metric-icon {
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border-radius: var(--xc-radius-sm);
  background: var(--xc-surface-control);
  color: var(--xc-accent-blue);
}

.ir-layout__welcome-metric-icon :deep(svg) { width: 20px; height: 20px; }
.ir-layout__welcome-metric-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--xc-space-1);
  line-height: var(--xc-lh-tight);
}
.ir-layout__welcome-metric-label {
  overflow: hidden;
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-2xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ir-layout__welcome-metric-value {
  color: var(--xc-text-strong);
  font-size: var(--xc-fs-kpi-sm);
  font-weight: var(--xc-fw-bold);
}
.ir-layout__welcome-metric-value em {
  margin-left: 3px;
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-3xs);
  font-style: normal;
  font-weight: var(--xc-fw-regular);
}

.ir-layout__viewport {
  min-width: 0;
  min-height: 0;
  flex: 1 1 auto;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.ir-layout__viewport::-webkit-scrollbar { display: none; width: 0; height: 0; }

.ir-layout__menu-trigger {
  display: none;
  position: fixed;
  top: 12px;
  left: 12px;
  z-index: var(--xc-z-nav);
  width: 40px;
  height: 40px;
  place-items: center;
  padding: 0;
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-sm);
  background: var(--xc-surface-raised);
  box-shadow: var(--xc-shadow-sm);
  color: var(--xc-text-strong);
  cursor: pointer;
}
.ir-layout__menu-trigger svg { width: 20px; height: 20px; }
.ir-layout__menu-trigger:focus-visible { outline: 2px solid var(--xc-accent-blue); outline-offset: 2px; }

@media (max-width: 1050px) {
  .ir-layout__welcome-metric { padding: 0 var(--xc-space-2); gap: var(--xc-space-2); }
  .ir-layout__welcome-metric-icon { width: 32px; height: 32px; }
}

@media (max-width: 767px) {
  .ir-layout__menu-trigger { display: grid; }
  .ir-layout__welcome-metrics { margin-left: 64px; margin-right: var(--xc-space-3); }
}

@media (max-width: 640px) {
  .ir-layout__welcome-metrics { display: none; }
}
</style>

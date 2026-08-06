<template>
  <div class="ir-layout xc-app">
    <div
      v-if="isWelcome"
      class="ir-layout__welcome-backdrop"
      :style="{ '--ir-welcome-bg': `url(${welcomeBackgroundSrc})` }"
      aria-hidden="true"
    >
      <div class="ir-layout__welcome-image" />
    </div>

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
// 欢迎态：仅首页且无会话时挂载全屏场景背景；发首条消息 / 打开历史 / 切换页面后自动隐藏
const isWelcome = computed(() => route.name === 'Home' && calc.messages.length === 0)

const sidebarCollapsed = ref(Boolean(route.meta.collapseSidebar))
const drawerOpen = ref(false)
const menuTrigger = ref(null)
let previousBodyOverflow = ''
let homeSidebarMedia = null

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
  overflow: hidden;
  background:
    linear-gradient(90deg, rgba(10, 12, 18, 0.78) 0%, rgba(10, 12, 18, 0.38) 42%, rgba(10, 12, 18, 0.08) 76%),
    linear-gradient(0deg, rgba(10, 12, 18, 0.38), rgba(10, 12, 18, 0.08)),
    var(--ir-welcome-bg) center / cover no-repeat,
    var(--xc-surface-workspace);
}
/* 左侧可读遮罩：压暗主内容区，让场景集中在右侧，避免干扰标题与输入框 */
.ir-layout__welcome-backdrop::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  background:
    linear-gradient(90deg, var(--xc-surface-workspace) 0%, rgba(10, 12, 18, 0.66) 42%, transparent 74%),
    linear-gradient(0deg, var(--xc-surface-workspace) 0%, transparent 46%);
  opacity: 0.32;
}
.ir-layout__welcome-image {
  position: absolute;
  inset: 0;
  background: var(--ir-welcome-bg) center / cover no-repeat;
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
  .ir-layout__welcome-backdrop { opacity: 0.8; }
}

@media (max-width: 767px) {
  .ir-layout__menu-trigger { display: grid; }
}

@media (max-width: 640px) {
  .ir-layout__welcome-backdrop { opacity: 0.55; }
}
</style>

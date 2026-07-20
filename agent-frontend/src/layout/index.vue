<template>
  <div class="ir-layout xc-app">
    <!-- 顶栏融入背景、贯穿整行宽度，与下方 rail/侧栏对齐（对齐 trader AppShell 结构） -->
    <header class="ir-layout__topbar">
      <div class="ir-brand">
        <img class="ir-brand__mark" src="/brand-logo.svg" alt="" aria-hidden="true" />
        <span class="ir-brand__name">{{ title }}</span>
        <span class="ir-brand__sub">ZRA · 储能投资投研助手</span>
      </div>
      <div class="ir-layout__user">
        <img class="ir-layout__avatar" :src="userAvatar" alt="" aria-hidden="true" />
        <span>{{ session.username || '访客' }}</span>
      </div>
    </header>

    <div class="ir-layout__body" :class="{ 'is-sidebar-hidden': sidebarHidden }">
      <AppRail
        :items="navItems"
        :active="activeRail"
        @nav="onNav"
      />
      <button
        v-if="sidebarHidden"
        class="ir-layout__sidebar-open"
        aria-label="展开历史会话栏"
        @click="sidebarHidden = false"
      >
        历史会话
      </button>
      <AppSidebar
        :history="calc.history"
        :current="calc.conversationId"
        :hidden="sidebarHidden"
        :can-hide="Boolean(route.meta.collapseSidebar)"
        @visibility-change="sidebarHidden = $event"
        @new-chat="onNewChat"
        @open-history="onOpenHistory"
        @delete-history="onDeleteHistory"
      />
      <main class="ir-layout__viewport">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useSessionStore } from '@/store/modules/session'
import { useCalculationStore } from '@/store/modules/calculation'
import { usePermissionStore } from '@/store/modules/permission'
import AppRail from './components/AppRail.vue'
import AppSidebar from './components/AppSidebar.vue'
import userAvatar from '@/assets/user.png'

const title = computed(() => import.meta.env.VITE_APP_TITLE || '朱雀投研智能体')
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
const activeRail = computed(() => route.path.replace(/^\//, ''))
const sidebarHidden = ref(Boolean(route.meta.collapseSidebar))

watch(() => route.fullPath, () => {
  sidebarHidden.value = Boolean(route.meta.collapseSidebar)
})

function onNewChat() {
  calc.resetConversation()
}

function onNav(path) {
  if (path && router.currentRoute.value.path !== path) router.push(path)
}

async function onOpenHistory(conversationId) {
  try {
    await calc.openConversation(conversationId)
  } catch (e) {
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
  } catch (e) {
    return // 取消
  }
  try {
    await calc.removeConversation(conversationId)
    ElMessage.success('已删除')
  } catch (e) {
    ElMessage.error('删除失败，请稍后重试')
  }
}

onMounted(() => {
  // 进入/刷新只加载列表并保持欢迎页，用户手动打开历史会话
  session.loadUserInfo()
  calc.loadHistory().catch(() => {})
})
</script>

<style scoped>
.ir-layout {
  position: relative;
  isolation: isolate;
  display: flex;
  flex-direction: column;
  height: 100vh;
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
/* 顶栏融入背景，保持低调的品牌分量 */
.ir-layout__topbar {
  height: 64px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--xc-gutter-x);
  background: transparent;
}
.ir-brand {
  display: flex;
  align-items: center;
  gap: var(--xc-space-3);
}
.ir-brand__mark {
  width: 21px;
  height: 34px;
  flex: 0 0 auto;
  object-fit: contain;
}
.ir-brand__name {
  font-size: var(--xc-fs-h3);
  font-weight: var(--xc-fw-semi);
  color: var(--xc-text-strong);
}
.ir-brand__sub {
  font-size: var(--xc-fs-2xs);
  color: var(--xc-text-mute);
}
.ir-layout__user {
  display: flex;
  align-items: center;
  gap: var(--xc-space-2);
  padding: var(--xc-space-1) var(--xc-space-3) var(--xc-space-1) var(--xc-space-1);
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-full);
  background: var(--xc-surface-card);
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-sm);
}
.ir-layout__avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  object-fit: cover;
}

/* 顶栏之下：rail + 历史侧栏 + 主视图，三者共享同一起始高度 */
.ir-layout__body {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  position: relative;
  gap: var(--xc-gutter-x);
  overflow: hidden;
}
.ir-layout__body.is-sidebar-hidden {
  gap: 0;
}
.ir-layout__sidebar-open {
  position: absolute;
  left: var(--xc-rail-w);
  top: 30px;
  z-index: var(--xc-z-nav);
  border: 1px solid var(--xc-border-soft);
  border-left: 0;
  border-radius: 0 var(--xc-radius-sm) var(--xc-radius-sm) 0;
  background: var(--xc-surface-glass);
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-2xs);
  padding: 8px 10px;
  cursor: pointer;
}
.ir-layout__sidebar-open:hover,
.ir-layout__sidebar-open:focus-visible {
  color: var(--xc-text-strong);
  background: var(--xc-surface-frosted);
}
.ir-layout__sidebar-open:focus-visible {
  outline: 2px solid var(--xc-accent-blue);
  outline-offset: 2px;
}
.ir-layout__viewport {
  flex: 1 1 auto;
  min-width: 0;
  overflow-y: auto;
  overflow-x: hidden;
}
</style>

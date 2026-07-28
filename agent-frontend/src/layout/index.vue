<template>
  <div class="ir-layout xc-app">
    <!-- 首页欢迎态全屏背景：铺满整个外壳、位于顶栏与悬浮 rail/侧栏下层；图片打底、XC 氛围渐变叠加在上以保留设计语言色 -->
    <div
      v-if="isWelcome"
      class="ir-layout__welcome-backdrop"
      :style="{ '--ir-welcome-bg': `url(${welcomeBackgroundSrc})` }"
      aria-hidden="true"
    />
    <!-- 顶栏融入背景、贯穿整行宽度，与下方 rail/侧栏对齐（对齐 trader AppShell 结构） -->
    <header class="ir-layout__topbar">
      <div class="ir-brand">
        <img class="ir-brand__mark" src="/brand-logo.svg" alt="" aria-hidden="true" />
        <span class="ir-brand__name">{{ title }}</span>
        <span class="ir-brand__sub">ZRA · 储能投资投研助手</span>
      </div>
      <div v-if="isWelcome" class="ir-layout__welcome-metrics" aria-label="平台概览">
        <div v-for="metric in metrics" :key="metric.label" class="ir-layout__welcome-metric">
          <span class="ir-layout__welcome-metric-icon" v-html="metric.icon" aria-hidden="true" />
          <span class="ir-layout__welcome-metric-copy">
            <span class="ir-layout__welcome-metric-label">{{ metric.label }}</span>
            <strong class="ir-layout__welcome-metric-value xc-num">{{ metric.value }}<em>{{ metric.unit }}</em></strong>
          </span>
        </div>
      </div>
      <div class="ir-layout__user">
        <img class="ir-layout__avatar" :src="userAvatar" alt="" aria-hidden="true" />
        <span>{{ session.username || '访客' }}</span>
      </div>
    </header>

    <div class="ir-layout__body" :class="{ 'is-sidebar-hidden': sidebarHidden, 'is-report-view': isReportView }">
      <template v-if="!isReportView">
        <AppRail
          :items="navItems"
          :active="activeRail"
          @nav="onNav"
        />
        <button
          v-if="sidebarHidden && !route.meta.collapseSidebar"
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
          @rename-history="onRenameHistory"
        />
      </template>
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
import welcomeBackgroundSrc from '@/assets/home-welcome-background.png'

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
const RAIL_TO_PATH = { home: '/home', line: '/tie-line', policy: '/policy-market' }
const PATH_TO_RAIL = { '/home': 'home', '/tie-line': 'line', '/policy-market': 'policy' }
const activeRail = computed(() => PATH_TO_RAIL[route.path] || route.path.replace(/^\//, ''))
const isReportView = computed(() => route.name === 'ReportDetail')
// 欢迎态：仅首页且无会话时铺满全屏背景并在顶栏展示平台指标；发首条消息 / 打开历史 / 切换页面后自动隐藏
const isWelcome = computed(() => route.name === 'Home' && calc.messages.length === 0)
const sidebarHidden = ref(Boolean(route.meta.collapseSidebar))

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

watch(() => route.fullPath, () => {
  sidebarHidden.value = Boolean(route.meta.collapseSidebar)
})

function onNewChat() {
  calc.resetConversation()
}

function onNav(target) {
  const path = RAIL_TO_PATH[target] || target
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
  } catch (e) {
    return // 取消
  }
  const title = String(value || '').trim()
  if (!title || title === conversation.title) return
  try {
    await calc.renameConversation(conversation.conversationId, title)
    ElMessage.success('已修改')
  } catch (e) {
    ElMessage.error('修改失败，请稍后重试')
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
/* 首页欢迎态全屏背景层：图片打底(cover)，XC 氛围渐变作为首层叠加在上，保留青/紫设计语言色 */
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
/* 顶栏透明融入全屏背景，保持低调的品牌分量 */
.ir-layout__topbar {
  position: relative;
  z-index: 1;
  height: var(--xc-topbar-h);
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--xc-space-6);
  padding: 0 var(--xc-gutter-x);
  background: transparent;
}
.ir-layout__welcome-metrics {
  display: flex;
  flex: 1 1 auto;
  min-width: 0;
  max-width: 1120px;
  align-items: stretch;
  padding: var(--xc-space-4) var(--xc-space-6);
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-lg);
  background: var(--xc-surface-card);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}
.ir-layout__welcome-metric {
  display: flex;
  flex: 1 1 0;
  align-items: center;
  gap: var(--xc-space-4);
  min-width: 0;
  padding: 0 var(--xc-space-5);
}
.ir-layout__welcome-metric + .ir-layout__welcome-metric {
  border-left: 1px solid var(--xc-border-card);
}
.ir-layout__welcome-metric:first-child { padding-left: 0; }
.ir-layout__welcome-metric:last-child { padding-right: 0; }
.ir-layout__welcome-metric-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  width: 42px;
  height: 42px;
  border-radius: var(--xc-radius-lg);
  background: var(--xc-surface-control);
  color: var(--xc-accent-blue);
}
.ir-layout__welcome-metric-icon :deep(svg) { width: 22px; height: 22px; }
.ir-layout__welcome-metric-copy {
  display: flex;
  flex-direction: column;
  gap: var(--xc-space-1);
  min-width: 0;
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
  font-size: var(--xc-fs-xl);
  font-weight: var(--xc-fw-bold);
}
.ir-layout__welcome-metric-value em {
  margin-left: 3px;
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-2xs);
  font-style: normal;
  font-weight: var(--xc-fw-regular);
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

@media (max-width: 900px) {
  .ir-layout__welcome-metrics { max-width: none; }
  .ir-layout__welcome-metric { padding: 0 var(--xc-space-2); }
}
@media (max-width: 640px) {
  .ir-layout__welcome-metrics { display: none; }
}

/* 顶栏之下：rail + 历史侧栏 + 主视图，三者共享同一起始高度 */
.ir-layout__body {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  position: relative;
  z-index: 1;
  gap: var(--xc-gutter-x);
  overflow: hidden;
}
.ir-layout__body.is-sidebar-hidden {
  gap: 0;
}
.ir-layout__body.is-report-view {
  gap: 0;
}
.ir-layout__body.is-report-view .ir-layout__viewport {
  width: 100%;
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
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.ir-layout__viewport::-webkit-scrollbar {
  display: none;
  width: 0;
  height: 0;
}
</style>

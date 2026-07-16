<template>
  <div class="ir-layout xc-app">
    <!-- 顶栏融入背景、贯穿整行宽度，与下方 rail/侧栏对齐（对齐 trader AppShell 结构） -->
    <header class="ir-layout__topbar">
      <div class="ir-brand">
        <span class="ir-brand__name">{{ title }}</span>
        <span class="ir-brand__sub">ZRA · 储能投资投研助手</span>
      </div>
      <div class="ir-layout__user">
        <img class="ir-layout__avatar" :src="userAvatar" alt="" aria-hidden="true" />
        <span>{{ session.username || '访客' }}</span>
      </div>
    </header>

    <div class="ir-layout__body">
      <AppRail :active="'home'" @nav="onNav" />
      <AppSidebar
        :history="calc.history"
        :current="calc.conversationId"
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
import { computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useSessionStore } from '@/store/modules/session'
import { useCalculationStore } from '@/store/modules/calculation'
import AppRail from './components/AppRail.vue'
import AppSidebar from './components/AppSidebar.vue'
import userAvatar from '@/assets/user.png'

const title = computed(() => import.meta.env.VITE_APP_TITLE || '朱雀投研智能体')
const session = useSessionStore()
const calc = useCalculationStore()

function onNewChat() {
  calc.resetConversation()
}
function onNav() {
  // 后续三大模块（全国指数地图/联络线地图/政策与市场）待各自 PRD；当前仅测算首页可用
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
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--xc-surface-base);
}
/* 顶栏融入背景，不再用横线分割 */
.ir-layout__topbar {
  height: 56px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--xc-gutter-x);
  background: var(--xc-surface-base);
}
.ir-brand {
  display: flex;
  align-items: baseline;
  gap: var(--xc-space-3);
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
  gap: var(--xc-gutter-x);
  overflow: hidden;
}
.ir-layout__viewport {
  flex: 1 1 auto;
  min-width: 0;
  overflow-y: auto;
  overflow-x: hidden;
}
</style>

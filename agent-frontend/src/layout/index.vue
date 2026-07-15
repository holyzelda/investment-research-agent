<template>
  <div class="ir-layout xc-app">
    <AppSidebar
      :collapsed="collapsed"
      :active="'calc'"
      :history="calc.history"
      :current="calc.conversationId"
      @toggle="collapsed = !collapsed"
      @new-chat="onNewChat"
      @nav="onNav"
      @open-history="onOpenHistory"
      @delete-history="onDeleteHistory"
    />
    <div class="ir-layout__main">
      <header class="ir-layout__topbar">
        <div class="ir-brand">
          <span class="ir-brand__name">{{ title }}</span>
          <span class="ir-brand__sub">ZRA · 储能投资投研助手</span>
        </div>
        <div class="ir-layout__user">
          <el-icon><UserFilled /></el-icon>
          <span>{{ session.username || '访客' }}</span>
        </div>
      </header>
      <main class="ir-layout__body">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UserFilled } from '@element-plus/icons-vue'
import { useSessionStore } from '@/store/modules/session'
import { useCalculationStore } from '@/store/modules/calculation'
import AppSidebar from './components/AppSidebar.vue'

const title = computed(() => import.meta.env.VITE_APP_TITLE || '朱雀投研智能体')
const session = useSessionStore()
const calc = useCalculationStore()
const collapsed = ref(false)

function onNewChat() {
  calc.resetConversation()
}
function onNav() {
  // 后续三大模块（全国指数地图/联络线地图/政策与市场）待各自 PRD；当前仅测算对话可用
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
  height: 100vh;
  background: var(--xc-surface-base);
}
.ir-layout__main {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.ir-layout__topbar {
  height: 56px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--xc-gutter-x);
  border-bottom: 1px solid var(--xc-border-soft);
  background: var(--xc-surface-2);
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
.ir-layout__body {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}
</style>

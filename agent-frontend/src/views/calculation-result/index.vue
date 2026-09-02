<template>
  <!-- 台账（管理员）跳转的纯只读测算结果页：只按 taskId 展示该版本，不提供任何写操作。 -->
  <div class="ir-readonly-page">
    <div v-if="loading" class="ir-readonly-page__centered">
      <div class="ir-readonly-page__spinner" />
      <p class="ir-readonly-page__hint">正在加载测算结果…</p>
    </div>

    <div v-else-if="error" class="ir-readonly-page__centered">
      <h1 class="ir-readonly-page__title">无法查看</h1>
      <p class="ir-readonly-page__desc">{{ error }}</p>
    </div>

    <div v-else class="ir-readonly-page__content">
      <header class="ir-readonly-page__head">
        <h1>{{ title || '测算结果' }}</h1>
        <span v-if="version">版本 {{ version }}</span>
      </header>
      <ReadonlyResultCard
        :basic-info="result?.basicInfo"
        :financial="result?.financial"
        :advanced="result?.advanced"
        :warnings="result?.warnings || []"
        :version="version"
        :calculated-at="calculatedAt"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getCalculationResult, getConversation } from '@/api/calc'
import ReadonlyResultCard from '@/components/ReadonlyResultCard.vue'

const route = useRoute()
const loading = ref(true)
const error = ref('')
const title = ref('')
const version = ref('')
const calculatedAt = ref('')
const result = ref(null)

async function loadResult() {
  const { conversationId, taskId } = route.params
  if (!conversationId || !taskId) {
    error.value = '链接缺少会话或版本标识'
    loading.value = false
    return
  }
  try {
    const conversationResponse = await getConversation(conversationId)
    const detail = conversationResponse?.data || {}
    // 一条台账记录对应一个版本，这里只认路由上的 taskId，不回退到最新版本。
    const target = (detail.versions || []).find(
      (item) => String(item.taskId) === String(taskId),
    )
    if (!target) {
      error.value = '未找到该测算版本的结果'
      return
    }
    const resultResponse = await getCalculationResult(taskId)
    const payload = resultResponse?.data || {}
    title.value = detail.title || ''
    version.value = target.version || payload.version || ''
    calculatedAt.value = payload.calculatedAt || target.calculatedAt || ''
    result.value = payload
  } catch (err) {
    error.value = err?.response?.status === 404
      ? '测算记录不存在或无权查看'
      : err?.response?.data?.msg || err?.message || '加载测算结果失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

onMounted(loadResult)
</script>

<style scoped>
.ir-readonly-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: #0a0e1a;
}
.ir-readonly-page__centered {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: var(--xc-space-4);
  padding: var(--xc-space-8);
  max-width: 480px;
  text-align: center;
}
.ir-readonly-page__title {
  margin: 0;
  color: var(--xc-status-danger);
  font-size: var(--xc-fs-h2);
  font-weight: var(--xc-fw-bold);
}
.ir-readonly-page__desc {
  margin: 0;
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-sm);
}
.ir-readonly-page__hint { color: var(--xc-text-mute); font-size: var(--xc-fs-sm); }
.ir-readonly-page__spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--xc-border-soft);
  border-top-color: var(--xc-accent-blue);
  border-radius: 50%;
  animation: ir-readonly-spin 0.8s linear infinite;
}
@keyframes ir-readonly-spin { to { transform: rotate(360deg); } }
.ir-readonly-page__content {
  width: 100%;
  max-width: 860px;
  padding: var(--xc-space-7) var(--xc-space-5);
  display: flex;
  flex-direction: column;
  gap: var(--xc-space-5);
}
.ir-readonly-page__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--xc-space-4);
}
.ir-readonly-page__head h1 {
  margin: 0;
  color: var(--xc-text-strong);
  font-size: var(--xc-fs-h3);
  font-weight: var(--xc-fw-semi);
}
.ir-readonly-page__head span { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
@media (max-width: 768px) {
  .ir-readonly-page__content { padding: var(--xc-space-4); }
}
</style>

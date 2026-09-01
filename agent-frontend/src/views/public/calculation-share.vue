<template>
  <div class="ir-share-page">
    <!-- 加载态 -->
    <div v-if="loading" class="ir-share-page__centered">
      <div class="ir-share-page__spinner" />
      <p class="ir-share-page__hint">正在加载分享内容…</p>
    </div>

    <!-- 错误态 -->
    <div v-else-if="error" class="ir-share-page__centered">
      <h1 class="ir-share-page__title ir-share-page__title--error">无法查看</h1>
      <p class="ir-share-page__desc">{{ error }}</p>
    </div>

    <!-- 已过期 / 已撤销 -->
    <div v-else-if="share.status === 'expired'" class="ir-share-page__centered">
      <h1 class="ir-share-page__title">分享链接已过期</h1>
      <p class="ir-share-page__desc">该测算结果分享链接已超过有效期，请联系分享者重新分享。</p>
    </div>
    <div v-else-if="share.status === 'revoked'" class="ir-share-page__centered">
      <h1 class="ir-share-page__title">分享已撤销</h1>
      <p class="ir-share-page__desc">分享者已撤销此分享链接，无法继续查看。</p>
    </div>
    <div v-else-if="share.status === 'not_found'" class="ir-share-page__centered">
      <h1 class="ir-share-page__title">分享不存在</h1>
      <p class="ir-share-page__desc">该分享链接无效，请检查链接是否正确。</p>
    </div>

    <!-- 有效分享内容 -->
    <div v-else-if="share.status === 'active'" class="ir-share-page__content">
      <ReadonlyResultCard
        :basic-info="share.basicInfo"
        :financial="share.financial"
        :advanced="share.advanced"
        :warnings="share.warnings || []"
        :version="share.version"
        :calculated-at="share.calculatedAt"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getPublicShare } from '@/api/calc'
import ReadonlyResultCard from '@/components/ReadonlyResultCard.vue'

const route = useRoute()
const loading = ref(true)
const error = ref('')
const share = ref({})

// 加载分享数据
async function loadShare() {
  const shareCode = route.params.shareCode
  if (!shareCode) {
    error.value = '分享链接无效'
    loading.value = false
    return
  }
  loading.value = true
  error.value = ''
  try {
    const response = await getPublicShare(shareCode)
    const data = response?.data?.data || response?.data
    if (!data?.status) throw new Error('分享接口未返回有效内容')
    share.value = data
  } catch (err) {
    const status = err?.response?.status
    if (status === 404) {
      share.value = { status: 'not_found' }
    } else {
      error.value = err?.response?.data?.msg || err?.message || '加载分享内容失败，请稍后重试'
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadShare()
})
</script>

<style scoped>
/* ── 页面容器 ── */
.ir-share-page {
  min-height: 100vh;
  background: #0a0e1a;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

/* ── 居中状态 ── */
.ir-share-page__centered {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: var(--xc-space-4);
  padding: var(--xc-space-8);
  text-align: center;
  max-width: 480px;
}
.ir-share-page__title {
  margin: 0;
  font-size: var(--xc-fs-h2);
  color: var(--xc-text-strong);
  font-weight: var(--xc-fw-bold);
}
.ir-share-page__title--error {
  color: var(--xc-status-danger);
}
.ir-share-page__desc {
  margin: 0;
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-sm);
  line-height: var(--xc-lh-normal);
}
.ir-share-page__hint {
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-sm);
}
.ir-share-page__spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--xc-border-soft);
  border-top-color: var(--xc-accent-blue);
  border-radius: 50%;
  animation: ir-spin 0.8s linear infinite;
}
@keyframes ir-spin { to { transform: rotate(360deg); } }

/* ── 内容区 ── */
.ir-share-page__content {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 860px;
  padding: var(--xc-space-7) var(--xc-space-5);
  display: flex;
  flex-direction: column;
  gap: var(--xc-space-5);
}

/* ── 响应式 ── */
@media (max-width: 768px) {
  .ir-share-page__content { padding: var(--xc-space-4); }
}
@media (max-width: 480px) {
  .ir-share-page__content { padding: var(--xc-space-3); }
}
</style>

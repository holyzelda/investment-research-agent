<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    @closed="handleClosed"
    title="分享测算结果"
    width="520px"
    :close-on-click-modal="false"
    destroy-on-close
    class="ir-share-dialog"
  >
    <div class="ir-share" v-loading="loading" element-loading-text="加载中…">
      <div class="ir-share__intro">
        <span class="ir-share__intro-icon" aria-hidden="true">
          <Link2 :size="20" :stroke-width="1.7" />
        </span>
        <div>
          <strong>{{ version || '当前版本' }}</strong>
          <span>仅展示本次测算结果，不包含项目会话和其他版本。</span>
        </div>
      </div>

      <!-- 未分享状态：创建分享 -->
      <template v-if="!hasAnyShare && !loading">
        <div class="ir-share__duration">
          <div class="ir-share__duration-copy">
            <label class="ir-share__duration-label">链接有效期</label>
            <span>到期后访问者将无法继续查看</span>
          </div>
          <el-radio-group v-model="duration" class="ir-share__radio-group">
            <el-radio-button :value="7">7 天</el-radio-button>
            <el-radio-button :value="14">14 天</el-radio-button>
            <el-radio-button :value="30">30 天</el-radio-button>
          </el-radio-group>
        </div>
        <div class="ir-share__footer">
          <span class="ir-share__security"><ShieldCheck :size="15" /> 获得链接的用户可访问</span>
          <el-button
            type="primary"
            :loading="creating"
            @click="handleCreate"
            class="ir-share__primary-btn"
          >
            <Link2 v-if="!creating" :size="16" />
            {{ creating ? '生成中…' : '生成分享链接' }}
          </el-button>
        </div>
      </template>

      <!-- 已分享有效状态：展示链接与操作 -->
      <template v-else-if="activeShare">
        <div class="ir-share__status">
          <span class="ir-share__status-icon is-active"><Check :size="16" :stroke-width="2" /></span>
          <span><strong>分享已生效</strong>，可直接复制链接发送</span>
        </div>
        <div class="ir-share__link-box">
          <input
            ref="linkInput"
            :value="shareUrl"
            readonly
            class="ir-share__link-input"
            @focus="$event.target.select()"
          />
          <el-button
            size="small"
            :class="['ir-share__copy-btn', { 'is-copied': copied }]"
            @click="copyLink"
          >
            <Check v-if="copied" :size="15" />
            <Copy v-else :size="15" />
            {{ copied ? '已复制' : '复制链接' }}
          </el-button>
        </div>
        <div class="ir-share__meta">
          <span>有效期至 <strong class="xc-num">{{ formatExpiry(activeShare.expiresAt) }}</strong></span>
          <span>{{ activeShare.durationDays }} 天</span>
        </div>
        <div class="ir-share__footer ir-share__footer--active">
          <span class="ir-share__security"><ShieldCheck :size="15" /> 公开链接，请谨慎转发</span>
          <el-button
            type="danger"
            plain
            size="small"
            :loading="revoking"
            @click="handleRevoke"
            class="ir-share__revoke-btn"
          >
            {{ revoking ? '撤销中…' : '撤销分享' }}
          </el-button>
        </div>
      </template>

      <!-- 已过期 / 已撤销，可重新创建 -->
      <template v-else>
        <div class="ir-share__status">
          <span class="ir-share__status-icon is-expired"><RotateCcw :size="15" /></span>
          <span><strong>{{ previousShare?.revokedAt ? '分享已撤销' : '分享链接已过期' }}</strong></span>
        </div>
        <div class="ir-share__duration">
          <div class="ir-share__duration-copy">
            <label class="ir-share__duration-label">新链接有效期</label>
            <span>原链接不会恢复访问</span>
          </div>
          <el-radio-group v-model="duration" class="ir-share__radio-group">
            <el-radio-button :value="7">7 天</el-radio-button>
            <el-radio-button :value="14">14 天</el-radio-button>
            <el-radio-button :value="30">30 天</el-radio-button>
          </el-radio-group>
        </div>
        <div class="ir-share__footer">
          <span />
          <el-button
            type="primary"
            :loading="creating"
            @click="handleCreate"
            class="ir-share__primary-btn"
          >
            <RotateCcw v-if="!creating" :size="16" />
            {{ creating ? '生成中…' : '重新生成分享链接' }}
          </el-button>
        </div>
      </template>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, Copy, Link2, RotateCcw, ShieldCheck } from '@lucide/vue'
import { createShare, listShares, revokeShare } from '@/api/calc'

const props = defineProps({
  visible: { type: Boolean, default: false },
  conversationId: { type: String, default: '' },
  taskId: { type: [Number, String], default: null },
  version: { type: String, default: '' },
})
const emit = defineEmits(['update:visible'])

const loading = ref(false)
const creating = ref(false)
const revoking = ref(false)
const copied = ref(false)
const duration = ref(7)
const shares = ref([])
const linkInput = ref(null)

const hasAnyShare = computed(() => shares.value.length > 0)

const activeShare = computed(() => {
  const now = Date.now()
  return shares.value.find((s) => !s.revokedAt && new Date(s.expiresAt).getTime() > now) || null
})

const previousShare = computed(() => {
  return shares.value.length > 0 ? shares.value[shares.value.length - 1] : null
})

const shareUrl = computed(() => {
  const path = activeShare.value?.shareUrl
  if (path) return new URL(path, window.location.origin).toString()
  if (!activeShare.value?.shareCode) return ''
  return new URL(`/investment/public/calculation-shares/${activeShare.value.shareCode}`, window.location.origin).toString()
})

watch(
  () => props.visible,
  (open) => {
    if (open && props.taskId) loadShares()
  },
  { immediate: true },
)

async function loadShares() {
  if (!props.conversationId || !props.taskId) return
  loading.value = true
  try {
    const response = await listShares(props.conversationId, props.taskId)
    shares.value = response.data || []
  } catch {
    shares.value = []
  } finally {
    loading.value = false
  }
}

function handleClosed() {
  shares.value = []
  duration.value = 7
  copied.value = false
}

async function handleCreate() {
  if (!props.taskId) return
  creating.value = true
  try {
    const response = await createShare(Number(props.taskId), duration.value)
    const data = response?.data?.data || response?.data || {}
    if (!data.shareCode) throw new Error('分享接口未返回分享码')
    shares.value = [
      {
        id: data.shareId,
        shareCode: data.shareCode,
        shareUrl: data.shareUrl,
        durationDays: data.durationDays,
        expiresAt: data.expiresAt,
        revokedAt: null,
        createdAt: data.createdAt,
      },
    ]
    ElMessage.success('分享链接已生成')
  } catch (error) {
    ElMessage.error(error?.response?.data?.msg || '生成分享链接失败，请稍后重试')
  } finally {
    creating.value = false
  }
}

async function handleRevoke() {
  if (!activeShare.value) return
  revoking.value = true
  try {
    await revokeShare(activeShare.value.id, Number(props.taskId))
    const share = shares.value.find((s) => s.id === activeShare.value.id)
    if (share) share.revokedAt = new Date().toISOString()
    ElMessage.success('分享已撤销')
  } catch (error) {
    ElMessage.error(error?.response?.data?.msg || '撤销分享失败，请稍后重试')
  } finally {
    revoking.value = false
  }
}

async function copyLink() {
  try {
    await navigator.clipboard.writeText(shareUrl.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    const input = linkInput.value
    if (input) {
      input.select()
      try {
        document.execCommand('copy')
        copied.value = true
        setTimeout(() => { copied.value = false }, 2000)
      } catch {
        ElMessage.warning('复制失败，请手动选中链接复制')
      }
    }
  }
}

function formatExpiry(iso) {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}
</script>

<style scoped>
:global(.ir-share-dialog) {
  max-width: calc(100vw - 32px);
  overflow: hidden;
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-md);
  background: var(--xc-surface-raised);
  box-shadow: var(--xc-shadow-xl);
}
:global(.ir-share-dialog .el-dialog__header) {
  margin: 0;
  padding: var(--xc-space-6) var(--xc-space-7) var(--xc-space-5);
  border-bottom: 1px solid var(--xc-border-soft);
}
:global(.ir-share-dialog .el-dialog__title) {
  color: var(--xc-text-strong);
  font-size: var(--xc-fs-lg);
  font-weight: var(--xc-fw-semi);
}
:global(.ir-share-dialog .el-dialog__headerbtn) { top: 10px; right: 12px; }
:global(.ir-share-dialog .el-dialog__close) { color: var(--xc-text-soft); }
:global(.ir-share-dialog .el-dialog__body) { padding: var(--xc-space-6) var(--xc-space-7) var(--xc-space-7); }
.ir-share {
  min-height: 220px;
  display: flex;
  flex-direction: column;
  gap: var(--xc-space-6);
}
.ir-share__intro {
  display: flex;
  align-items: center;
  gap: var(--xc-space-4);
  padding-bottom: var(--xc-space-6);
  border-bottom: 1px solid var(--xc-border-soft);
}
.ir-share__intro-icon {
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  display: grid;
  place-items: center;
  border-radius: var(--xc-radius-sm);
  background: var(--xc-status-info-soft);
  color: var(--xc-accent-blue);
}
.ir-share__intro div { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.ir-share__intro strong { color: var(--xc-text-strong); font-size: var(--xc-fs-sm); }
.ir-share__intro span:not(.ir-share__intro-icon) {
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-2xs);
  line-height: var(--xc-lh-normal);
}
.ir-share__duration {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--xc-space-6);
}
.ir-share__duration-copy { display: flex; flex-direction: column; gap: 3px; }
.ir-share__duration-label {
  color: var(--xc-text-default);
  font-size: var(--xc-fs-sm);
  font-weight: var(--xc-fw-medium);
}
.ir-share__duration-copy span { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.ir-share__radio-group {
  --el-radio-button-checked-bg-color: var(--xc-accent-blue);
  --el-radio-button-checked-border-color: var(--xc-accent-blue);
  --el-radio-button-checked-text-color: #fff;
}
.ir-share__primary-btn { min-width: 142px; }
.ir-share__primary-btn :deep(span),
.ir-share__copy-btn :deep(span) { display: inline-flex; align-items: center; gap: var(--xc-space-2); }
.ir-share__status {
  display: flex;
  align-items: center;
  gap: var(--xc-space-3);
  font-size: var(--xc-fs-sm);
  color: var(--xc-text-soft);
}
.ir-share__status strong { color: var(--xc-text-strong); }
.ir-share__status-icon {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: var(--xc-radius-full);
}
.ir-share__status-icon.is-active {
  background: var(--xc-status-ok-soft);
  color: var(--xc-status-ok);
}
.ir-share__status-icon.is-expired {
  background: var(--xc-surface-control);
  color: var(--xc-text-soft);
}
.ir-share__link-box {
  display: flex;
  gap: 0;
  align-items: center;
  padding: var(--xc-space-2);
  border: 1px solid var(--xc-border-accent);
  border-radius: var(--xc-radius-sm);
  background: var(--xc-surface-control);
}
.ir-share__link-input {
  flex: 1;
  min-width: 0;
  height: 34px;
  padding: 0 var(--xc-space-3);
  border: 0;
  background: transparent;
  color: var(--xc-text-strong);
  font-family: var(--xc-font-mono);
  font-size: var(--xc-fs-xs);
  outline: none;
  cursor: default;
}
.ir-share__link-input:focus-visible { outline: 2px solid var(--xc-accent-blue); outline-offset: -2px; }
.ir-share__copy-btn { flex-shrink: 0; }
.ir-share__copy-btn.is-copied {
  color: var(--xc-status-ok);
  border-color: var(--xc-status-ok);
}
.ir-share__meta {
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-2xs);
  display: flex;
  justify-content: space-between;
  gap: var(--xc-space-4);
}
.ir-share__meta strong { color: var(--xc-text-soft); font-weight: var(--xc-fw-medium); }
.ir-share__footer {
  min-height: 48px;
  margin-top: auto;
  padding-top: var(--xc-space-5);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--xc-space-4);
  border-top: 1px solid var(--xc-border-soft);
}
.ir-share__security { display: inline-flex; align-items: center; gap: var(--xc-space-2); color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.ir-share__footer--active { padding-top: var(--xc-space-4); }

@media (max-width: 560px) {
  :global(.ir-share-dialog .el-dialog__header),
  :global(.ir-share-dialog .el-dialog__body) { padding-left: var(--xc-space-5); padding-right: var(--xc-space-5); }
  .ir-share__duration { align-items: flex-start; flex-direction: column; gap: var(--xc-space-4); }
  .ir-share__radio-group { width: 100%; display: flex; }
  .ir-share__radio-group :deep(.el-radio-button) { flex: 1; }
  .ir-share__radio-group :deep(.el-radio-button__inner) { width: 100%; }
  .ir-share__footer { align-items: stretch; flex-direction: column-reverse; }
  .ir-share__primary-btn { width: 100%; }
  .ir-share__link-box { align-items: stretch; flex-direction: column; gap: var(--xc-space-2); }
  .ir-share__copy-btn { width: 100%; }
}
</style>

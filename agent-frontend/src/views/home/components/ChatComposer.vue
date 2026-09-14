<template>
  <div
    class="ir-composer"
    @dragenter.prevent="onDragEnter"
    @dragover.prevent
    @dragleave.prevent="onDragLeave"
    @drop.prevent="onDrop"
  >
    <div class="ir-composer__frame" :class="{ 'is-dragging': isDragging }">
      <div v-if="spotContext || spotUploading || spotError" class="ir-composer__attachment" aria-live="polite">
        <LoaderCircle v-if="spotUploading" class="is-spinning" aria-hidden="true" />
        <CircleAlert v-else-if="effectiveSpotError" class="is-error" aria-hidden="true" />
        <FileSpreadsheet v-else aria-hidden="true" />
        <span class="ir-composer__attachment-copy">
          <strong>{{ attachmentTitle }}</strong>
          <span v-if="spotUploading || effectiveSpotError" class="ir-composer__attachment-detail">
            {{ attachmentDetail }}
          </span>
          <span v-else class="ir-composer__attachment-detail ir-composer__attachment-summary">
            <span>{{ readyDateRange }}</span>
            <span aria-hidden="true">·</span>
            <span>有效 {{ readyValidDays }} 天</span>
            <span v-if="readySkippedDays" class="is-warning">
              <span aria-hidden="true">·</span> 跳过 {{ readySkippedDays }} 天
            </span>
            <span aria-hidden="true">·</span>
            <span>本会话使用</span>
          </span>
        </span>
        <span v-if="spotUploading" class="ir-composer__elapsed">已用时 {{ elapsedSeconds }} 秒</span>
        <button
          type="button"
          class="ir-composer__attachment-remove"
          :aria-label="spotError ? '关闭电价文件错误' : '移除自定义电价文件'"
          :title="spotError ? '关闭错误' : '移除文件'"
          :disabled="spotUploading || responding"
          @click="spotError ? $emit('spot-error-dismiss') : $emit('spot-remove')"
        >
          <X aria-hidden="true" />
        </button>
        <div v-if="spotUploading" class="ir-composer__progress" role="status" aria-live="polite">
          <div class="ir-composer__steps" aria-label="文件处理进度">
            <div
              v-for="step in progressSteps"
              :key="step.phase"
              class="ir-composer__step"
              :class="stepState(step.phase)"
            >
              <span class="ir-composer__step-dot" aria-hidden="true">
                <Check v-if="stepState(step.phase) === 'is-complete'" />
                <span v-else>{{ step.index }}</span>
              </span>
              <span>{{ step.label }}</span>
            </div>
          </div>
          <div v-if="progressPhase === 'uploading'" class="ir-composer__meter" aria-hidden="true">
            <span :style="{ width: `${uploadPercent}%` }" />
          </div>
          <div v-else-if="progressPhase === 'computing' && totalDays" class="ir-composer__meter" aria-hidden="true">
            <span :style="{ width: `${computePercent}%` }" />
          </div>
        </div>
      </div>

      <div v-if="isDragging" class="ir-composer__drop-overlay" aria-hidden="true">
        <Upload class="ir-composer__drop-icon" />
        <span>释放以充电价文件</span>
      </div>

      <el-input
        ref="inputRef"
        v-model="text"
        type="textarea"
        :autosize="{ minRows: 1, maxRows: 6 }"
        resize="none"
        class="ir-composer__input"
        :placeholder="placeholder"
        :disabled="responding"
        @keydown.enter.exact.prevent="onSend"
      />

      <div class="ir-composer__bar">
        <div class="ir-composer__tools">
          <input
            ref="fileInputRef"
            class="ir-composer__file-input"
            type="file"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            :disabled="responding || spotUploading"
            @change="onFileChange"
          >

          <button
            type="button"
            class="ir-composer__action-btn ir-composer__action-btn--upload"
            aria-label="上传现货电价文件"
            :disabled="responding || spotUploading"
            @click="fileInputRef?.click()"
          >
            <Upload aria-hidden="true" />
            <span>上传电价文件</span>
          </button>

          <button
            type="button"
            class="ir-composer__action-btn ir-composer__action-btn--template"
            aria-label="下载电价文件模板"
            :disabled="responding || spotUploading"
            @click="$emit('spot-template')"
          >
            <Download aria-hidden="true" />
            <span>下载模板</span>
          </button>

          <el-popover
            :visible="hintPopoverVisible"
            placement="top-start"
            :width="360"
            trigger="click"
            popper-class="ir-composer__hint-popover"
            @update:visible="hintPopoverVisible = $event"
          >
            <template #reference>
              <button
                type="button"
                class="ir-composer__hint-trigger"
                aria-label="查看电价文件格式要求"
                :class="{ 'is-active': hintPopoverVisible }"
              >
                <CircleHelp aria-hidden="true" />
              </button>
            </template>
            <div class="ir-composer__hint-body">
              <strong>现货电价文件格式要求</strong>
              <p>上传 Excel 文件（.xlsx），用于按文件中的电价数据测算储能收益。</p>
              <ul>
                <li><strong>日期</strong> — 格式如 2024-01-01</li>
                <li><strong>时点</strong> — 00:15 至 24:00，15 分钟间隔</li>
                <li><strong>电价</strong> — 单位：元/MWh</li>
              </ul>
              <p class="ir-composer__hint-tip">
                可点击「下载模板」获取标准格式文件。
              </p>
            </div>
          </el-popover>
        </div>

        <button
          class="ir-composer__send"
          :class="{ 'is-idle': !responding && !text.trim(), 'is-stop': responding }"
          :aria-label="responding ? '停止生成' : '发送'"
          :disabled="!responding && (!text.trim() || spotUploading || Boolean(effectiveSpotError))"
          @click="onAction"
        >
          <Send v-if="!responding" aria-hidden="true" />
          <Square v-else aria-hidden="true" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { Check, CircleAlert, CircleHelp, Download, FileSpreadsheet, LoaderCircle, Send, Square, Upload, X } from '@lucide/vue'

const props = defineProps({
  responding: { type: Boolean, default: false },
  placeholder: { type: String, default: '继续对话……' },
  spotContext: { type: Object, default: null },
  spotUploading: { type: Boolean, default: false },
  spotProgress: { type: Object, default: null },
  spotError: { type: String, default: '' },
})
const emit = defineEmits(['send', 'stop', 'spot-upload', 'spot-remove', 'spot-error-dismiss', 'spot-template'])
const text = ref('')
const inputRef = ref(null)
const fileInputRef = ref(null)
const elapsedSeconds = ref(0)
const hintPopoverVisible = ref(false)
const isDragging = ref(false)
let elapsedTimer = null
let dragCounter = 0

const progressSteps = [
  { index: 1, phase: 'uploading', label: '文件上传' },
  { index: 2, phase: 'validating', label: '格式校验' },
  { index: 3, phase: 'computing', label: '数据计算' },
  { index: 4, phase: 'saving', label: '准备完成' },
]
const progressOrder = progressSteps.map((step) => step.phase)
const progressPhase = computed(() => props.spotProgress?.phase || 'uploading')
const uploadPercent = computed(() => Math.max(0, Math.min(100, Number(props.spotProgress?.uploadPercent) || 0)))
const completedDays = computed(() => Number(props.spotProgress?.completedDays) || 0)
const totalDays = computed(() => Number(props.spotProgress?.totalDays) || 0)
const computePercent = computed(() => (
  totalDays.value ? Math.max(0, Math.min(100, Math.round((completedDays.value / totalDays.value) * 100))) : 0
))
const readyDateRange = computed(() => {
  const context = props.spotContext || {}
  return `${context.startDate || '-'} 至 ${context.endDate || '-'}`
})
const readyValidDays = computed(() => Number(props.spotContext?.validDays) || 0)
const readySkippedDays = computed(() => Number(props.spotContext?.skippedDays) || 0)
const effectiveSpotError = computed(() => {
  if (props.spotError) return props.spotError
  if (props.spotContext?.status && props.spotContext.status !== 'ready') {
    return '本会话的自定义电价已失效，请移除后重新上传'
  }
  return ''
})
const attachmentTitle = computed(() => {
  if (props.spotUploading) return props.spotProgress?.fileName || '正在处理电价文件'
  if (effectiveSpotError.value) return '电价文件不可用'
  return props.spotContext?.fileName || '自定义现货电价'
})
const attachmentDetail = computed(() => {
  if (props.spotUploading) {
    if (progressPhase.value === 'uploading') return `正在上传电价文件${uploadPercent.value ? ` · ${uploadPercent.value}%` : ''}`
    if (progressPhase.value === 'computing' && totalDays.value) {
      return `${props.spotProgress?.message || '正在计算不同充放电策略'} · 已完成 ${completedDays.value}/${totalDays.value} 个有效日`
    }
    return props.spotProgress?.message || '正在处理电价文件'
  }
  if (effectiveSpotError.value) return effectiveSpotError.value
  return ''
})

function stopElapsedTimer() {
  if (elapsedTimer !== null) window.clearInterval(elapsedTimer)
  elapsedTimer = null
}

watch(() => props.spotUploading, (uploading) => {
  stopElapsedTimer()
  elapsedSeconds.value = 0
  if (!uploading) return
  const startedAt = Date.now()
  elapsedTimer = window.setInterval(() => {
    elapsedSeconds.value = Math.floor((Date.now() - startedAt) / 1000)
  }, 1000)
}, { immediate: true })

onBeforeUnmount(stopElapsedTimer)

function stepState(phase) {
  if (progressPhase.value === 'error') return ''
  const currentIndex = progressOrder.indexOf(progressPhase.value)
  const stepIndex = progressOrder.indexOf(phase)
  if (stepIndex < currentIndex) return 'is-complete'
  if (stepIndex === currentIndex) return 'is-active'
  return ''
}

async function fill(value) {
  text.value = String(value || '')
  await nextTick()
  inputRef.value?.focus?.({ cursor: 'end' })
}

defineExpose({ fill })

function onAction() {
  if (props.responding) {
    emit('stop')
    return
  }
  onSend()
}

function onFileChange(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (file) emit('spot-upload', file)
}

function onSend() {
  if (props.responding || props.spotUploading || effectiveSpotError.value) return
  const value = text.value.trim()
  if (!value) return
  text.value = ''
  emit('send', value)
}

function onDragEnter(event) {
  if (props.responding || props.spotUploading) return
  const types = event.dataTransfer?.types
  if (!types || !Array.from(types).includes('Files')) return
  dragCounter++
  isDragging.value = true
}

function onDragLeave() {
  dragCounter--
  if (dragCounter <= 0) {
    dragCounter = 0
    isDragging.value = false
  }
}

function onDrop(event) {
  dragCounter = 0
  isDragging.value = false
  if (props.responding || props.spotUploading) return
  const file = event.dataTransfer?.files?.[0]
  if (!file) return
  if (!file.name.endsWith('.xlsx') && file.type !== 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') return
  emit('spot-upload', file)
}
</script>

<style scoped>
.ir-composer { flex: 0 0 auto; }
.ir-composer__frame {
  position: relative;
  overflow: hidden;
  min-height: 120px;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-xl);
  background: var(--xc-surface-raised);
  padding: var(--xc-space-5) var(--xc-space-6) var(--xc-space-4) var(--xc-space-7);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: var(--xc-shadow-raised);
  transition: border-color var(--xc-dur-base), box-shadow var(--xc-dur-base);
}
.ir-composer__frame:focus-within { border-color: var(--xc-border-accent); }
.ir-composer__frame.is-dragging {
  border-color: var(--xc-accent-blue);
  border-style: dashed;
  background: color-mix(in srgb, var(--xc-accent-blue-soft) 30%, var(--xc-surface-raised));
}

.ir-composer__input { flex: 0 0 auto; }

.ir-composer__attachment {
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--xc-space-3);
  margin-bottom: var(--xc-space-4);
  padding-bottom: var(--xc-space-4);
  border-bottom: 1px solid var(--xc-border-soft);
  color: var(--xc-accent-blue);
}
.ir-composer__attachment > svg { width: 18px; height: 18px; flex: 0 0 auto; }
.ir-composer__attachment > .is-error { color: var(--xc-status-danger); }
.ir-composer__attachment-copy { min-width: 0; display: flex; flex: 1; flex-direction: column; }
.ir-composer__attachment-copy strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ir-composer__attachment-copy strong { color: var(--xc-text-strong); font-size: var(--xc-fs-sm); font-weight: var(--xc-fw-medium); }
.ir-composer__attachment-detail { min-width: 0; overflow: hidden; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); text-overflow: ellipsis; white-space: nowrap; }
.ir-composer__attachment-summary { display: flex; flex-wrap: wrap; column-gap: var(--xc-space-1); overflow: visible; white-space: normal; }
.ir-composer__attachment-summary .is-warning { color: var(--xc-status-warn); }
.ir-composer__elapsed { flex: 0 0 auto; color: var(--xc-text-mute); font-family: var(--xc-font-num); font-size: var(--xc-fs-2xs); font-variant-numeric: tabular-nums; }
.ir-composer__progress {
  flex: 1 0 100%;
  margin: var(--xc-space-4) 34px 0 26px;
  padding-top: var(--xc-space-4);
  border-top: 1px solid var(--xc-border-soft);
}
.ir-composer__steps {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--xc-space-2);
}
.ir-composer__step {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--xc-space-2);
  color: var(--xc-text-faint);
  font-size: var(--xc-fs-2xs);
  white-space: nowrap;
}
.ir-composer__step.is-active { color: var(--xc-accent-blue); }
.ir-composer__step.is-complete { color: var(--xc-status-ok); }
.ir-composer__step-dot {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border: 1px solid var(--xc-border-strong);
  border-radius: 50%;
  color: inherit;
  font-family: var(--xc-font-num);
  font-size: 10px;
  line-height: 1;
}
.ir-composer__step.is-active .ir-composer__step-dot {
  border-color: currentColor;
  box-shadow: 0 0 0 3px var(--xc-accent-blue-soft);
  animation: ir-composer-step-pulse 1.6s ease-in-out infinite;
}
.ir-composer__step.is-complete .ir-composer__step-dot {
  border-color: currentColor;
  background: var(--xc-status-ok-soft);
}
.ir-composer__step-dot svg { width: 11px; height: 11px; }
.ir-composer__meter {
  height: 3px;
  margin: var(--xc-space-3) 0 0 26px;
  overflow: hidden;
  border-radius: var(--xc-radius-full);
  background: var(--xc-surface-control);
}
.ir-composer__meter span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--xc-accent-blue);
}

.ir-composer__attachment-remove {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: var(--xc-radius-sm);
  background: transparent;
  color: var(--xc-text-soft);
  cursor: pointer;
}
.ir-composer__attachment-remove:hover:not(:disabled) { background: var(--xc-surface-control); color: var(--xc-text-strong); }
.ir-composer__attachment-remove:focus-visible { outline: 2px solid var(--xc-accent-blue); outline-offset: 2px; }
.ir-composer__attachment-remove:disabled { cursor: default; opacity: 0.45; }
.ir-composer__attachment-remove svg { width: 18px; height: 18px; }

.ir-composer__drop-overlay {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--xc-space-3);
  background: color-mix(in srgb, var(--xc-accent-blue-soft) 60%, transparent);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  color: var(--xc-accent-blue);
  font-size: var(--xc-fs-md);
  font-weight: var(--xc-fw-medium);
  border-radius: inherit;
  pointer-events: none;
}
.ir-composer__drop-icon { width: 32px; height: 32px; }

.ir-composer__input :deep(.el-textarea__inner) {
  background: transparent;
  border: 0;
  box-shadow: none;
  color: var(--xc-text-default);
  font-size: var(--xc-fs-md);
  line-height: var(--xc-lh-normal);
  padding: 0;
}
.ir-composer__input :deep(.el-textarea__inner::placeholder) { color: var(--xc-text-faint); }

.ir-composer__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  padding-top: var(--xc-space-4);
}
.ir-composer__tools {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--xc-space-2);
}
.ir-composer__file-input { display: none; }

.ir-composer__action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 0 12px;
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-sm);
  background: transparent;
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-xs);
  font-weight: var(--xc-fw-medium);
  cursor: pointer;
  white-space: nowrap;
  transition: background var(--xc-dur-fast), color var(--xc-dur-fast), border-color var(--xc-dur-fast);
}
.ir-composer__action-btn svg { width: 16px; height: 16px; flex: 0 0 auto; }
.ir-composer__action-btn:hover:not(:disabled) {
  background: var(--xc-surface-control);
  color: var(--xc-text-strong);
  border-color: var(--xc-border-strong);
}
.ir-composer__action-btn:focus-visible {
  outline: 2px solid var(--xc-accent-blue);
  outline-offset: 2px;
}
.ir-composer__action-btn:disabled {
  cursor: default;
  opacity: 0.45;
}

.ir-composer__action-btn--upload {
  color: var(--xc-accent-blue);
  border-color: color-mix(in srgb, var(--xc-accent-blue) 30%, var(--xc-border-card));
}
.ir-composer__action-btn--upload:hover:not(:disabled) {
  background: var(--xc-accent-blue-soft);
  color: var(--xc-accent-blue);
  border-color: color-mix(in srgb, var(--xc-accent-blue) 50%, var(--xc-border-card));
}

.ir-composer__action-btn--template {
  color: var(--xc-text-mute);
}

.ir-composer__hint-trigger {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--xc-text-faint);
  cursor: pointer;
  transition: background var(--xc-dur-fast), color var(--xc-dur-fast);
}
.ir-composer__hint-trigger svg { width: 16px; height: 16px; }
.ir-composer__hint-trigger:hover { background: var(--xc-surface-control); color: var(--xc-text-soft); }
.ir-composer__hint-trigger.is-active { background: var(--xc-accent-blue-soft); color: var(--xc-accent-blue); }
.ir-composer__hint-trigger:focus-visible { outline: 2px solid var(--xc-accent-blue); outline-offset: 2px; }

.ir-composer__send {
  width: 44px;
  height: 44px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: var(--xc-radius-md);
  background: var(--xc-grad-send);
  color: var(--xc-text-strong);
  cursor: pointer;
  box-shadow: var(--xc-glow-blue);
  transition: opacity var(--xc-dur-fast), transform var(--xc-dur-fast);
}
.ir-composer__send:hover:not(:disabled) { transform: translateY(-1px); }
.ir-composer__send.is-idle { opacity: 0.45; }
.ir-composer__send.is-stop { background: var(--xc-status-danger); box-shadow: none; }
.ir-composer__send:disabled { cursor: default; }
.ir-composer__send svg { width: 20px; height: 20px; }

.is-spinning { animation: ir-composer-spin 0.8s linear infinite; }
@keyframes ir-composer-spin { to { transform: rotate(360deg); } }
@keyframes ir-composer-step-pulse {
  0%, 100% { opacity: 0.72; }
  50% { opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .ir-composer__frame,
  .ir-composer__send,
  .ir-composer__action-btn { transition: none; }
  .ir-composer__step.is-active .ir-composer__step-dot { animation: none; }
}

@media (max-width: 560px) {
  .ir-composer__progress { margin-right: 0; margin-left: 0; }
  .ir-composer__steps { gap: 0; }
  .ir-composer__step { flex-direction: column; align-items: flex-start; gap: 3px; white-space: normal; }
  .ir-composer__meter { margin-left: 0; }
  .ir-composer__bar { align-items: flex-end; gap: var(--xc-space-3); }
  .ir-composer__tools { align-items: flex-start; flex-wrap: wrap; gap: var(--xc-space-1); }
  .ir-composer__action-btn { height: 30px; padding: 0 8px; font-size: var(--xc-fs-2xs); }
  .ir-composer__action-btn span { display: none; }
  .ir-composer__hint-trigger { width: 24px; height: 24px; }
}
</style>


<style>
.ir-composer__hint-popover.el-popover {
  padding: 0 !important;
  background: var(--xc-surface-2) !important;
  border: 1px solid var(--xc-border-strong) !important;
  color: var(--xc-text-default) !important;
}
.ir-composer__hint-popover.el-popover > .el-popper__arrow {
  display: none !important;
}
.ir-composer__hint-body {
  padding: 16px;
}
.ir-composer__hint-body strong {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: var(--xc-text-strong);
}
.ir-composer__hint-body p {
  margin: 0 0 8px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--xc-text-soft);
}
.ir-composer__hint-body ul {
  margin: 0 0 12px;
  padding: 10px 12px;
  list-style: none;
  border-radius: 6px;
  background: var(--xc-surface-control);
}
.ir-composer__hint-body li {
  font-size: 13px;
  line-height: 1.8;
  color: var(--xc-text-default);
}
.ir-composer__hint-body li strong {
  display: inline;
  margin-bottom: 0;
  font-size: 13px;
}
.ir-composer__hint-tip {
  font-size: 12px !important;
  color: var(--xc-text-mute) !important;
}
</style>

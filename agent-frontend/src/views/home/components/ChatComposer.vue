<template>
  <div class="ir-composer">
    <div class="ir-composer__frame">
      <div v-if="spotContext || spotUploading || spotError" class="ir-composer__attachment" aria-live="polite">
        <LoaderCircle v-if="spotUploading" class="is-spinning" aria-hidden="true" />
        <CircleAlert v-else-if="effectiveSpotError" class="is-error" aria-hidden="true" />
        <FileSpreadsheet v-else aria-hidden="true" />
        <span class="ir-composer__attachment-copy">
          <strong>{{ attachmentTitle }}</strong>
          <span>{{ attachmentDetail }}</span>
        </span>
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
            class="ir-composer__upload"
            aria-label="上传现货电价文件"
            title="上传现货电价文件"
            :disabled="responding || spotUploading"
            @click="fileInputRef?.click()"
          >
            <Upload aria-hidden="true" />
          </button>
          <button
            type="button"
            class="ir-composer__template"
            aria-label="下载电价文件模板"
            title="下载电价文件模板"
            :disabled="responding || spotUploading"
            @click="$emit('spot-template')"
          >
            <Download aria-hidden="true" />
          </button>
          <span class="ir-composer__hint">Excel 电价</span>
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
import { computed, nextTick, ref } from 'vue'
import { CircleAlert, Download, FileSpreadsheet, LoaderCircle, Send, Square, Upload, X } from '@lucide/vue'

const props = defineProps({
  responding: { type: Boolean, default: false },
  placeholder: { type: String, default: '继续对话……' },
  spotContext: { type: Object, default: null },
  spotUploading: { type: Boolean, default: false },
  spotError: { type: String, default: '' },
})
const emit = defineEmits(['send', 'stop', 'spot-upload', 'spot-remove', 'spot-error-dismiss', 'spot-template'])
const text = ref('')
const inputRef = ref(null)
const fileInputRef = ref(null)
const effectiveSpotError = computed(() => {
  if (props.spotError) return props.spotError
  if (props.spotContext?.status && props.spotContext.status !== 'ready') {
    return '本会话的自定义电价已失效，请移除后重新上传'
  }
  return ''
})
const attachmentTitle = computed(() => {
  if (props.spotUploading) return '正在校验电价文件'
  if (effectiveSpotError.value) return '电价文件不可用'
  return props.spotContext?.fileName || '自定义现货电价'
})
const attachmentDetail = computed(() => {
  if (props.spotUploading) return '正在解析并计算 19 个充放电档位'
  if (effectiveSpotError.value) return effectiveSpotError.value
  const context = props.spotContext || {}
  return `${context.startDate || '-'} 至 ${context.endDate || '-'} · 有效 ${context.validDays || 0} 天 · 本会话使用`
})

// 供外部（如欢迎态示例胶囊）把示例文案填入输入框并聚焦，不自动发送。
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
.ir-composer__input { flex: 0 0 auto; }
.ir-composer__attachment {
  min-width: 0;
  display: flex;
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
.ir-composer__attachment-copy strong,
.ir-composer__attachment-copy span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ir-composer__attachment-copy strong { color: var(--xc-text-strong); font-size: var(--xc-fs-sm); font-weight: var(--xc-fw-medium); }
.ir-composer__attachment-copy span { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.ir-composer__attachment-remove,
.ir-composer__upload,
.ir-composer__template {
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
.ir-composer__attachment-remove:hover:not(:disabled),
.ir-composer__upload:hover:not(:disabled),
.ir-composer__template:hover:not(:disabled) { background: var(--xc-surface-control); color: var(--xc-text-strong); }
.ir-composer__attachment-remove:focus-visible,
.ir-composer__upload:focus-visible,
.ir-composer__template:focus-visible { outline: 2px solid var(--xc-accent-blue); outline-offset: 2px; }
.ir-composer__attachment-remove:disabled,
.ir-composer__upload:disabled,
.ir-composer__template:disabled { cursor: default; opacity: 0.45; }
.ir-composer__attachment-remove svg,
.ir-composer__upload svg,
.ir-composer__template svg { width: 18px; height: 18px; }
.ir-composer__file-input { display: none; }
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
.ir-composer__tools { display: flex; align-items: center; gap: var(--xc-space-2); }
.ir-composer__hint { font-size: var(--xc-fs-xs); color: var(--xc-text-mute); line-height: var(--xc-lh-normal); }
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

@media (prefers-reduced-motion: reduce) {
  .ir-composer__frame,
  .ir-composer__send { transition: none; }
}
</style>

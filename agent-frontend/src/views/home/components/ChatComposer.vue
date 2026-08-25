<template>
  <div class="ir-composer">
    <div class="ir-composer__frame">
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
        <div class="ir-composer__hint">
          <span>Enter 发送 · Shift+Enter 换行</span>
        </div>
        <button
          class="ir-composer__send"
          :class="{ 'is-idle': !responding && !text.trim(), 'is-stop': responding }"
          :aria-label="responding ? '停止生成' : '发送'"
          :disabled="!responding && !text.trim()"
          @click="onAction"
        >
          <svg v-if="!responding" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M3 11.5 21 3l-3.5 18-5-7-9.5-2.5z" />
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <rect x="6" y="6" width="12" height="12" rx="2" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, ref } from 'vue'

const props = defineProps({
  responding: { type: Boolean, default: false },
  placeholder: { type: String, default: '继续对话……' },
})
const emit = defineEmits(['send', 'stop'])
const text = ref('')
const inputRef = ref(null)

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

function onSend() {
  if (props.responding) return
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
.ir-composer__frame::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--xc-border-card);
  transition: background var(--xc-dur-base), box-shadow var(--xc-dur-base);
}
.ir-composer__frame:focus-within { border-color: var(--xc-border-accent); }
.ir-composer__frame:focus-within::before {
  background: var(--xc-grad-send);
  box-shadow: var(--xc-glow-blue);
}
.ir-composer__input { flex: 0 0 auto; }
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

@media (prefers-reduced-motion: reduce) {
  .ir-composer__frame,
  .ir-composer__frame::before,
  .ir-composer__send { transition: none; }
}
</style>

<template>
  <div class="ir-composer">
    <div class="ir-composer__frame">
      <el-input
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
          :class="{ 'is-idle': !responding && !text.trim() }"
          :aria-label="responding ? '测算中' : '发送'"
          :disabled="responding"
          @click="onSend"
        >
          <svg v-if="!responding" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M3 11.5 21 3l-3.5 18-5-7-9.5-2.5z" />
          </svg>
          <svg v-else class="ir-composer__spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M12 3a9 9 0 1 0 9 9" stroke-linecap="round" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  responding: { type: Boolean, default: false },
  placeholder: { type: String, default: '继续对话……' },
})
const emit = defineEmits(['send'])
const text = ref('')

function onSend() {
  if (props.responding) return
  const v = text.value
  text.value = ''
  emit('send', v)
}
</script>

<style scoped>
.ir-composer {
  flex: 0 0 auto;
  padding: var(--xc-space-4) var(--xc-space-6) var(--xc-space-6);
}
.ir-composer__frame {
  position: relative;
  min-height: 112px;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-xl);
  background: var(--xc-surface-raised);
  padding: var(--xc-space-5) var(--xc-space-6) var(--xc-space-4);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: var(--xc-shadow-raised);
  transition: border-color var(--xc-dur-base), box-shadow var(--xc-dur-base);
}
.ir-composer__frame:focus-within {
  border-color: var(--xc-border-accent);
  box-shadow: var(--xc-shadow-raised), var(--xc-glow-blue);
}
.ir-composer__input {
  flex: 0 0 auto;
}
.ir-composer__input :deep(.el-textarea__inner) {
  background: transparent;
  border: 0;
  box-shadow: none;
  color: var(--xc-text-default);
  font-size: var(--xc-fs-md);
  line-height: var(--xc-lh-normal);
  padding: 0;
}
.ir-composer__input :deep(.el-textarea__inner::placeholder) {
  color: var(--xc-text-faint);
}
.ir-composer__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  padding-top: var(--xc-space-4);
}
.ir-composer__hint {
  font-size: var(--xc-fs-2xs);
  color: var(--xc-text-faint);
}
.ir-composer__send {
  width: 44px;
  height: 44px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: var(--xc-radius-lg);
  background: var(--xc-grad-send);
  color: #fff;
  cursor: pointer;
  box-shadow: var(--xc-glow-blue);
  transition: opacity var(--xc-dur-fast), transform var(--xc-dur-fast);
}
.ir-composer__send:hover:not(:disabled) { transform: translateY(-1px); }
.ir-composer__send.is-idle { opacity: 0.45; }
.ir-composer__send:disabled { cursor: default; }
.ir-composer__send svg { width: 20px; height: 20px; }
.ir-composer__spin { animation: ir-spin 0.9s linear infinite; }
@keyframes ir-spin { to { transform: rotate(360deg); } }
</style>

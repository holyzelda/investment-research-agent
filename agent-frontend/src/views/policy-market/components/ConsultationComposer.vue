<template>
  <div class="pm-composer">
    <textarea
      ref="textareaRef"
      v-model="question"
      class="pm-composer__input"
      placeholder="输入你想了解的政策或市场问题…"
      rows="2"
      @keydown="onKeydown"
    />
    <div class="pm-composer__tools">
      <span>Ctrl / Cmd + Enter 提交咨询</span>
      <button type="button" aria-label="提交咨询" @click="submit">提交</button>
    </div>
    <div class="pm-composer__quick">
      <span>试试这些：</span>
      <button v-for="item in quickQuestions" :key="item" type="button" data-quick-question @click="question = item">{{ item }}</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['submit-question'])
const textareaRef = ref(null)
const question = ref('')
const quickQuestions = [
  '新能源消纳政策有何变化？',
  '本月电价机制如何影响制造业？',
  '查找储能行业最新政策',
]

function submit() {
  const normalizedQuestion = question.value.trim()
  if (!normalizedQuestion) {
    textareaRef.value?.focus()
    return
  }
  emit('submit-question', normalizedQuestion)
  question.value = ''
}

function onKeydown(event) {
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') submit()
}

defineExpose({ focus: () => textareaRef.value?.focus() })
</script>

<style scoped>
.pm-composer { display: grid; gap: var(--xc-space-3); padding: var(--xc-space-4); border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-md); background: var(--xc-surface-card); }
.pm-composer__input { width: 100%; min-height: 72px; resize: vertical; box-sizing: border-box; border: 0; outline: 0; background: transparent; color: var(--xc-text-strong); font: inherit; line-height: var(--xc-lh-normal); }
.pm-composer__input::placeholder { color: var(--xc-text-mute); }
.pm-composer__tools { display: flex; align-items: center; justify-content: space-between; gap: var(--xc-space-3); color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.pm-composer__tools button { border: 0; border-radius: var(--xc-radius-sm); padding: var(--xc-space-2) var(--xc-space-4); background: var(--xc-accent-blue); color: var(--xc-text-strong); cursor: pointer; }
.pm-composer__tools button:hover, .pm-composer__tools button:focus-visible { box-shadow: var(--xc-glow-blue); }
.pm-composer__quick { display: flex; flex-wrap: wrap; align-items: center; gap: var(--xc-space-2); color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.pm-composer__quick button { border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-full); padding: var(--xc-space-1) var(--xc-space-3); background: transparent; color: var(--xc-text-soft); cursor: pointer; }
.pm-composer__quick button:hover, .pm-composer__quick button:focus-visible { border-color: var(--xc-border-accent); color: var(--xc-text-strong); }
</style>

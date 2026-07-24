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
.pm-composer { position: relative; display: grid; gap: var(--xc-space-3); padding: 22px 22px 16px; border: 1px solid var(--xc-border-accent); border-radius: var(--xc-radius-md); background: linear-gradient(135deg, var(--xc-surface-card), var(--xc-surface-raised)); box-shadow: 0 12px 30px rgb(25 48 58 / 10%), 0 0 0 5px rgb(72 150 166 / 7%); transition: border-color .18s ease, box-shadow .18s ease; }
.pm-composer::before { position: absolute; top: -10px; left: 20px; padding: 0 8px; background: var(--xc-surface-base); color: var(--xc-accent-blue); content: '开始一次研究'; font-size: var(--xc-fs-2xs); letter-spacing: .08em; }
.pm-composer:focus-within { border-color: var(--xc-accent-blue); box-shadow: 0 14px 34px rgb(25 48 58 / 14%), 0 0 0 5px rgb(72 150 166 / 12%); }
.pm-composer__input { width: 100%; min-height: 88px; resize: vertical; box-sizing: border-box; border: 0; outline: 0; background: transparent; color: var(--xc-text-strong); font: inherit; font-size: clamp(15px, 1.4vw, 18px); line-height: 1.7; }
.pm-composer__input::placeholder { color: var(--xc-text-mute); }
.pm-composer__tools { display: flex; align-items: center; justify-content: space-between; gap: var(--xc-space-3); color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.pm-composer__tools button { min-width: 78px; border: 0; border-radius: var(--xc-radius-sm); padding: 10px 16px; background: var(--xc-accent-blue); color: var(--xc-text-strong); font-weight: var(--xc-fw-semi); cursor: pointer; }
.pm-composer__tools button:hover, .pm-composer__tools button:focus-visible { box-shadow: var(--xc-glow-blue); }
.pm-composer__quick { display: flex; flex-wrap: wrap; align-items: center; gap: var(--xc-space-2); color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.pm-composer__quick button { border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); padding: var(--xc-space-1) var(--xc-space-3); background: transparent; color: var(--xc-text-soft); cursor: pointer; }
.pm-composer__quick button:hover, .pm-composer__quick button:focus-visible { border-color: var(--xc-border-accent); color: var(--xc-text-strong); }
@media (max-width: 520px) { .pm-composer__tools span { display: none; }.pm-composer__quick > span { flex-basis: 100%; } }
</style>

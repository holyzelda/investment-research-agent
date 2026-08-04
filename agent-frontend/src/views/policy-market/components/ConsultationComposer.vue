<template>
  <div class="pm-composer">
    <div class="pm-composer__heading">
      <span class="pm-composer__icon"><FileSearch :size="17" /></span>
      <div><strong>研究问题</strong><span>说明地区、时间或关注对象，结论会更准确</span></div>
    </div>
    <textarea
      ref="textareaRef"
      v-model="question"
      class="pm-composer__input"
      placeholder="输入你想了解的政策或市场问题…"
      rows="2"
      @keydown="onKeydown"
    />
    <div class="pm-composer__quick">
      <span>相关问题</span>
      <button v-for="item in quickQuestions" :key="item" type="button" data-quick-question @click="question = item">{{ item }}</button>
    </div>
    <div class="pm-composer__tools">
      <span>{{ question.length ? `${question.length} 字` : '等待输入' }}</span>
      <button type="button" aria-label="提交咨询" @click="submit"><Send :size="16" />提交研究</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { FileSearch, Send } from '@lucide/vue'

const emit = defineEmits(['submit-question'])
const textareaRef = ref(null)
const question = ref('')
const quickQuestions = [
  '宁夏储能政策',
  '蒙西储能补偿变化',
  '甘肃，宁夏，蒙西储能投资哪个地方好？',
]

function setQuestion(value = '') {
  question.value = String(value || '')
}

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

defineExpose({ focus: () => textareaRef.value?.focus(), setQuestion })
</script>

<style scoped>
.pm-composer {
  position: relative;
  display: grid;
  gap: 16px;
  padding: 20px 22px 18px 26px;
  border: 1px solid var(--xc-border-soft);
  border-left: 3px solid var(--pm-accent, var(--xc-accent-blue));
  border-radius: var(--xc-radius-sm);
  background: var(--pm-surface, var(--xc-surface-raised));
  box-shadow: 0 14px 32px rgb(0 0 0 / 18%);
  transition: border-color 240ms cubic-bezier(.16, 1, .3, 1), box-shadow 240ms cubic-bezier(.16, 1, .3, 1);
}

.pm-composer__heading { display: flex; align-items: center; gap: 10px; }
.pm-composer__heading > div { display: grid; gap: 2px; }
.pm-composer__heading strong { color: var(--xc-text-strong); font-size: var(--xc-fs-sm); }
.pm-composer__heading div span { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.pm-composer__icon {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-sm);
  color: var(--pm-accent, var(--xc-accent-blue));
}

.pm-composer:focus-within {
  border-color: var(--pm-accent, var(--xc-accent-blue));
  box-shadow: 0 18px 40px rgb(0 0 0 / 24%);
}

.pm-composer__input {
  width: 100%;
  min-height: 96px;
  resize: vertical;
  box-sizing: border-box;
  border: 0;
  border-bottom: 1px solid var(--xc-border-soft);
  outline: 0;
  padding: 8px 0 16px;
  background: transparent;
  color: var(--xc-text-strong);
  font: inherit;
  font-size: clamp(15px, 1.4vw, 18px);
  line-height: 1.7;
}

.pm-composer__input::placeholder { color: var(--xc-text-mute); }
.pm-composer__tools { display: flex; align-items: center; justify-content: space-between; gap: 12px; color: var(--xc-text-mute); font-family: var(--xc-font-mono); font-size: var(--xc-fs-2xs); }
.pm-composer__tools button { min-width: 124px; min-height: 44px; display: inline-flex; align-items: center; justify-content: center; gap: 8px; border: 1px solid var(--pm-accent, var(--xc-accent-blue)); border-radius: var(--xc-radius-sm); padding: 10px 18px; background: var(--pm-accent, var(--xc-accent-blue)); color: #132326; font-weight: var(--xc-fw-bold); cursor: pointer; }
.pm-composer__tools button:hover, .pm-composer__tools button:focus-visible { outline: 2px solid var(--pm-accent, var(--xc-accent-blue)); outline-offset: 3px; }
.pm-composer__quick { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.pm-composer__quick > span { margin-right: 2px; font-family: var(--xc-font-mono); }
.pm-composer__quick button { border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); padding: 7px 10px; background: transparent; color: var(--xc-text-soft); cursor: pointer; }
.pm-composer__quick button:hover, .pm-composer__quick button:focus-visible { border-color: var(--xc-border-accent); outline: none; background: var(--xc-surface-frosted); color: var(--xc-text-strong); }
@media (max-width: 720px) { .pm-composer__quick > span { width: 100%; } }
@media (max-width: 520px) { .pm-composer { padding: 18px 16px 16px 18px; }.pm-composer__heading div span { display: none; }.pm-composer__tools span { display: none; }.pm-composer__tools button { width: 100%; } }
@media (prefers-reduced-motion: reduce) { .pm-composer { transition: none; } }
</style>

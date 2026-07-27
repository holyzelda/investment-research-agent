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
.pm-composer {
  position: relative;
  display: grid;
  gap: var(--xc-space-4);
  padding: 30px 22px 18px;
  border: 1px solid var(--xc-border-accent);
  border-radius: var(--xc-radius-sm);
  background: var(--xc-surface-raised);
  box-shadow: 0 10px 28px rgb(0 0 0 / 16%), 0 0 0 4px var(--xc-accent-blue-soft);
  transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease;
}

.pm-composer::before {
  position: absolute;
  top: 11px;
  left: 22px;
  color: var(--xc-accent-blue);
  content: '开始一次研究';
  font-size: var(--xc-fs-2xs);
  font-weight: var(--xc-fw-semi);
  letter-spacing: .08em;
}

.pm-composer:focus-within {
  border-color: var(--xc-accent-blue);
  box-shadow: 0 14px 34px rgb(0 0 0 / 22%), 0 0 0 5px var(--xc-accent-blue-soft);
  transform: translateY(-1px);
}

.pm-composer__input {
  width: 100%;
  min-height: 92px;
  resize: vertical;
  box-sizing: border-box;
  border: 0;
  border-bottom: 1px solid var(--xc-border-soft);
  outline: 0;
  padding: 12px 0 14px;
  background: transparent;
  color: var(--xc-text-strong);
  font: inherit;
  font-size: clamp(15px, 1.4vw, 18px);
  line-height: 1.7;
}

.pm-composer__input::placeholder { color: var(--xc-text-mute); }
.pm-composer__tools { display: flex; align-items: center; justify-content: space-between; gap: var(--xc-space-3); color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.pm-composer__tools button { min-width: 96px; min-height: 40px; border: 1px solid var(--xc-accent-blue); border-radius: var(--xc-radius-sm); padding: 10px 18px; background: var(--xc-accent-blue); color: #06131a; font-weight: var(--xc-fw-bold); cursor: pointer; }
.pm-composer__tools button:hover, .pm-composer__tools button:focus-visible { outline: none; box-shadow: var(--xc-glow-blue); }
.pm-composer__quick { display: flex; flex-wrap: wrap; align-items: center; gap: var(--xc-space-2); padding-top: 2px; color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); }
.pm-composer__quick button { border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); padding: 6px 10px; background: var(--xc-surface-control); color: var(--xc-text-soft); cursor: pointer; }
.pm-composer__quick button:hover, .pm-composer__quick button:focus-visible { border-color: var(--xc-border-accent); outline: none; background: var(--xc-surface-frosted); color: var(--xc-text-strong); }
@media (max-width: 520px) { .pm-composer { padding-inline: 16px; }.pm-composer::before { left: 16px; }.pm-composer__tools span { display: none; }.pm-composer__quick > span { flex-basis: 100%; } }
</style>

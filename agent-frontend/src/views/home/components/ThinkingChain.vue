<template>
  <div v-if="visible" class="ir-thinking">
    <button type="button" class="ir-thinking__header" :class="{ 'ir-thinking__header--toggleable': terminal }" @click="toggleChain">
      <svg class="ir-thinking__header-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 1 1 7.072 0l-.548.547A3.374 3.374 0 0 0 14 18.469V19a2 2 0 1 1-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      <span class="ir-thinking__header-title">{{ title }}</span>
      <span v-if="durationText" class="ir-thinking__duration">{{ durationText }}</span>
      <svg v-if="terminal" class="ir-thinking__chain-chevron" :class="{ 'is-open': chainOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <path d="M6 9l6 6 6-6" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </button>
    <div v-if="chainOpen" class="ir-thinking__body">
      <div v-if="bootstrapping" class="ir-thinking__placeholder"><span class="ir-thinking__pulse" />{{ bootstrapText }}</div>
      <ThinkingNodeItem v-for="(node, i) in nodes" :key="node.nodeId" :node="node" :ordinal="nodes.length > 1 ? `${i + 1}/${nodes.length}` : ''" @toggle="toggleNode" />
      <div v-if="streaming && nodes.length && !hasActive" class="ir-thinking__placeholder ir-thinking__placeholder--bridge"><span class="ir-thinking__pulse" />正在推进下一步…</div>
      <button v-if="terminal && nodes.length > 1" type="button" class="ir-thinking__toggle" @click.stop="toggleAll">{{ allExpanded ? '全部折叠' : '全部展开' }}</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted, watch } from 'vue'
import ThinkingNodeItem from './ThinkingNodeItem.vue'

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  hasActive: { type: Boolean, default: false },
  streaming: { type: Boolean, default: false },
  bootstrapping: { type: Boolean, default: false },
  startedAt: { type: Number, default: null },
  finishedAt: { type: Number, default: null },
  activeTitle: { type: String, default: '正在深度推理' },
  completedTitle: { type: String, default: '推理完成' },
  bootstrappingTitle: { type: String, default: '正在唤醒推理内核…' },
  bootstrapText: { type: String, default: '正在准备分析上下文…' },
})

const now = ref(Date.now())
const chainOpen = ref(true)
let timer = setInterval(() => { now.value = Date.now() }, 100)
onUnmounted(() => { clearInterval(timer); timer = null })

const terminal = computed(() => !props.streaming && Boolean(props.finishedAt))
watch(terminal, (isTerminal) => {
  if (isTerminal) chainOpen.value = false
}, { immediate: true })
const visible = computed(() => props.bootstrapping || props.nodes.length > 0 || props.streaming)
const title = computed(() => {
  if (props.bootstrapping) return props.bootstrappingTitle
  return terminal.value ? props.completedTitle : props.activeTitle
})
const elapsed = computed(() => {
  if (!props.startedAt) return 0
  return Math.max(0, (props.finishedAt || now.value) - props.startedAt)
})
const durationText = computed(() => {
  if (!elapsed.value) return ''
  const sec = Math.floor(elapsed.value / 1000)
  return sec < 60 ? `${sec}s` : `${Math.floor(sec / 60)}m ${sec % 60}s`
})
const allExpanded = computed(() => props.nodes.length > 0 && props.nodes.every((node) => node.open))

function toggleChain() { if (terminal.value) chainOpen.value = !chainOpen.value }
function toggleNode(nodeId) {
  const node = props.nodes.find((item) => item.nodeId === nodeId)
  if (node) node.open = !node.open
}
function toggleAll() {
  const next = !allExpanded.value
  for (const node of props.nodes) node.open = next
}
</script>

<style scoped>
.ir-thinking {
  margin: 0 0 var(--xc-space-3);
  padding: var(--xc-space-4) var(--xc-space-5);
  border: 1px solid var(--xc-border-soft);
  border-radius: var(--xc-radius-sm);
  background: color-mix(in srgb, var(--xc-surface-base) 78%, transparent);
}
.ir-thinking__header {
  display: flex;
  align-items: center;
  gap: var(--xc-space-2);
  width: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: default;
}
.ir-thinking__header--toggleable { cursor: pointer; }
.ir-thinking__header-icon { width: 16px; height: 16px; flex: 0 0 auto; color: var(--xc-accent-blue); }
.ir-thinking__header-title { font-size: var(--xc-fs-sm); font-weight: var(--xc-fw-medium); color: var(--xc-text-strong); }
.ir-thinking__duration { margin-left: auto; font-size: var(--xc-fs-2xs); color: var(--xc-text-mute); font-variant-numeric: tabular-nums; }
.ir-thinking__chain-chevron { width: 14px; height: 14px; color: var(--xc-text-mute); transition: transform var(--xc-dur-fast); }
.ir-thinking__chain-chevron.is-open { transform: rotate(180deg); }
.ir-thinking__body {
  display: flex;
  flex-direction: column;
  gap: var(--xc-space-1);
  margin-top: var(--xc-space-3);
  padding-top: var(--xc-space-3);
  border-top: 1px solid var(--xc-border-soft);
}
.ir-thinking__placeholder { display: flex; align-items: center; gap: var(--xc-space-3); min-height: 28px; color: var(--xc-text-mute); font-size: var(--xc-fs-xs); }
.ir-thinking__placeholder--bridge { padding-left: 26px; }
.ir-thinking__pulse { width: 7px; height: 7px; border-radius: 50%; background: var(--xc-accent-blue); animation: ir-thinking-pulse 1.2s ease-in-out infinite; }
@keyframes ir-thinking-pulse { 0%, 100% { opacity: 0.35; transform: scale(0.8); } 50% { opacity: 1; transform: scale(1); } }
.ir-thinking__toggle { align-self: flex-end; margin-top: var(--xc-space-2); padding: var(--xc-space-1) var(--xc-space-3); font-size: var(--xc-fs-2xs); color: var(--xc-accent-blue); background: transparent; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); cursor: pointer; }
@media (prefers-reduced-motion: reduce) {
  .ir-thinking__chain-chevron { transition: none; }
  .ir-thinking__pulse { animation: none; }
}
</style>

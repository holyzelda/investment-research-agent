<template>
  <div v-if="nodes.length" class="ir-thinking">
    <div class="ir-thinking__header">
      <svg class="ir-thinking__header-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 1 1 7.072 0l-.548.547A3.374 3.374 0 0 0 14 18.469V19a2 2 0 1 1-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      <span class="ir-thinking__header-title">思考过程</span>
      <span v-if="durationText" class="ir-thinking__duration">{{ durationText }}</span>
      <button
        v-if="nodes.length > 1"
        type="button"
        class="ir-thinking__toggle"
        @click="allExpanded = !allExpanded"
      >
        {{ allExpanded ? '全部折叠' : '全部展开' }}
      </button>
    </div>
    <div class="ir-thinking__body">
      <ThinkingNodeItem
        v-for="(node, i) in nodes"
        :key="node.nodeId"
        :node="node"
        :ordinal="nodes.length > 1 ? `${i + 1}/${nodes.length}` : ''"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import ThinkingNodeItem from './ThinkingNodeItem.vue'

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  hasActive: { type: Boolean, default: false },
})

const allExpanded = ref(false)

watch(() => props.nodes, (newNodes) => {
  // 同步 node.open 到子组件
  for (const node of newNodes) {
    node.open = allExpanded.value
  }
}, { deep: true })

watch(allExpanded, (val) => {
  for (const node of props.nodes) {
    node.open = val
  }
})

// 思考计时（仅当有 active 节点时累加）
const startTime = ref(null)
const elapsed = ref(0)
let timer = null

watch(() => props.hasActive, (active) => {
  if (active && !startTime.value) {
    startTime.value = Date.now()
    timer = setInterval(() => {
      elapsed.value = Date.now() - startTime.value
    }, 100)
  } else if (!active && timer) {
    clearInterval(timer)
    timer = null
  }
}, { immediate: true })

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

const durationText = computed(() => {
  if (!elapsed.value) return ''
  const sec = Math.floor(elapsed.value / 1000)
  return sec < 60 ? `${sec}s` : `${Math.floor(sec / 60)}m ${sec % 60}s`
})
</script>

<style scoped>
.ir-thinking {
  margin: var(--xc-space-4) 0;
  padding: var(--xc-space-4);
  border-radius: var(--xc-radius-md);
  border: 1px solid var(--xc-border-strong);
  background: var(--xc-bg-subtle);
}
.ir-thinking__header {
  display: flex;
  align-items: center;
  gap: var(--xc-space-3);
  margin-bottom: var(--xc-space-3);
  padding-bottom: var(--xc-space-3);
  border-bottom: 1px solid var(--xc-border-base);
}
.ir-thinking__header-icon { width: 18px; height: 18px; color: var(--xc-accent-blue); }
.ir-thinking__header-title {
  font-size: var(--xc-fs-base);
  font-weight: var(--xc-fw-medium);
  color: var(--xc-text-strong);
}
.ir-thinking__duration {
  margin-left: auto;
  font-size: var(--xc-fs-xs);
  color: var(--xc-text-mute);
  font-variant-numeric: tabular-nums;
}
.ir-thinking__toggle {
  padding: var(--xc-space-1) var(--xc-space-3);
  font-size: var(--xc-fs-xs);
  color: var(--xc-accent-blue);
  background: transparent;
  border: 1px solid var(--xc-border-strong);
  border-radius: var(--xc-radius-sm);
  cursor: pointer;
  transition: all var(--xc-dur-fast);
}
.ir-thinking__toggle:hover {
  background: var(--xc-bg-subtle-hover);
  border-color: var(--xc-accent-blue);
}
.ir-thinking__body { display: flex; flex-direction: column; gap: var(--xc-space-1); }
</style>

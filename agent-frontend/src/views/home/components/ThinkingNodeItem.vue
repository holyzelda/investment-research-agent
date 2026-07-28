<template>
  <div class="ir-node" :class="`ir-node--${node.status}`">
    <button
      type="button"
      class="ir-node__head"
      :class="{ 'ir-node__head--expandable': expandable }"
      @click="expandable && (expanded = !expanded)"
    >
      <span class="ir-node__icon" :class="`ir-node__icon--${node.status}`">
        <svg v-if="node.status === 'active'" class="ir-node__spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M12 3a9 9 0 1 0 9 9" stroke-linecap="round" />
        </svg>
        <svg v-else-if="node.status === 'waiting_user'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" stroke-linecap="round" />
        </svg>
        <svg v-else-if="node.status === 'aborted'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M6 6l12 12M18 6 6 18" stroke-linecap="round" />
        </svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </span>
      <span class="ir-node__title">
        {{ node.title || '推理步骤' }}
        <span v-if="ordinal" class="ir-node__ordinal">{{ ordinal }}</span>
      </span>
      <span v-if="displaySubtitle" class="ir-node__subtitle">{{ displaySubtitle }}</span>
      <svg
        v-if="expandable"
        class="ir-node__chevron"
        :class="{ 'ir-node__chevron--open': expanded }"
        viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"
      >
        <path d="M6 9l6 6 6-6" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </button>

    <div v-if="expanded" class="ir-node__body">
      <ul v-if="node.substeps && node.substeps.length" class="ir-node__substeps">
        <li v-for="(step, i) in node.substeps" :key="i" :class="`ir-node__substep--${step.status}`">
          <span class="ir-node__substep-dot" />
          <span>{{ step.desc }}</span>
        </li>
      </ul>
      <pre v-if="node.text" class="ir-node__text">{{ node.text }}</pre>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  node: { type: Object, required: true },
  ordinal: { type: String, default: '' },
})

const expandable = computed(() => Boolean(
  (props.node.substeps && props.node.substeps.length)
  || props.node.text
  || props.node.subtitle,
))

// 活动态默认展开，完成后折叠；用户可手动切换
const expanded = ref(props.node.open)

// 折叠的重复节点用保留的初始动作副标题（去掉“正在”），否则用当前副标题
const displaySubtitle = computed(() => {
  if (props.node.status === 'active') return props.node.subtitle
  return props.node.subtitle || props.node.actionSubtitle?.replace(/^正在/, '') || ''
})
</script>

<style scoped>
.ir-node {
  border-radius: var(--xc-radius-sm);
  padding: var(--xc-space-2) 0;
}
.ir-node__head {
  display: flex;
  align-items: center;
  gap: var(--xc-space-3);
  width: 100%;
  padding: 0;
  border: none;
  background: transparent;
  text-align: left;
  color: var(--xc-text-soft);
  cursor: default;
}
.ir-node__head--expandable { cursor: pointer; }
.ir-node__icon {
  flex: 0 0 auto;
  display: inline-flex;
  width: 16px;
  height: 16px;
}
.ir-node__icon svg { width: 16px; height: 16px; }
.ir-node__icon--active { color: var(--xc-accent-blue); }
.ir-node__icon--completed { color: var(--xc-status-ok); }
.ir-node__icon--waiting_user { color: var(--xc-status-warn); }
.ir-node__icon--aborted { color: var(--xc-status-danger); }
.ir-node__spin { animation: ir-node-spin 0.9s linear infinite; }
@keyframes ir-node-spin { to { transform: rotate(360deg); } }
.ir-node__title {
  flex: 0 0 auto;
  font-size: var(--xc-fs-sm);
  color: var(--xc-text-strong);
}
.ir-node__ordinal { color: var(--xc-text-mute); font-size: var(--xc-fs-2xs); margin-left: 2px; }
.ir-node__subtitle {
  flex: 1 1 auto;
  min-width: 0;
  font-size: var(--xc-fs-xs);
  color: var(--xc-text-mute);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ir-node__chevron { flex: 0 0 auto; width: 14px; height: 14px; color: var(--xc-text-mute); transition: transform var(--xc-dur-fast); }
.ir-node__chevron--open { transform: rotate(180deg); }
.ir-node__body { padding: var(--xc-space-2) 0 var(--xc-space-2) 28px; }
.ir-node__substeps { list-style: none; margin: 0 0 var(--xc-space-2); padding: 0; display: flex; flex-direction: column; gap: var(--xc-space-2); }
.ir-node__substeps li { display: flex; align-items: center; gap: var(--xc-space-2); font-size: var(--xc-fs-xs); color: var(--xc-text-soft); }
.ir-node__substep-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--xc-text-faint); }
.ir-node__substep--completed .ir-node__substep-dot { background: var(--xc-status-ok); }
.ir-node__substep--active .ir-node__substep-dot { background: var(--xc-accent-blue); }
.ir-node__text {
  margin: 0;
  max-height: 240px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: var(--xc-font-mono, monospace);
  font-size: var(--xc-fs-xs);
  line-height: var(--xc-lh-normal);
  color: var(--xc-text-soft);
}
</style>

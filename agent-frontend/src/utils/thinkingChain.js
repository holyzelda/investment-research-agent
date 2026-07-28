/**
 * 思考过程「节点链」reducer —— 框架无关，便于单测。
 *
 * 移植自 etrader-agent-nx 的 thinking-chain 语义：
 * - frameId 幂等/顺序守卫：过期帧丢弃
 * - 稳定节点身份：按 node_id upsert（非 append-only）
 * - 执行顺序独立于到达顺序：按 node_seq 排序
 * - 完成只由显式 node_status（completed/aborted）决定，text 结束不算完成
 * - substeps 作为服务端快照整体替换
 * - 仅最新 active 节点默认展开
 * - 流关闭时安全收尾：残余 active → completed 并折叠
 *
 * 事件负载（thinking 事件的内层 data）约定：
 * {
 *   text?, node_id, ref_node_id?, node_kind?, node_seq?,
 *   node_title?, node_subtitle?, node_status?,   // active|completed|aborted|waiting_user
 *   substeps?: [{ desc, status }]
 * }
 * 边界帧：无 text、有 node_status；token 帧：有 text、通常无 node_status。
 */

const TERMINAL = new Set(['completed', 'aborted'])

export function createThinkingState() {
  return { nodesById: {}, order: [], lastFrameId: -1 }
}

function parseFrameId(id) {
  if (id === null || id === undefined) return null
  const digits = String(id).replace(/\D/g, '')
  if (!digits) return null
  const n = Number(digits)
  return Number.isFinite(n) ? n : null
}

function insertBySeq(state, nodeId, seq) {
  const target = Number.isFinite(seq) ? seq : Number.MAX_SAFE_INTEGER
  let index = state.order.length
  for (let i = 0; i < state.order.length; i += 1) {
    const other = state.nodesById[state.order[i]]
    const otherSeq = Number.isFinite(other?.seq) ? other.seq : Number.MAX_SAFE_INTEGER
    if (target < otherSeq) { index = i; break }
  }
  state.order.splice(index, 0, nodeId)
}

/**
 * 应用一帧 thinking 事件。原地修改 state。
 * @param {object} state - createThinkingState() 的产物
 * @param {string|number|null} frameId - SSE id
 * @param {object} payload - thinking 内层负载
 */
export function applyThinkingFrame(state, frameId, payload) {
  if (!payload) return
  const fid = parseFrameId(frameId)
  if (fid !== null) {
    if (fid <= state.lastFrameId) return
    state.lastFrameId = fid
  }

  const nodeId = payload.node_id || payload.ref_node_id
  if (!nodeId) return

  let node = state.nodesById[nodeId]
  if (!node) {
    node = {
      nodeId,
      seq: Number.isFinite(payload.node_seq) ? payload.node_seq : null,
      kind: payload.node_kind || '',
      title: payload.node_title || '',
      status: 'active',
      subtitle: payload.node_subtitle || '',
      actionSubtitle: payload.node_subtitle || '',
      substeps: [],
      text: '',
      open: false,
    }
    state.nodesById[nodeId] = node
    insertBySeq(state, nodeId, node.seq)
  }

  const isBoundary = typeof payload.node_status === 'string' && payload.node_status !== ''

  if (isBoundary) {
    if (payload.node_title) node.title = payload.node_title
    if (Number.isFinite(payload.node_seq)) node.seq = payload.node_seq
    if (payload.node_kind) node.kind = payload.node_kind
    if (Array.isArray(payload.substeps)) node.substeps = payload.substeps.slice()
    if (payload.node_subtitle) {
      node.subtitle = payload.node_subtitle
      if (payload.node_status === 'active' && !node.actionSubtitle) {
        node.actionSubtitle = payload.node_subtitle
      }
    }
    node.status = payload.node_status
    if (payload.node_status === 'active') {
      // 最新 active 节点默认展开，其余折叠
      for (const id of state.order) state.nodesById[id].open = false
      node.open = true
    } else if (TERMINAL.has(payload.node_status)) {
      node.open = false
    }
  }

  if (typeof payload.text === 'string' && payload.text) {
    node.text += payload.text
  }
}

/** 流关闭安全收尾：残余 active → completed 并折叠；waiting_user 保留。 */
export function finalizeThinking(state) {
  for (const id of state.order) {
    const node = state.nodesById[id]
    if (node.status === 'active') {
      node.status = 'completed'
      node.open = false
    }
  }
}

/** 渲染用有序节点数组。 */
export function thinkingNodes(state) {
  return state.order.map((id) => state.nodesById[id])
}

/** 是否仍有 active 节点（用于计时/loading 判定）。 */
export function hasActiveNode(state) {
  return state.order.some((id) => state.nodesById[id].status === 'active')
}

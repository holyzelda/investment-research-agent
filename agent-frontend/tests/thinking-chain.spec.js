import { describe, expect, it } from 'vitest'
import { applyThinkingFrame, createThinkingState, finalizeThinking, thinkingNodes } from '@/utils/thinkingChain'

describe('thinkingChain', () => {
  it('upserts nodes, orders by sequence and appends tokens', () => {
    const state = createThinkingState()
    applyThinkingFrame(state, 1, { node_id: 'b', node_seq: 2, node_title: '第二步', node_status: 'active' })
    applyThinkingFrame(state, 2, { node_id: 'a', node_seq: 1, node_title: '第一步', node_status: 'active' })
    applyThinkingFrame(state, 3, { node_id: 'a', text: '甲' })
    applyThinkingFrame(state, 4, { node_id: 'a', text: '乙' })

    expect(thinkingNodes(state).map((node) => node.nodeId)).toEqual(['a', 'b'])
    expect(state.nodesById.a.text).toBe('甲乙')
    expect(state.nodesById.a.open).toBe(true)
    expect(state.nodesById.b.open).toBe(false)
  })

  it('ignores duplicate frames and replaces substep snapshots', () => {
    const state = createThinkingState()
    applyThinkingFrame(state, 10, { node_id: 'a', node_status: 'active', substeps: [{ desc: '旧', status: 'active' }] })
    applyThinkingFrame(state, 10, { node_id: 'a', text: '重复' })
    applyThinkingFrame(state, 11, { node_id: 'a', node_status: 'active', substeps: [{ desc: '新', status: 'completed' }] })

    expect(state.nodesById.a.text).toBe('')
    expect(state.nodesById.a.substeps).toEqual([{ desc: '新', status: 'completed' }])
  })

  it('finalizes active nodes but preserves waiting_user', () => {
    const state = createThinkingState()
    applyThinkingFrame(state, 1, { node_id: 'a', node_status: 'active' })
    applyThinkingFrame(state, 2, { node_id: 'b', node_status: 'waiting_user' })
    finalizeThinking(state)

    expect(state.nodesById.a).toMatchObject({ status: 'completed', open: false })
    expect(state.nodesById.b.status).toBe('waiting_user')
  })
})

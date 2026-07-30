import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ThinkingChain from '@/views/home/components/ThinkingChain.vue'

const THINKING_NODE_SOURCE = readFileSync(
  resolve(process.cwd(), 'src/views/home/components/ThinkingNodeItem.vue'),
  'utf8',
)

const NODE = {
  nodeId: 'n1',
  title: '识别项目参数',
  status: 'completed',
  open: false,
  substeps: [],
  text: '',
}

describe('ThinkingChain component', () => {
  it('stays open while streaming', () => {
    const wrapper = mount(ThinkingChain, {
      props: { nodes: [NODE], streaming: true, startedAt: Date.now() - 1000 },
    })

    expect(wrapper.find('.ir-thinking__body').exists()).toBe(true)
    expect(wrapper.find('.ir-thinking__header--toggleable').exists()).toBe(false)
    wrapper.unmount()
  })

  it('rotates the active node icon around its own center', () => {
    const wrapper = mount(ThinkingChain, {
      props: {
        nodes: [{ ...NODE, status: 'active', open: true }],
        streaming: true,
        hasActive: true,
        startedAt: Date.now() - 1000,
      },
    })

    expect(wrapper.find('.ir-node__spin').exists()).toBe(true)
    expect(THINKING_NODE_SOURCE).toMatch(/\.ir-node__spin\s*\{[^}]*animation:\s*ir-node-spin/)
    expect(THINKING_NODE_SOURCE).toMatch(/\.ir-node__spin\s*\{[^}]*transform-origin:\s*center/)
    expect(THINKING_NODE_SOURCE).toMatch(/\.ir-node__spin\s*\{[^}]*transform-box:\s*fill-box/)
    wrapper.unmount()
  })

  it('animates subtitle changes for the active node', () => {
    expect(THINKING_NODE_SOURCE).toContain('<Transition name="ir-node-subtitle" mode="out-in">')
    expect(THINKING_NODE_SOURCE).toContain(':key="displaySubtitle"')
    expect(THINKING_NODE_SOURCE).toContain('.ir-node-subtitle-enter-active,.ir-node-subtitle-leave-active')
    expect(THINKING_NODE_SOURCE).toContain('.ir-node-subtitle-enter-from')
    expect(THINKING_NODE_SOURCE).toContain('.ir-node-subtitle-leave-to')
  })

  it('defaults to collapsed when terminal and toggles from the header', async () => {
    const wrapper = mount(ThinkingChain, {
      props: { nodes: [NODE], streaming: false, startedAt: 1000, finishedAt: 2000 },
    })

    expect(wrapper.find('.ir-thinking__body').exists()).toBe(false)
    expect(wrapper.find('.ir-thinking__header--toggleable').exists()).toBe(true)
    await wrapper.find('.ir-thinking__header').trigger('click')
    expect(wrapper.find('.ir-thinking__body').exists()).toBe(true)
    wrapper.unmount()
  })
})

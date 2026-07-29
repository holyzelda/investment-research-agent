import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ThinkingChain from '@/views/home/components/ThinkingChain.vue'

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

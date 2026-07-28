import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AiAnswerContent from '@/views/home/components/AiAnswerContent.vue'

describe('AiAnswerContent', () => {
  it('preserves line breaks and renders unsafe markup as text', () => {
    const wrapper = mount(AiAnswerContent, {
      props: { text: '第一行\n<script>alert(1)</script>' },
    })

    expect(wrapper.find('.ir-ai-answer__text').text()).toContain('第一行')
    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.html()).toContain('&lt;script&gt;alert(1)&lt;/script&gt;')
  })

  it('renders fallback and a shared action slot', () => {
    const wrapper = mount(AiAnswerContent, {
      props: { fallback: '智能分析暂未生成' },
      slots: { actions: '<button type="button">查看报告</button>' },
    })

    expect(wrapper.text()).toContain('智能分析暂未生成')
    expect(wrapper.find('button').text()).toBe('查看报告')
  })
})

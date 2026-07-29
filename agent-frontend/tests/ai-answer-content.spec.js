import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AiAnswerContent from '@/views/home/components/AiAnswerContent.vue'

describe('AiAnswerContent', () => {
  it('renders Markdown structure and inline scrollable tables', () => {
    const wrapper = mount(AiAnswerContent, {
      props: {
        text: '# 投资结论\n\n**建议复核**\n\n- 收益边界\n- 成本边界\n\n| 指标 | 数值 |\n| --- | ---: |\n| IRR | 8.6% |',
      },
    })

    expect(wrapper.find('h1').text()).toBe('投资结论')
    expect(wrapper.find('strong').text()).toBe('建议复核')
    expect(wrapper.findAll('li').map((item) => item.text())).toEqual(['收益边界', '成本边界'])
    expect(wrapper.find('table').exists()).toBe(true)
    expect(wrapper.findAll('th').map((cell) => cell.text())).toEqual(['指标', '数值'])
    expect(wrapper.find('.ir-ai-answer__markdown').exists()).toBe(true)
  })

  it('disables raw HTML while preserving the literal content', () => {
    const wrapper = mount(AiAnswerContent, {
      props: { text: '第一行\n<script>alert(1)</script>\n<img src=x onerror=alert(2)>' },
    })

    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.text()).toContain('<script>alert(1)</script>')
    expect(wrapper.text()).toContain('<img src=x onerror=alert(2)>')
  })

  it('renders fallback, error state and a shared action slot', () => {
    const wrapper = mount(AiAnswerContent, {
      props: { fallback: '**智能分析暂未生成**', error: true },
      slots: { actions: '<button type="button">查看报告</button>' },
    })

    expect(wrapper.find('strong').text()).toBe('智能分析暂未生成')
    expect(wrapper.classes()).toContain('ir-ai-answer--error')
    expect(wrapper.find('button').text()).toBe('查看报告')
  })
})

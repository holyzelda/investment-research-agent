import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ReportAiAnalysis from '@/views/report/components/ReportAiAnalysis.vue'
import { renderReportMarkdown } from '@/views/report/utils/renderReportMarkdown'

describe('report markdown renderer', () => {
  it('renders the approved report markdown subset', () => {
    const html = renderReportMarkdown('## 核心结论\n\n**收益稳定**\n\n- 风险可控\n\n> 关注政策\n\n`IRR`')
    expect(html).toContain('<h2>核心结论</h2>')
    expect(html).toContain('<strong>收益稳定</strong>')
    expect(html).toContain('<ul>')
    expect(html).toContain('<blockquote>')
    expect(html).toContain('<code>IRR</code>')
  })

  it('escapes raw html and removes link interactivity', () => {
    const html = renderReportMarkdown('<script>alert(1)</script>\n\n[政策来源](https://example.com)\n\n![图](x)')
    expect(html).toContain('&lt;script&gt;alert(1)&lt;/script&gt;')
    expect(html).not.toContain('<script>')
    expect(html).not.toContain('<a')
    expect(html).toContain('政策来源')
    expect(html).not.toContain('<img')
  })

  it('uses fallback content in the report-only analysis card', () => {
    const wrapper = mount(ReportAiAnalysis, { props: { text: '', fallback: '**暂未生成**' } })
    expect(wrapper.text()).toContain('AI 智能分析')
    expect(wrapper.find('strong').text()).toBe('暂未生成')
  })
})

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('element-plus', () => ({
  ElDialog: {},
  ElPopover: { template: '<div class="el-popover-stub"><slot name="reference" /><slot /></div>' },
}))
vi.mock('element-plus/es', () => ({
  ElDialog: {},
  ElPopover: { template: '<div class="el-popover-stub"><slot name="reference" /><slot /></div>' },
}))
import ConsultationComposer from '@/views/policy-market/components/ConsultationComposer.vue'
import ConsultationHistory from '@/views/policy-market/components/ConsultationHistory.vue'
import ConsultationResult from '@/views/policy-market/components/ConsultationResult.vue'
import MarketPulse from '@/views/policy-market/components/MarketPulse.vue'

const createNews = (count) => Array.from({ length: count }, (_, index) => ({
  id: index + 1,
  title: `资讯 ${index + 1}`,
  publishTime: '2026-07-23T09:00:00',
  tags: [],
}))

let animationCallback
let animationId

beforeEach(() => {
  animationCallback = null
  animationId = 0
  vi.stubGlobal('requestAnimationFrame', vi.fn((callback) => {
    animationCallback = callback
    animationId += 1
    return animationId
  }))
  vi.stubGlobal('cancelAnimationFrame', vi.fn())
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('政策与市场咨询组件', () => {
  it('历史列表发出新建、选择和删除事件，删除不触发选择', async () => {
    const wrapper = mount(ConsultationHistory, { props: { consultations: [{ id: 'c-1', title: '新能源消纳政策有何变化？', createdAt: '2026-07-23T10:42:00+08:00' }], selectedId: 'c-1' } })
    await wrapper.get('[aria-label="新建提问"]').trigger('click')
    await wrapper.get('[data-consultation-id="c-1"]').trigger('click')
    await wrapper.get('[aria-label="删除研究记录"]').trigger('click')

    expect(wrapper.emitted('new-question')).toHaveLength(1)
    expect(wrapper.emitted('select')).toEqual([['c-1']])
    expect(wrapper.emitted('delete')).toEqual([['c-1']])
  })

  it('快捷问题填入输入框，Ctrl+Enter 发出提交事件', async () => {
    const wrapper = mount(ConsultationComposer)
    await wrapper.get('[data-quick-question]').trigger('click')
    expect(wrapper.get('textarea').element.value).toBeTruthy()
    await wrapper.get('textarea').trigger('keydown', { key: 'Enter', ctrlKey: true })
    expect(wrapper.emitted('submit-question')?.[0]?.[0]).toBeTruthy()
  })

  it('空输入不提交并显示结果区空态', async () => {
    const composer = mount(ConsultationComposer)
    const result = mount(ConsultationResult, { props: { consultation: null } })
    await composer.get('[aria-label="提交咨询"]').trigger('click')
    expect(composer.emitted('submit-question')).toBeUndefined()
    expect(result.text()).toContain('等待研究问题')
  })

  it('按咨询状态显示处理中、失败和完成结果', () => {
    const processing = mount(ConsultationResult, { props: { consultation: { status: 'processing', question: '问题' } } })
    const failed = mount(ConsultationResult, { props: { consultation: { status: 'failed', question: '问题', answer: '' } } })
    const completed = mount(ConsultationResult, {
      props: {
        consultation: {
          status: 'completed', title: '问题', answer: '回答[1]。',
          sourceData: {
            references: [
              { index: 1, title: '宁夏调频细则', url: 'https://example.test/source', token: 'tk', type: 'wiki' },
            ],
          },
        },
      },
    })
    expect(processing.text()).toContain('正在分析')
    expect(failed.text()).toContain('咨询失败')
    expect(completed.text()).toContain('回答')
    expect(completed.text()).toContain('宁夏调频细则')
    // 结果区只保留结论与源文件，检索元信息不再展示
    expect(completed.text()).not.toContain('覆盖范围')
    expect(completed.text()).not.toContain('数据时点')
    expect(completed.text()).not.toContain('核验状态')
    expect(completed.text()).not.toContain('案卷状态')
  })

  it('正文角标渲染为可点击按钮并定位到对应来源行', async () => {
    const wrapper = mount(ConsultationResult, {
      attachTo: document.body,
      props: {
        consultation: {
          status: 'completed', title: '问题', answer: '容量补偿 0.28 元/kWh[1]。调频另有细则[2]。',
          sourceData: {
            references: [
              { index: 1, title: '容量电费实施细则', url: 'https://example.test/cap', type: 'wiki' },
              { index: 2, title: '某新闻报道', url: 'https://example.test/news', type: 'web' },
            ],
          },
        },
      },
    })

    const cites = wrapper.findAll('.pm-cite')
    expect(cites.map((node) => node.text())).toEqual(['1', '2'])
    // 来源行带锚点 id，角标点击靠它定位
    expect(wrapper.find('#pm-source-1').exists()).toBe(true)
    expect(wrapper.find('#pm-source-2').exists()).toBe(true)
    // 来源类型区分知识库与联网，用户据此判断可信度
    expect(wrapper.text()).toContain('知识库')
    expect(wrapper.text()).toContain('联网')

    await cites[1].trigger('click')
    expect(wrapper.find('#pm-source-2').classes()).toContain('is-highlighted')
    expect(wrapper.find('#pm-source-1').classes()).not.toContain('is-highlighted')

    wrapper.unmount()
  })

  it('有 references 时不渲染历史 sources 的重复条目', () => {
    const wrapper = mount(ConsultationResult, {
      props: {
        consultation: {
          status: 'completed', title: '问题', answer: '回答[1]。',
          sourceData: {
            sources: ['https://example.test/source'],
            references: [{ index: 1, title: '某细则', url: 'https://example.test/source', type: 'wiki' }],
          },
        },
      },
    })

    expect(wrapper.findAll('.pm-result__ref')).toHaveLength(1)
    expect(wrapper.text()).toContain('某细则')
  })

  it('历史记录只有 sources 时归一化进编号来源列表', () => {
    const wrapper = mount(ConsultationResult, {
      props: {
        consultation: {
          status: 'completed', title: '问题', answer: '旧回答',
          sourceData: { sources: ['https://example.test/legacy'] },
        },
      },
    })

    expect(wrapper.findAll('.pm-result__ref')).toHaveLength(1)
    expect(wrapper.text()).toContain('https://example.test/legacy')
  })

  it('没有任何来源时给出空态说明', () => {
    const wrapper = mount(ConsultationResult, {
      props: { consultation: { status: 'completed', title: '问题', answer: '方向性回答。', sourceData: {} } },
    })

    expect(wrapper.findAll('.pm-result__ref')).toHaveLength(0)
    expect(wrapper.text()).toContain('没有可引用的源文件')
  })

  it('案卷阅读模式不重复渲染当前问题标题', () => {
    const wrapper = mount(ConsultationResult, {
      props: { consultation: { status: 'completed', title: '问题', answer: '完整回答' }, readerMode: true },
    })
    expect(wrapper.text()).toContain('完整回答')
    expect(wrapper.text()).not.toContain('关于「问题」')
  })

  it('动态资讯主题和真实趋势按接口结果展示', () => {
    const wrapper = mount(MarketPulse, {
      props: {
        filters: { province: 'all', period: 'all', topic: '储能' },
        topicOptions: [{ value: '储能', label: '储能', count: 8 }],
        stats: { total: 8, trendPercent: -12.5, rangeLabel: '内蒙古 · 本月' },
      },
    })

    expect(wrapper.get('[data-filter="topic"]').text()).toContain('储能')
    expect(wrapper.text()).toContain('条资讯')
    expect(wrapper.text()).toContain('较上期 -12.5%')
  })

  it('无可比数据时显示对应趋势状态', () => {
    const wrapper = mount(MarketPulse, { props: { stats: { total: 0, trendPercent: null, rangeLabel: '全部省份 · 全部时间' } } })
    expect(wrapper.text()).toContain('暂无可比数据')
  })

  it('自定义筛选菜单发出完整筛选条件，并展示完整省份选项', async () => {
    const wrapper = mount(MarketPulse, { props: { filters: { province: 'all', period: 'all', topic: 'all' }, news: [] } })
    await wrapper.get('[data-filter="province"]').trigger('click')
    expect(wrapper.find('[data-test="province-北京"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="province-广西"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="province-新疆"]').exists()).toBe(true)
    expect(wrapper.findAll('[data-test^="province-"]')).toHaveLength(35)

    await wrapper.get('[data-test="province-内蒙古"]').trigger('click')

    expect(wrapper.emitted('filters-change')?.[0]?.[0]).toEqual({ province: '内蒙古', period: 'all', topic: 'all' })
  })

  it('市场脉搏显示标签和安全外链，不显示横向滚动资讯', () => {
    const wrapper = mount(MarketPulse, { props: { news: [{ id: 1, title: '置顶储能政策', linkUrl: 'https://example.test/top', publishTime: '2026-07-23T09:00:00', tags: ['政策', '储能'] }] } })
    expect(wrapper.text()).toContain('置顶储能政策')
    expect(wrapper.text()).toContain('政策')
    expect(wrapper.find('.pm-pulse__ticker').exists()).toBe(false)
    const item = wrapper.get('[data-news-id="1"]')
    expect(item.attributes('href')).toBe('https://example.test/top')
    expect(item.attributes('target')).toBe('_blank')
    expect(item.attributes('rel')).toBe('noopener noreferrer')
  })

  it('无链接资讯不渲染为可跳转链接', () => {
    const wrapper = mount(MarketPulse, { props: { news: [{ id: 2, title: '无链接资讯', publishTime: '2026-07-23T09:00:00', tags: [] }] } })
    const item = wrapper.get('[data-news-id="2"]')
    expect(item.element.tagName).toBe('DIV')
    expect(item.attributes('href')).toBeUndefined()
  })

  it('资讯超过五条时全部渲染在内部滚动区域，不再提供查看全部入口', async () => {
    const wrapper = mount(MarketPulse, { props: { news: createNews(6) } })
    expect(wrapper.findAll('[data-news-id]')).toHaveLength(6)
    expect(wrapper.find('[data-view-all-news]').exists()).toBe(false)
  })

  it('资讯不超过五条时同样不显示查看全部入口', () => {
    const wrapper = mount(MarketPulse, { props: { news: createNews(5) } })
    expect(wrapper.find('[data-view-all-news]').exists()).toBe(false)
  })

  it('异步加载资讯并完成浏览器帧布局后自动启动内部滚动', async () => {
    const wrapper = mount(MarketPulse, { props: { news: [] } })
    const list = wrapper.get('[data-news-scroll]')
    Object.defineProperty(list.element, 'scrollHeight', { value: 960 })
    Object.defineProperty(list.element, 'clientHeight', { value: 432 })
    list.element.scrollTop = 0
    await wrapper.vm.$nextTick()
    animationCallback = null

    await wrapper.setProps({ news: createNews(6) })
    await wrapper.vm.$nextTick()

    expect(animationCallback).not.toBeNull()
    const layoutCallback = animationCallback
    layoutCallback(1000)
    expect(animationCallback).not.toBeNull()
    animationCallback(2000)
    expect(list.element.scrollTop).toBe(60)
  })

  it('资讯溢出且鼠标离开时自动推进内部滚动位置', async () => {
    const wrapper = mount(MarketPulse, { props: { news: createNews(6) } })
    const list = wrapper.get('[data-news-scroll]')
    Object.defineProperty(list.element, 'scrollHeight', { value: 960 })
    Object.defineProperty(list.element, 'clientHeight', { value: 432 })
    list.element.scrollTop = 0

    await list.trigger('mouseleave')
    animationCallback(1000)
    animationCallback(1016)

    expect(list.element.scrollTop).toBeGreaterThan(0)
  })

  it('自动滚动到底部停留后回到顶部并开始下一轮', async () => {
    vi.useFakeTimers()
    const wrapper = mount(MarketPulse, { props: { news: createNews(6) } })
    const list = wrapper.get('[data-news-scroll]').element
    Object.defineProperty(list, 'scrollHeight', { value: 960 })
    Object.defineProperty(list, 'clientHeight', { value: 432 })
    list.scrollTop = 527

    await wrapper.get('[data-news-scroll]').trigger('mouseleave')
    animationCallback(1000)
    animationCallback(1017)
    expect(list.scrollTop).toBeCloseTo(528, 1)

    await vi.advanceTimersByTimeAsync(1200)

    expect(list.scrollTop).toBe(0)
    expect(requestAnimationFrame).toHaveBeenCalled()
  })

  it('资讯区悬停时暂停自动滚动', async () => {
    const wrapper = mount(MarketPulse, { props: { news: createNews(6) } })
    const list = wrapper.get('[data-news-scroll]')
    Object.defineProperty(list.element, 'scrollHeight', { value: 960 })
    Object.defineProperty(list.element, 'clientHeight', { value: 432 })

    await list.trigger('mouseleave')
    await list.trigger('mouseenter')

    expect(cancelAnimationFrame).toHaveBeenCalled()
  })
})

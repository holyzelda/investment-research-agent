import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('element-plus', () => ({ ElDialog: {} }))
vi.mock('element-plus/es', () => ({ ElDialog: {} }))
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
  it('历史列表发出新建和选择事件，不渲染删除动作', async () => {
    const wrapper = mount(ConsultationHistory, { props: { consultations: [{ id: 'c-1', title: '新能源消纳政策有何变化？', createdAt: '2026-07-23T10:42:00+08:00' }], selectedId: 'c-1' } })
    expect(wrapper.text()).not.toContain('删除')
    await wrapper.get('[aria-label="新建提问"]').trigger('click')
    await wrapper.get('[data-consultation-id="c-1"]').trigger('click')
    expect(wrapper.emitted('new-question')).toHaveLength(1)
    expect(wrapper.emitted('select')).toEqual([['c-1']])
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
    expect(result.text()).toContain('你的咨询结果将展示在这里')
  })

  it('按咨询状态显示处理中、失败和完成结果', () => {
    const processing = mount(ConsultationResult, { props: { consultation: { status: 'processing', question: '问题' } } })
    const failed = mount(ConsultationResult, { props: { consultation: { status: 'failed', question: '问题', answer: '' } } })
    const completed = mount(ConsultationResult, { props: { consultation: { status: 'completed', title: '问题', answer: '回答', sourceScope: ['政策文件'] } } })
    expect(processing.text()).toContain('正在分析')
    expect(failed.text()).toContain('咨询失败')
    expect(completed.text()).toContain('回答')
    expect(completed.text()).toContain('政策文件')
  })

  it('筛选变化时发出完整筛选条件', async () => {
    const wrapper = mount(MarketPulse, { props: { filters: { province: 'all', period: 'all', topic: 'all' }, stats: { total: 186, trend: 9.3, rangeLabel: '内蒙古' }, news: [] } })
    await wrapper.get('[data-filter="province"]').setValue('内蒙古')
    expect(wrapper.emitted('filters-change')?.[0]?.[0]).toMatchObject({ province: '内蒙古' })
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

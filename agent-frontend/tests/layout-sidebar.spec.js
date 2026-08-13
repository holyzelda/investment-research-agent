import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import AppSidebar from '@/layout/components/AppSidebar.vue'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('AppShell conversation history', () => {
  it('keeps a stable shell surface in expanded and compact states', async () => {
    const wrapper = mount(AppSidebar, { props: { collapsed: false } })

    expect(wrapper.find('.ir-shell-wrap').exists()).toBe(true)
    expect(wrapper.find('[data-testid="app-shell"]').exists()).toBe(true)
    expect(wrapper.find('.ir-shell-wrap').classes()).not.toContain('is-collapsed')

    await wrapper.setProps({ collapsed: true })
    expect(wrapper.find('.ir-shell-wrap').classes()).toContain('is-collapsed')
  })

  it('shows month/day labels for older conversations', () => {
    const wrapper = mount(AppSidebar, {
      props: {
        history: [
          { conversationId: 7, title: '甘肃 200MW/800MWh', createdAt: '2020-01-05T09:00:00' },
        ],
      },
    })

    expect(wrapper.find('.ir-shell__history-date').text()).toBe('1/5')
  })

  it('labels conversations created today and yesterday', () => {
    const iso = (date) =>
      `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}T08:00:00`
    const today = new Date()
    const yesterday = new Date()
    yesterday.setDate(today.getDate() - 1)
    const wrapper = mount(AppSidebar, {
      props: {
        history: [
          { conversationId: 1, title: '今日会话', createdAt: iso(today) },
          { conversationId: 2, title: '昨日会话', createdAt: iso(yesterday) },
        ],
      },
    })

    const labels = wrapper.findAll('.ir-shell__history-date').map((node) => node.text())
    expect(labels).toEqual(['今日', '昨天'])
  })

  it('keeps rename and delete actions separate from opening a history item', async () => {
    const conversation = { conversationId: 7, title: '甘肃 200MW/800MWh', createdAt: '2020-01-05T09:00:00' }
    const wrapper = mount(AppSidebar, { props: { history: [conversation] } })

    await wrapper.find('.ir-shell__history-edit').trigger('click')
    await wrapper.find('.ir-shell__history-delete').trigger('click')

    expect(wrapper.emitted('rename-history')).toEqual([[conversation]])
    expect(wrapper.emitted('delete-history')).toEqual([[7]])
    expect(wrapper.emitted('open-history')).toBeUndefined()
  })

  it('opens the user menu and emits its selected action', async () => {
    const wrapper = mount(AppSidebar, { props: { username: '测试用户' } })
    const trigger = wrapper.find('.ir-shell__user')

    expect(trigger.attributes('aria-expanded')).toBe('false')
    await trigger.trigger('click')
    expect(trigger.attributes('aria-expanded')).toBe('true')
    expect(wrapper.find('.ir-shell__user-menu').exists()).toBe(true)

    await wrapper.find('[role="menuitem"]').trigger('click')
    expect(wrapper.emitted('user-menu')).toEqual([['ledger']])
    expect(wrapper.find('.ir-shell__user-menu').exists()).toBe(false)
  })

  it('observes the load-more sentinel after asynchronous history pagination appears', async () => {
    const observe = vi.fn()
    const disconnect = vi.fn()
    const IntersectionObserver = vi.fn(function IntersectionObserver(callback, options) {
      this.observe = observe
      this.disconnect = disconnect
      this.callback = callback
      this.options = options
    })
    vi.stubGlobal('IntersectionObserver', IntersectionObserver)
    const wrapper = mount(AppSidebar, {
      props: {
        history: [{ conversationId: 7, title: '甘肃 200MW/800MWh' }],
        hasMore: false,
      },
    })

    await wrapper.setProps({ hasMore: true })

    const sentinel = wrapper.find('.ir-shell__history-sentinel')
    expect(sentinel.exists()).toBe(true)
    expect(IntersectionObserver).toHaveBeenCalledOnce()
    expect(IntersectionObserver.mock.calls[0][1].root).toBe(wrapper.find('.ir-shell__history-list').element)
    expect(observe).toHaveBeenCalledWith(sentinel.element)

    IntersectionObserver.mock.instances[0].callback([{ isIntersecting: true }])
    expect(wrapper.emitted('load-more')).toEqual([[]])
  })
})

import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AppSidebar from '@/layout/components/AppSidebar.vue'

const stubs = {
  transition: false,
}

describe('地图页历史会话栏', () => {
  it('默认不传 hidden 时保留完整会话栏', () => {
    const wrapper = mount(AppSidebar, {
      props: { history: [] },
      global: { stubs },
    })

    expect(wrapper.find('.ir-sider-wrap').exists()).toBe(true)
    expect(wrapper.text()).toContain('历史会话')
  })

  it('marks the history panel as the desktop history navigation surface', () => {
    const wrapper = mount(AppSidebar, {
      props: { history: [] },
      global: { stubs },
    })

    expect(wrapper.find('[data-testid="history-sidebar"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('查看全部历史会话')
    expect(wrapper.find('[data-testid="all-history-link"]').exists()).toBe(false)
  })

  it('hidden 时不占用侧栏布局，且可由父级展开', async () => {
    const wrapper = mount(AppSidebar, {
      props: { hidden: true, canHide: true },
      global: { stubs },
    })

    expect(wrapper.find('.ir-sider-wrap').exists()).toBe(false)

    await wrapper.setProps({ hidden: false })
    expect(wrapper.find('.ir-sider-wrap').exists()).toBe(true)
    await wrapper.find('.ir-sider__hide').trigger('click')
    expect(wrapper.emitted('visibility-change')).toEqual([[true]])
  })

  it('每条历史前展示时间标签：过往会话显示 月/日', () => {
    const wrapper = mount(AppSidebar, {
      props: {
        history: [
          { conversationId: 7, title: '甘肃 200MW/800MWh', createdAt: '2020-01-05T09:00:00' },
        ],
      },
      global: { stubs },
    })

    expect(wrapper.find('.ir-sider__hist-date').text()).toBe('1/5')
  })

  it('今日与昨天的会话分别标注「今日」「昨天」', () => {
    const iso = (d) =>
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}T08:00:00`
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
      global: { stubs },
    })

    const labels = wrapper.findAll('.ir-sider__hist-date').map((n) => n.text())
    expect(labels).toEqual(['今日', '昨天'])
  })

  it('悬浮操作区提供编辑标题与删除两个图标，替代原三点菜单', () => {
    const wrapper = mount(AppSidebar, {
      props: {
        history: [
          { conversationId: 7, title: '甘肃 200MW/800MWh', createdAt: '2020-01-05T09:00:00' },
        ],
      },
      global: { stubs },
    })

    expect(wrapper.find('.ir-sider__hist-edit').exists()).toBe(true)
    expect(wrapper.find('.ir-sider__hist-delete').exists()).toBe(true)
    expect(wrapper.find('.ir-sider__hist-more').exists()).toBe(false)
  })
})

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
})

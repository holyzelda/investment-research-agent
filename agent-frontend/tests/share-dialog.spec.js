import { describe, expect, it, vi } from 'vitest'
import { shallowMount, mount } from '@vue/test-utils'
import { nextTick } from 'vue'

const api = vi.hoisted(() => ({
  createShare: vi.fn(),
  listShares: vi.fn(),
  revokeShare: vi.fn(),
}))

const message = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
}))

vi.mock('@/api/calc', () => api)
vi.mock('element-plus', () => {
  const ElMessage = message
  const ElRadioGroup = { name: 'ElRadioGroup', template: '<div class="el-radio-group-stub"><slot /></div>', props: ['modelValue'] }
  const ElRadioButton = { name: 'ElRadioButton', template: '<label class="el-radio-button-stub" @click="$emit(\'click\')"><slot /></label>', props: ['value'] }
  const ElDialog = { name: 'ElDialog', template: '<div class="ir-share-dialog"><slot /></div>', props: ['modelValue'], emits: ['update:modelValue'] }
  const ElButton = { name: 'ElButton', template: '<button :class="$attrs.class" :loading="$attrs.loading" @click="$emit(\'click\')"><slot /></button>', props: ['loading', 'type', 'size', 'plain'] }
  const ElLoadingDirective = { mounted() {}, unmounted() {} }
  return { ElMessage, ElRadioGroup, ElRadioButton, ElDialog, ElButton, ElLoadingDirective, default: {} }
})

import ShareDialog from '@/views/home/components/ShareDialog.vue'

describe('ShareDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  function createWrapper(props = {}) {
    return mount(ShareDialog, {
      props: {
        visible: true,
        conversationId: 'conv-1',
        taskId: 42,
        version: 'V1',
        ...props,
      },
    })
  }

  it('shows create form when no shares exist', async () => {
    api.listShares.mockResolvedValue({ data: [] })

    const wrapper = createWrapper()
    await nextTick()

    expect(wrapper.text()).toContain('生成分享链接')
    expect(wrapper.text()).toContain('有效期')
  })

  it('loads shares on mount when visible and taskId is provided', async () => {
    api.listShares.mockResolvedValue({ data: [] })

    createWrapper()
    await nextTick()

    expect(api.listShares).toHaveBeenCalledWith('conv-1', 42)
  })

  it('does not load shares when taskId is missing', async () => {
    api.listShares.mockResolvedValue({ data: [] })

    mount(ShareDialog, {
      props: { visible: true, conversationId: 'conv-1', taskId: null, version: 'V1' },
    })
    await nextTick()

    expect(api.listShares).not.toHaveBeenCalled()
  })

  it('shows active share state with link and revoke button', async () => {
    const future = new Date(Date.now() + 86400000 * 7).toISOString()
    api.listShares.mockResolvedValue({
      data: [
        {
          id: 1,
          shareCode: 'abc123',
          durationDays: 7,
          expiresAt: future,
          revokedAt: null,
          createdAt: new Date().toISOString(),
        },
      ],
    })

    const wrapper = createWrapper()
    await nextTick()

    expect(wrapper.text()).toContain('分享已生效')
    expect(wrapper.find('input.ir-share__link-input').element.value).toContain('abc123')
    expect(wrapper.text()).toContain('撤销分享')
    expect(wrapper.text()).toContain('有效期至')
  })

  it('shows expired state when share has expired', async () => {
    const past = new Date(Date.now() - 86400000).toISOString()
    api.listShares.mockResolvedValue({
      data: [
        {
          id: 1,
          shareCode: 'expired-code',
          durationDays: 7,
          expiresAt: past,
          revokedAt: null,
          createdAt: new Date(Date.now() - 86400000 * 8).toISOString(),
        },
      ],
    })

    const wrapper = createWrapper()
    await nextTick()

    expect(wrapper.text()).toContain('分享链接已过期')
    expect(wrapper.text()).toContain('重新生成分享链接')
  })

  it('shows revoked state when share has been revoked', async () => {
    api.listShares.mockResolvedValue({
      data: [
        {
          id: 1,
          shareCode: 'revoked-code',
          durationDays: 7,
          expiresAt: new Date(Date.now() + 86400000).toISOString(),
          revokedAt: new Date().toISOString(),
          createdAt: new Date().toISOString(),
        },
      ],
    })

    const wrapper = createWrapper()
    await nextTick()

    expect(wrapper.text()).toContain('分享已撤销')
    expect(wrapper.text()).toContain('重新生成分享链接')
  })

  it('creates a share and shows the link', async () => {
    api.listShares.mockResolvedValue({ data: [] })
    api.createShare.mockResolvedValue({
      data: {
        data: {
          shareCode: 'new-share-code',
          shareId: 2,
          durationDays: 7,
          expiresAt: new Date(Date.now() + 86400000 * 7).toISOString(),
          createdAt: new Date().toISOString(),
        },
      },
    })

    const wrapper = createWrapper()
    await nextTick()

    await wrapper.find('.ir-share__primary-btn').trigger('click')

    expect(api.createShare).toHaveBeenCalledWith(42, 7)
    await nextTick()

    expect(wrapper.text()).toContain('分享已生效')
    expect(wrapper.find('input.ir-share__link-input').element.value).toContain('new-share-code')
    expect(message.success).toHaveBeenCalledWith('分享链接已生成')
  })

  it('uses the request interceptor response shape when creating a share', async () => {
    api.listShares.mockResolvedValue({ data: [] })
    api.createShare.mockResolvedValue({
      code: 200,
      data: {
        shareCode: 'direct-share-code',
        shareId: 3,
        shareUrl: '/investment/public/calculation-shares/direct-share-code',
        durationDays: 7,
        expiresAt: new Date(Date.now() + 86400000 * 7).toISOString(),
      },
    })

    const wrapper = createWrapper()
    await nextTick()
    await wrapper.find('.ir-share__primary-btn').trigger('click')
    await nextTick()

    expect(wrapper.text()).toContain('分享已生效')
    expect(wrapper.find('input.ir-share__link-input').element.value).toContain('direct-share-code')
  })

  it('revokes an active share', async () => {
    const future = new Date(Date.now() + 86400000 * 7).toISOString()
    api.listShares.mockResolvedValue({
      data: [
        {
          id: 1,
          shareCode: 'abc123',
          durationDays: 7,
          expiresAt: future,
          revokedAt: null,
          createdAt: new Date().toISOString(),
        },
      ],
    })
    api.revokeShare.mockResolvedValue({ data: {} })

    const wrapper = createWrapper()
    await nextTick()

    await wrapper.find('.ir-share__revoke-btn').trigger('click')

    expect(api.revokeShare).toHaveBeenCalledWith(1, 42)
    await nextTick()

    expect(message.success).toHaveBeenCalledWith('分享已撤销')
    expect(wrapper.text()).toContain('分享已撤销')
  })
})

import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import GraphicalCaptcha from '@/components/GraphicalCaptcha.vue'

const { createCaptchaChallenge, verifyCaptchaChallenge } = vi.hoisted(() => ({
  createCaptchaChallenge: vi.fn(),
  verifyCaptchaChallenge: vi.fn(),
}))

vi.mock('@/api/auth', () => ({ createCaptchaChallenge, verifyCaptchaChallenge }))
enableAutoUnmount(afterEach)

const challenge = {
  captchaEnabled: true,
  type: 'image_selection',
  challengeId: 'challenge-1',
  prompt: '请选择所有包含输电塔的图片',
  columns: 3,
  expiresIn: 120,
  tiles: [
    { tileId: 'tile-1', imageUrl: '/one.jpg' },
    { tileId: 'tile-2', imageUrl: '/two.jpg' },
  ],
}

describe('GraphicalCaptcha', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    createCaptchaChallenge.mockResolvedValue({ data: challenge })
  })

  async function readyWrapper() {
    const wrapper = mount(GraphicalCaptcha)
    await flushPromises()
    for (const image of wrapper.findAll('img')) await image.trigger('load')
    return wrapper
  }

  it('renders neutral, accessible image choices and validates a selection', async () => {
    verifyCaptchaChallenge.mockResolvedValue({ data: { verified: true, captchaToken: 'opaque-token', expiresIn: 60 } })
    const wrapper = await readyWrapper()
    const tiles = wrapper.findAll('.captcha-tile')
    expect(wrapper.text()).toContain(challenge.prompt)
    expect(tiles[0].attributes('aria-label')).toBe('验证图片 1')
    expect(tiles[0].attributes('aria-pressed')).toBe('false')

    await tiles[0].trigger('click')
    expect(tiles[0].attributes('aria-pressed')).toBe('true')
    await wrapper.find('.verify-button').trigger('click')
    await flushPromises()

    expect(verifyCaptchaChallenge).toHaveBeenCalledWith('challenge-1', ['tile-1'])
    expect(wrapper.emitted('verified').at(-1)[0]).toMatchObject({ captchaToken: 'opaque-token' })
    expect(wrapper.text()).toContain('安全验证已通过')
  })

  it('does not submit an empty selection', async () => {
    const wrapper = await readyWrapper()
    await wrapper.find('.verify-button').trigger('click')
    expect(verifyCaptchaChallenge).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('请至少选择一张图片')
  })

  it('keeps captcha enabled and login blocked when challenge loading fails', async () => {
    createCaptchaChallenge.mockRejectedValue(new Error('network'))
    const wrapper = mount(GraphicalCaptcha)
    await flushPromises()
    expect(wrapper.text()).toContain('验证内容加载失败，请重试')
    expect(wrapper.emitted('enabled-change').every(([enabled]) => enabled === true)).toBe(true)
  })

  it('supports the migration-period character challenge', async () => {
    createCaptchaChallenge.mockResolvedValue({ data: {
      captchaEnabled: true,
      type: 'character',
      uuid: 'legacy-id',
      img: 'synthetic-image',
    } })
    const wrapper = mount(GraphicalCaptcha)
    await flushPromises()
    await wrapper.find('input').setValue('1234')
    expect(wrapper.emitted('verified').at(-1)[0]).toEqual({ code: '1234', uuid: 'legacy-id', legacy: true })
  })
})

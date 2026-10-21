import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import axios from 'axios'
import Login from '@/views/login.vue'
import GraphicalCaptcha from '@/components/GraphicalCaptcha.vue'
import request from '@/utils/request'
import { createCaptchaChallenge, verifyCaptchaChallenge } from '@/api/auth'

const { login, warning, error } = vi.hoisted(() => ({ login: vi.fn(), warning: vi.fn(), error: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { warning, error }, ElMessageBox: { confirm: vi.fn() } }))
vi.mock('vue-router', () => ({ useRoute: () => ({ query: {} }), useRouter: () => ({ push: vi.fn() }) }))
vi.mock('@/store/modules/session', () => ({ useSessionStore: () => ({ login, loadUserInfo: vi.fn() }) }))
vi.mock('@/store/modules/permission', () => ({ usePermissionStore: () => ({ resetRoutes: vi.fn() }) }))

const challenge = (id = 'challenge-1') => ({
  captchaEnabled: true, type: 'image_selection', challengeId: id,
  prompt: '请选择所有包含输电塔的图片', columns: 3, expiresIn: 120,
  tiles: Array.from({ length: 9 }, (_, index) => ({ tileId: `${id}-${index}`, imageUrl: `/synthetic-${index}.png` })),
  alternativeModes: ['audio'],
})
const success = () => ({ code: 200, data: { verified: true, captchaToken: 'synthetic-token', expiresIn: 2 } })
const deferred = () => {
  let resolve
  const promise = new Promise((done) => { resolve = done })
  return { promise, resolve }
}
let wrappers
let create
let verify
let configs
const originalAdapter = request.defaults.adapter

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date', 'setTimeout', 'clearTimeout', 'setInterval', 'clearInterval'] })
  vi.setSystemTime(new Date('2026-10-21T12:00:00Z'))
  vi.clearAllMocks()
  wrappers = []
  configs = []
  create = vi.fn(async () => ({ code: 200, data: challenge() }))
  verify = vi.fn(async () => success())
  request.defaults.adapter = async (config) => {
    configs.push(config)
    const body = await (config.url.endsWith('/verify') ? verify(config) : create(config))
    return { data: body, status: 200, statusText: 'OK', headers: {}, config, request: {} }
  }
})
afterEach(() => {
  wrappers.forEach((wrapper) => wrapper.unmount())
  request.defaults.adapter = originalAdapter
  vi.useRealTimers()
})
async function render(component = GraphicalCaptcha) {
  const wrapper = mount(component)
  wrappers.push(wrapper)
  await flushPromises()
  return wrapper
}
async function selectAndVerify(wrapper) {
  for (const image of wrapper.findAll('.captcha-tile img')) await image.trigger('load')
  await wrapper.find('.captcha-tile').trigger('click')
  await wrapper.find('.verify-button').trigger('click')
  await flushPromises()
}
async function fillCredentials(wrapper) {
  await wrapper.find('input[autocomplete="username"]').setValue('alice')
  await wrapper.find('input[autocomplete="current-password"]').setValue('synthetic-password')
  await flushPromises()
}

describe('captcha business errors through the real Axios interceptors', () => {
  it('preserves business code/data and keeps ordinary request error messages', async () => {
    create.mockResolvedValue({ code: 'CAPTCHA_RATE_LIMITED', msg: 'safe-message', data: { retryAfter: 30 } })
    await expect(createCaptchaChallenge()).rejects.toMatchObject({
      code: 'CAPTCHA_RATE_LIMITED', data: { retryAfter: 30 }, message: 'safe-message',
    })
    expect(error).not.toHaveBeenCalled()
    await expect(request({ url: '/ir/example' })).rejects.toThrow('safe-message')
    expect(error).toHaveBeenCalledWith('safe-message')
    for (const config of configs.filter((item) => item.url.startsWith('/gateway/ecenter/'))) {
      expect(config.baseURL).toBe('')
      expect(config.headers.Authorization).toBeUndefined()
      expect(config.headers.userId).toBeUndefined()
      expect(config.headers.username).toBeUndefined()
    }
  })

  it.each([200, 429])('waits for retryAfter on HTTP %s without creating another challenge', async (status) => {
    verify.mockImplementation(async (config) => {
      const data = { code: 'CAPTCHA_RATE_LIMITED', msg: 'limited', data: { retryAfter: 30, nextChallenge: challenge('replacement') } }
      if (status === 429) throw new axios.AxiosError('HTTP 429', undefined, config, {}, { status, data, config })
      return data
    })
    const wrapper = await render()
    await selectAndVerify(wrapper)
    expect(wrapper.text()).toContain('30 秒后重试')
    expect(wrapper.find('header button').attributes('disabled')).toBeDefined()
    expect(wrapper.emitted('verified')).toBeUndefined()
    await vi.advanceTimersByTimeAsync(29000)
    expect(wrapper.text()).toContain('1 秒后重试')
    expect(create).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(1000)
    await flushPromises()
    expect(wrapper.findAll('.captcha-tile')).toHaveLength(9)
    expect(create).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).not.toContain('秒后重试')
    // The replacement challenge, rather than the consumed original, is submitted.
    verify.mockResolvedValue(success())
    await selectAndVerify(wrapper)
    expect(verify.mock.calls.at(-1)[0].url).toContain('/replacement/verify')
  })

  it('applies the cooldown to challenge creation and reloads only when it ends', async () => {
    create.mockResolvedValueOnce({ code: 'CAPTCHA_RATE_LIMITED', data: { retryAfter: 30 } })
    const wrapper = await render()
    expect(wrapper.text()).toContain('30 秒后重试')
    await wrapper.vm.reset('account-changed')
    expect(create).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(30000)
    await flushPromises()
    expect(create).toHaveBeenCalledTimes(2)
    expect(wrapper.findAll('.captcha-tile')).toHaveLength(9)
  })

  it('does not revive a nextChallenge that expired during the cooldown', async () => {
    verify.mockResolvedValue({ code: 'CAPTCHA_RATE_LIMITED', data: {
      retryAfter: 30, nextChallenge: { ...challenge('short-lived'), expiresIn: 10 },
    } })
    const wrapper = await render()
    await selectAndVerify(wrapper)
    await vi.advanceTimersByTimeAsync(30000)
    await flushPromises()
    expect(create).toHaveBeenCalledTimes(2)
    verify.mockResolvedValue(success())
    await selectAndVerify(wrapper)
    expect(verify.mock.calls.at(-1)[0].url).toContain('/challenge-1/verify')
  })

  it.each([
    ['CAPTCHA_INCORRECT', '选择不正确'], ['CAPTCHA_EXPIRED', '验证已过期'], ['CAPTCHA_CONSUMED', '验证已使用'],
  ])('uses nextChallenge for %s and retains its feedback', async (code, message) => {
    verify.mockResolvedValue({ code, data: { nextChallenge: challenge('replacement') } })
    const wrapper = await render()
    await selectAndVerify(wrapper)
    expect(wrapper.text()).toContain(message)
    expect(wrapper.find('.captcha-tile').attributes('aria-pressed')).toBe('false')
    expect(create).toHaveBeenCalledTimes(1)
    verify.mockResolvedValue(success())
    await selectAndVerify(wrapper)
    expect(verify.mock.calls.at(-1)[0].url).toContain('/replacement/verify')
  })

  it('reloads an incorrect challenge without erasing the error message', async () => {
    verify.mockResolvedValue({ code: 'CAPTCHA_INCORRECT' })
    const wrapper = await render()
    await selectAndVerify(wrapper)
    expect(create).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('选择不正确，请重试')
  })

  it.each(['CAPTCHA_UNAVAILABLE', 'timeout'])('fails closed with explicit retry for %s', async (code) => {
    if (code === 'timeout') verify.mockRejectedValue(new Error('timeout'))
    else verify.mockResolvedValue({ code })
    const wrapper = await render()
    await selectAndVerify(wrapper)
    expect(wrapper.find('.captcha-error').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('选择不正确')
    expect(create).toHaveBeenCalledTimes(1)
    expect(wrapper.emitted('verified')).toBeUndefined()
    await wrapper.find('.captcha-error button').trigger('click')
    await flushPromises()
    expect(wrapper.findAll('.captcha-tile')).toHaveLength(9)
  })

  it('does not invent an audio protocol or request an unsupported alternative', async () => {
    const wrapper = await render()
    expect(wrapper.find('.alternative-button').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('替代验证尚未接入')
    await wrapper.find('.alternative-button').trigger('click')
    expect(create).toHaveBeenCalledTimes(1)
    expect(JSON.parse(configs[0].data).preferredMode).toBe('image_selection')
  })

  it('rejects a successful response that omits the token lifetime', async () => {
    verify.mockResolvedValue({ code: 200, data: { verified: true, captchaToken: 'synthetic-token' } })
    const wrapper = await render()
    await selectAndVerify(wrapper)
    expect(wrapper.emitted('verified')).toBeUndefined()
    expect(wrapper.text()).toContain('验证凭证有效期无效')
  })

  it('does not mislabel a malformed success response as an incorrect selection', async () => {
    verify.mockResolvedValue({ code: 200, data: { verified: false } })
    const wrapper = await render()
    await selectAndVerify(wrapper)
    expect(wrapper.emitted('verified')).toBeUndefined()
    expect(wrapper.text()).toContain('验证结果无效')
    expect(create).toHaveBeenCalledTimes(1)
  })
})

describe('login captcha lifetime and account isolation', () => {
  it.each(['focus', 'visibilitychange', 'submit'])('rejects expired tokens after wall-clock advance with suspended timers: %s', async (event) => {
    const wrapper = await render(Login)
    await fillCredentials(wrapper)
    await selectAndVerify(wrapper)
    expect(wrapper.find('.login-submit').attributes('disabled')).toBeUndefined()
    const calls = create.mock.calls.length
    vi.setSystemTime(Date.now() + 3000) // Advances the wall clock without running timers.
    if (event === 'submit') await wrapper.find('form').trigger('submit')
    else {
      (event === 'focus' ? window : document).dispatchEvent(new Event(event))
      await flushPromises()
    }
    expect(wrapper.find('.login-submit').attributes('disabled')).toBeDefined()
    expect(login).not.toHaveBeenCalled()
    expect(create).toHaveBeenCalledTimes(calls + 1)
  })

  it('expires an unverified challenge on resume, including legacy challenges', async () => {
    create.mockResolvedValue({ code: 200, data: { type: 'character', uuid: 'synthetic-id', img: 'synthetic', expiresIn: 2 } })
    const wrapper = await render()
    await wrapper.find('input').setValue('1234')
    expect(wrapper.emitted('verified')).toHaveLength(1)
    vi.setSystemTime(Date.now() + 3000)
    window.dispatchEvent(new Event('focus'))
    await flushPromises()
    expect(wrapper.find('input').element.value).toBe('')
    expect(create).toHaveBeenCalledTimes(2)
    expect(wrapper.emitted('invalidated').at(-1)[0]).toBe('expired')
  })

  it('discards an alice verification completed after switching to bob', async () => {
    const pending = deferred()
    verify.mockReturnValue(pending.promise)
    const wrapper = await render(Login)
    await fillCredentials(wrapper)
    await selectAndVerify(wrapper)
    await wrapper.find('input[autocomplete="username"]').setValue('bob')
    pending.resolve(success())
    await flushPromises()
    expect(wrapper.find('.captcha-passed').exists()).toBe(false)
    expect(wrapper.find('.login-submit').attributes('disabled')).toBeDefined()
    await wrapper.find('form').trigger('submit')
    expect(login).not.toHaveBeenCalled()
  })

  it('discards a challenge load completed for an earlier account', async () => {
    const pending = deferred()
    const wrapper = await render(Login)
    create.mockReturnValueOnce(pending.promise)
    await wrapper.find('input[autocomplete="username"]').setValue('alice')
    await flushPromises()
    await wrapper.find('input[autocomplete="username"]').setValue('bob')
    await flushPromises()
    pending.resolve({ code: 200, data: { captchaEnabled: false } })
    await flushPromises()
    await wrapper.find('input[autocomplete="current-password"]').setValue('synthetic-password')
    expect(wrapper.findAll('.captcha-tile')).toHaveLength(9)
    expect(wrapper.find('.login-submit').attributes('disabled')).toBeDefined()
  })

  it('fails closed and exposes retry after disabled captcha then login/reload failure', async () => {
    create.mockResolvedValue({ code: 200, data: { captchaEnabled: false } })
    login.mockRejectedValue(new Error('synthetic login failure'))
    const wrapper = await render(Login)
    await fillCredentials(wrapper)
    expect(wrapper.find('.login-submit').attributes('disabled')).toBeUndefined()
    create.mockRejectedValueOnce(new Error('Network Error'))
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    await wrapper.find('input[autocomplete="current-password"]').setValue('another-password')
    expect(wrapper.find('.login-submit').attributes('disabled')).toBeDefined()
    expect(wrapper.find('.captcha-error button').exists()).toBe(true)
    await wrapper.find('form').trigger('submit')
    expect(login).toHaveBeenCalledTimes(1)
    await wrapper.find('.captcha-error button').trigger('click')
    await flushPromises()
    expect(wrapper.find('.login-submit').attributes('disabled')).toBeUndefined()
  })
})

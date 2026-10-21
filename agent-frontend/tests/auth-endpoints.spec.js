import { beforeEach, describe, expect, it, vi } from 'vitest'

const request = vi.fn(() => Promise.resolve({ data: {} }))

vi.mock('@/utils/request', () => ({ default: request }))

const { login, getCodeImg, createCaptchaChallenge, verifyCaptchaChallenge } = await import('@/api/auth')
const { getUserInfo } = await import('@/api/session')
const { getRouters } = await import('@/api/menu')

describe('gateway authentication endpoint paths', () => {
  beforeEach(() => request.mockClear())

  it('uses root gateway paths for captcha and login', async () => {
    await getCodeImg()
    expect(request).toHaveBeenLastCalledWith(expect.objectContaining({
      url: '/gateway/code',
    }))

    await login({ username: 'admin', password: 'secret' })
    expect(request).toHaveBeenLastCalledWith(expect.objectContaining({
      url: '/gateway/ecenter/system/auth/login',
    }))
  })

  it('uses root ecenter gateway paths for user info and dynamic menus', async () => {
    await getUserInfo()
    expect(request).toHaveBeenLastCalledWith(expect.objectContaining({
      url: '/gateway/ecenter/system/user/getInfo',
    }))

    await getRouters()
    expect(request).toHaveBeenLastCalledWith(expect.objectContaining({
      url: '/gateway/ecenter/system/menu/getRouters/eAgentIr',
    }))
  })

  it('creates and verifies graphical captcha challenges without an auth token', async () => {
    await createCaptchaChallenge()
    expect(request).toHaveBeenLastCalledWith(expect.objectContaining({
      url: '/gateway/ecenter/system/auth/captcha/challenges',
      method: 'post',
      headers: { isToken: false },
    }))

    await verifyCaptchaChallenge('challenge/id', ['tile-2', 'tile-2', 'tile-1'])
    expect(request).toHaveBeenLastCalledWith(expect.objectContaining({
      url: '/gateway/ecenter/system/auth/captcha/challenges/challenge%2Fid/verify',
      data: { tileIds: ['tile-2', 'tile-1'] },
    }))
  })

  it('sends only the captcha token for graphical captcha login', async () => {
    await login({ username: ' admin ', password: 'secret', captchaToken: 'one-time', code: 'old', uuid: 'old-id' })
    const payload = request.mock.calls.at(-1)[0].data
    expect(payload).toMatchObject({ username: 'admin', captchaToken: 'one-time' })
    expect(payload).not.toHaveProperty('code')
    expect(payload).not.toHaveProperty('uuid')
  })
})

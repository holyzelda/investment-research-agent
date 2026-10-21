import { beforeEach, describe, expect, it, vi } from 'vitest'

const request = vi.fn(() => Promise.resolve({ data: {} }))

vi.mock('@/utils/request', () => ({ default: request }))

const { login, getCodeImg, loginBySms, sendSmsCode } = await import('@/api/auth')
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

  it('uses ecenter SMS endpoints and fixes the country code to China', async () => {
    await sendSmsCode('13800138000')
    expect(request).toHaveBeenLastCalledWith(expect.objectContaining({
      url: '/gateway/ecenter/system/auth/sms/send',
      data: { mobile: '13800138000', countryCode: '86', scene: 'login' },
    }))

    await loginBySms({ mobile: '13800138000', code: '012345', requestId: 'request-1' })
    expect(request).toHaveBeenLastCalledWith(expect.objectContaining({
      url: '/gateway/ecenter/system/auth/sms/login',
      data: { mobile: '13800138000', code: '012345', requestId: 'request-1', countryCode: '86' },
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
})

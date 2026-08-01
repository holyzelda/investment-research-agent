import { beforeEach, describe, expect, it, vi } from 'vitest'

const request = vi.fn(() => Promise.resolve({ data: {} }))

vi.mock('@/utils/request', () => ({ default: request }))

const { login, getCodeImg } = await import('@/api/auth')
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
})

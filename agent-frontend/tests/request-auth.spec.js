import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import axios from 'axios'

const confirm = vi.fn(() => new Promise(() => {}))
const error = vi.fn()

vi.mock('element-plus', () => ({
  ElMessage: { error },
  ElMessageBox: { confirm },
}))

const { default: request, isRelogin } = await import('@/utils/request')
const { removeToken, removeUserIdentity, setToken, setUserIdentity } = await import('@/utils/auth')

function responseAdapter(data, status = 200) {
  return async (config) => {
    if (status >= 400) {
      const requestError = new axios.AxiosError(`HTTP ${status}`, undefined, config)
      requestError.response = { status, data, headers: {}, config, request: {} }
      throw requestError
    }
    return { data, status, statusText: 'OK', headers: {}, config, request: {} }
  }
}

describe('request authentication expiry', () => {
  beforeEach(() => {
    confirm.mockClear()
    error.mockClear()
    isRelogin.show = false
    window.sessionStorage.clear()
    setToken('expired-token')
    setUserIdentity({ userId: 'admin-1', username: '张三' })
  })

  afterEach(() => {
    request.defaults.adapter = undefined
    removeToken()
    removeUserIdentity()
    window.sessionStorage.clear()
  })

  it('opens the re-login dialog for a protected API returning business code 401', async () => {
    request.defaults.adapter = responseAdapter({ code: 401, msg: 'Token 已失效' })

    await expect(request({ url: '/gateway/ir-agent/ir/me' })).rejects.toThrow('Token 已失效')

    expect(confirm).toHaveBeenCalledOnce()
    expect(isRelogin.show).toBe(true)
    expect(window.sessionStorage.getItem('ir-login-required')).toBe('1')
  })

  it('does not open the expiry dialog for the public login API', async () => {
    request.defaults.adapter = responseAdapter({ code: 401, msg: '用户名或密码错误' })

    await expect(request({
      url: '/gateway/ecenter/system/auth/login',
      method: 'post',
      headers: { isToken: false },
      data: {},
    })).rejects.toThrow('用户名或密码错误')

    expect(confirm).not.toHaveBeenCalled()
    expect(window.sessionStorage.getItem('ir-login-required')).toBeNull()
  })

  it('opens the re-login dialog for an HTTP 401 response', async () => {
    request.defaults.adapter = responseAdapter({ msg: 'Unauthorized' }, 401)

    await expect(request({ url: '/gateway/ecenter/system/menu/getRouters/eAgentIr' })).rejects.toMatchObject({
      response: { status: 401 },
    })

    expect(confirm).toHaveBeenCalledOnce()
    expect(window.sessionStorage.getItem('ir-login-required')).toBe('1')
  })

  it('does not authenticate public calculation-share requests', async () => {
    let capturedConfig
    request.defaults.adapter = async (config) => {
      capturedConfig = config
      return { data: { code: 200, msg: 'success', data: { status: 'not_found' } }, status: 200, statusText: 'OK', headers: {}, config, request: {} }
    }

    const { getPublicShare } = await import('@/api/calc')
    await getPublicShare('public-share-code')

    expect(capturedConfig.headers.Authorization).toBeUndefined()
    expect(capturedConfig.headers.userId).toBeUndefined()
    expect(capturedConfig.headers.username).toBeUndefined()
    expect(capturedConfig.headers.isToken).toBeUndefined()
  })

  it('does not trigger re-login for an anonymous public share 401', async () => {
    request.defaults.adapter = responseAdapter({ code: 401, msg: '令牌为空' })

    const { getPublicShare } = await import('@/api/calc')
    await expect(getPublicShare('public-share-code')).rejects.toThrow('令牌为空')

    expect(confirm).not.toHaveBeenCalled()
    expect(window.sessionStorage.getItem('ir-login-required')).toBeNull()
  })

  it('adds ecenter identity only to IR business requests', async () => {
    let capturedConfig
    request.defaults.adapter = async (config) => {
      capturedConfig = config
      return { data: { code: 200 }, status: 200, statusText: 'OK', headers: {}, config, request: {} }
    }

    await request({ url: '/ir/me' })

    expect(capturedConfig.headers.userId).toBe('admin-1')
    expect(capturedConfig.headers.username).toBe('%E5%BC%A0%E4%B8%89')
  })

  it('does not add identity to root gateway endpoints or overwrite explicit headers', async () => {
    const capturedConfigs = []
    request.defaults.adapter = async (config) => {
      capturedConfigs.push(config)
      return { data: { code: 200 }, status: 200, statusText: 'OK', headers: {}, config, request: {} }
    }

    await request({ url: '/gateway/ecenter/system/user/getInfo?systemSign=eAgentIr' })
    await request({ url: '/ir/me', headers: { userId: 'explicit-id', username: 'explicit-name' } })

    expect(capturedConfigs[0].headers.userId).toBeUndefined()
    expect(capturedConfigs[0].headers.username).toBeUndefined()
    expect(capturedConfigs[1].headers.userId).toBe('explicit-id')
    expect(capturedConfigs[1].headers.username).toBe('explicit-name')
  })

  it('routes root gateway endpoints outside the business base URL', async () => {
    let capturedConfig
    request.defaults.adapter = async (config) => {
      capturedConfig = config
      return { data: { code: 200 }, status: 200, statusText: 'OK', headers: {}, config, request: {} }
    }

    await request({ url: '/gateway/code', headers: { isToken: false } })

    expect(capturedConfig.baseURL).toBe('')
  })
})

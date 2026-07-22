import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import axios from 'axios'

const confirm = vi.fn(() => new Promise(() => {}))
const error = vi.fn()

vi.mock('element-plus', () => ({
  ElMessage: { error },
  ElMessageBox: { confirm },
}))

const { default: request, isRelogin } = await import('@/utils/request')
const { removeToken, setToken } = await import('@/utils/auth')

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
  })

  afterEach(() => {
    request.defaults.adapter = undefined
    removeToken()
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
})

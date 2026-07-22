import { beforeEach, describe, expect, it, vi } from 'vitest'

const guards = []
const routerMock = {
  beforeEach: vi.fn((guard) => guards.push(guard)),
  getRoutes: vi.fn(() => []),
  hasRoute: vi.fn(() => false),
  addRoute: vi.fn(),
}

vi.mock('@/router', () => ({ default: routerMock }))
vi.mock('@/store/modules/session', () => ({
  useSessionStore: () => ({ loaded: true, loadUserInfo: vi.fn() }),
}))
vi.mock('@/store/modules/permission', () => ({
  usePermissionStore: () => ({ loaded: true, generateRoutes: vi.fn() }),
}))

const { default: _permission } = await import('@/permission')
const { clearLoginRequired, getToken, markLoginRequired, removeToken, setToken } = await import('@/utils/auth')

describe('platform opener token handoff', () => {
  const guard = () => guards[0]

  beforeEach(() => {
    removeToken()
    clearLoginRequired()
    const storage = new Map()
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      value: {
        getItem: (key) => storage.get(key) || null,
        setItem: (key, value) => storage.set(key, String(value)),
        removeItem: (key) => storage.delete(key),
      },
    })
    Object.defineProperty(window, 'opener', {
      configurable: true,
      value: { postMessage: vi.fn() },
    })
  })

  it('accepts a valid opener token and retries the original navigation', async () => {
    const to = { path: '/home', fullPath: '/home' }
    setToken('stale-platform-token')
    const navigation = guard()(to)
    window.dispatchEvent(new MessageEvent('message', {
      data: { type: 'token', token: 'valid-platform-token' },
    }))

    await expect(navigation).resolves.toEqual({ ...to, replace: true })
    expect(getToken()).toBe('valid-platform-token')
    expect(window.opener.postMessage).toHaveBeenCalledWith('request-token', '*')
  })

  it('does not ask the opener for a stale token while login is required', async () => {
    markLoginRequired()
    const result = await guard()({ path: '/login', fullPath: '/login' })

    expect(result).toBe(true)
    expect(window.opener.postMessage).not.toHaveBeenCalled()
  })
})
